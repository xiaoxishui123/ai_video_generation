"""
文本/参考图生成图片工具 (Text-to-Image / Image-to-Image)

使用火山引擎豆包 Seedream 系列模型根据文本描述或参考图生成图片。

支持的模型:
- doubao-seedream-4-5-251128: Seedream 4.5 (推荐，最新版本，支持参考图)
- doubao-seedream-3-0-t2i-250110: Seedream 3.0 T2I (仅支持文生图)

功能说明:
- 文生图: 仅使用 prompt 生成图片
- 图生图: 使用 prompt + reference_images 参考图生成图片
- Seedream 4.5 支持最多 14 张参考图
- 支持自动获取参考图尺寸（当 size 设置为 "auto" 时）

API 文档参考:
- 火山引擎 Ark API: https://www.volcengine.com/docs/82379/1541523
"""

import requests
import struct
import base64
from typing import Any, Generator, Optional, Tuple, List
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class TextToImageTool(Tool):
    """文本生成图片工具 - 火山引擎 Seedream 模型"""

    # ========== 火山方舟配置 ==========
    # 使用 Ark API
    VOLCENGINE_API_BASE = "https://ark.cn-beijing.volces.com/api/v3"
    
    # 支持的模型列表
    VOLCENGINE_MODELS = {
        "doubao-seedream-4-5-251128": {"name": "Seedream 4.5 (推荐)"},
        "doubao-seedream-3-0-t2i-250110": {"name": "Seedream 3.0 T2I"},
    }
    
    # 火山引擎支持的尺寸列表（宽x高）
    # 文生图模式：支持所有尺寸
    SUPPORTED_SIZES_T2I = [
        (512, 512),
        (768, 768),
        (1024, 1024),
        (1280, 720),
        (720, 1280),
        (1536, 1024),
        (1024, 1536),
        (2048, 2048),
    ]
    
    # 图生图模式：要求至少 3686400 像素（约1920x1920）
    # 只支持较大尺寸
    SUPPORTED_SIZES_I2I = [
        (2048, 2048),      # 4,194,304 像素
        (2560, 1440),      # 3,686,400 像素 (16:9)
        (1440, 2560),      # 3,686,400 像素 (9:16)
        (2048, 1536),      # 3,145,728 像素 - 可能不够，但保留
        (1536, 2048),      # 3,145,728 像素
    ]
    
    # 图生图最小像素要求
    I2I_MIN_PIXELS = 3686400
    
    # 默认参数
    DEFAULT_SIZE = "1024x1024"
    DEFAULT_SIZE_I2I = "2k"  # 图生图默认使用 2k
    DEFAULT_GUIDANCE_SCALE = 7.5
    
    def _download_and_convert_to_base64(self, url: str) -> Optional[str]:
        """
        下载图片并转换为 base64 数据 URL
        
        解决火山引擎无法访问 Dify 内部文件 URL 的问题。
        火山引擎 API 支持 data URL 格式的图片输入。
        
        Args:
            url: 图片的 URL 地址
            
        Returns:
            base64 数据 URL (如 "data:image/jpeg;base64,...") 或 None
        """
        # 如果已经是 data URL，直接返回
        if url.startswith('data:'):
            return url
            
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=60)
            
            if response.status_code != 200:
                return None
            
            image_data = response.content
            
            # 检测图片 MIME 类型
            content_type = response.headers.get('Content-Type', '').lower()
            if 'png' in content_type:
                mime_type = 'image/png'
            elif 'gif' in content_type:
                mime_type = 'image/gif'
            elif 'webp' in content_type:
                mime_type = 'image/webp'
            elif 'jpeg' in content_type or 'jpg' in content_type:
                mime_type = 'image/jpeg'
            else:
                # 从图片头部检测
                if image_data[:8] == b'\x89PNG\r\n\x1a\n':
                    mime_type = 'image/png'
                elif image_data[:2] == b'\xff\xd8':
                    mime_type = 'image/jpeg'
                elif image_data[:6] in (b'GIF87a', b'GIF89a'):
                    mime_type = 'image/gif'
                elif image_data[:4] == b'RIFF' and len(image_data) > 12 and image_data[8:12] == b'WEBP':
                    mime_type = 'image/webp'
                else:
                    mime_type = 'image/jpeg'
            
            # 转换为 base64
            b64_data = base64.b64encode(image_data).decode('utf-8')
            return f"data:{mime_type};base64,{b64_data}"
            
        except Exception:
            return None
    
    def _prepare_reference_images(self, urls: List[str]) -> Tuple[List[str], int, int]:
        """
        准备参考图片，将 URL 转换为 base64 格式
        
        Args:
            urls: 图片 URL 列表
            
        Returns:
            (转换后的图片列表, 成功数量, 失败数量)
        """
        converted = []
        success_count = 0
        fail_count = 0
        
        for url in urls:
            result = self._download_and_convert_to_base64(url)
            if result:
                converted.append(result)
                success_count += 1
            else:
                fail_count += 1
        
        return converted, success_count, fail_count
    
    def _get_image_size_from_url(self, url: str) -> Optional[Tuple[int, int]]:
        """
        从图片 URL 获取图片尺寸（宽, 高）
        只下载图片头部信息，不下载完整图片，节省带宽
        
        Args:
            url: 图片的 URL 地址
            
        Returns:
            (width, height) 或 None（获取失败时）
        """
        try:
            # 设置请求头，只获取部分内容
            headers = {
                'Range': 'bytes=0-65535',  # 只获取前64KB，足够解析大多数图片头部
                'User-Agent': 'Mozilla/5.0'
            }
            
            response = requests.get(url, headers=headers, timeout=10, stream=True)
            
            # 读取图片数据
            data = response.content
            
            # 尝试识别图片格式并获取尺寸
            size = self._get_image_dimensions(data)
            return size
            
        except Exception:
            return None
    
    def _get_image_dimensions(self, data: bytes) -> Optional[Tuple[int, int]]:
        """
        从图片二进制数据解析图片尺寸
        支持 PNG, JPEG, GIF, WEBP 格式
        
        Args:
            data: 图片的二进制数据（至少需要头部信息）
            
        Returns:
            (width, height) 或 None
        """
        # PNG 格式: 前8字节是签名，接下来是IHDR块
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            # IHDR 块在第 16-24 字节包含宽度和高度
            if len(data) >= 24:
                width = struct.unpack('>I', data[16:20])[0]
                height = struct.unpack('>I', data[20:24])[0]
                return (width, height)
        
        # JPEG 格式
        if data[:2] == b'\xff\xd8':
            # JPEG 需要解析 SOF 标记
            try:
                return self._get_jpeg_dimensions(data)
            except Exception:
                pass
        
        # GIF 格式
        if data[:6] in (b'GIF87a', b'GIF89a'):
            if len(data) >= 10:
                width = struct.unpack('<H', data[6:8])[0]
                height = struct.unpack('<H', data[8:10])[0]
                return (width, height)
        
        # WEBP 格式
        if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            try:
                return self._get_webp_dimensions(data)
            except Exception:
                pass
        
        return None
    
    def _get_jpeg_dimensions(self, data: bytes) -> Optional[Tuple[int, int]]:
        """解析 JPEG 图片尺寸"""
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xff:
                i += 1
                continue
            
            marker = data[i + 1]
            
            # SOF 标记 (0xC0-0xCF, 除了 0xC4, 0xC8, 0xCC)
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                         0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                if i + 9 <= len(data):
                    height = struct.unpack('>H', data[i + 5:i + 7])[0]
                    width = struct.unpack('>H', data[i + 7:i + 9])[0]
                    return (width, height)
            
            # 跳过当前标记块
            if i + 4 <= len(data):
                length = struct.unpack('>H', data[i + 2:i + 4])[0]
                i += 2 + length
            else:
                break
        
        return None
    
    def _get_webp_dimensions(self, data: bytes) -> Optional[Tuple[int, int]]:
        """解析 WEBP 图片尺寸"""
        if len(data) < 30:
            return None
        
        # VP8 格式
        if data[12:16] == b'VP8 ':
            if len(data) >= 30:
                width = struct.unpack('<H', data[26:28])[0] & 0x3fff
                height = struct.unpack('<H', data[28:30])[0] & 0x3fff
                return (width, height)
        
        # VP8L 格式 (无损)
        if data[12:16] == b'VP8L':
            if len(data) >= 25:
                bits = struct.unpack('<I', data[21:25])[0]
                width = (bits & 0x3fff) + 1
                height = ((bits >> 14) & 0x3fff) + 1
                return (width, height)
        
        # VP8X 格式 (扩展)
        if data[12:16] == b'VP8X':
            if len(data) >= 30:
                width = struct.unpack('<I', data[24:27] + b'\x00')[0] + 1
                height = struct.unpack('<I', data[27:30] + b'\x00')[0] + 1
                return (width, height)
        
        return None
    
    def _find_closest_supported_size(self, width: int, height: int, is_i2i: bool = False) -> str:
        """
        找到最接近的支持尺寸
        
        Args:
            width: 原始宽度
            height: 原始高度
            is_i2i: 是否为图生图模式（需要更大尺寸）
            
        Returns:
            最接近的支持尺寸字符串，如 "1024x1024" 或 "2k"
        """
        # 根据模式选择支持的尺寸列表
        supported_sizes = self.SUPPORTED_SIZES_I2I if is_i2i else self.SUPPORTED_SIZES_T2I
        
        # 计算原始宽高比
        original_ratio = width / height
        
        best_size = None
        best_score = float('inf')
        
        for sw, sh in supported_sizes:
            # 计算支持尺寸的宽高比
            supported_ratio = sw / sh
            
            # 计算宽高比差异（使用对数差异，对称处理）
            ratio_diff = abs(original_ratio - supported_ratio) / max(original_ratio, supported_ratio)
            
            # 计算面积差异
            original_area = width * height
            supported_area = sw * sh
            area_diff = abs(original_area - supported_area) / max(original_area, supported_area)
            
            # 综合得分（宽高比更重要）
            score = ratio_diff * 2 + area_diff
            
            if score < best_score:
                best_score = score
                best_size = (sw, sh)
        
        if best_size:
            # 图生图模式：使用 2k 格式（更可靠）
            if is_i2i:
                return "2k"
            return f"{best_size[0]}x{best_size[1]}"
        
        return self.DEFAULT_SIZE_I2I if is_i2i else self.DEFAULT_SIZE

    def _invoke(
        self, tool_parameters: dict[str, Any]
    ) -> Generator[ToolInvokeMessage, None, None]:
        """
        执行工具调用 - 生成图片
        """
        # 获取凭证
        api_key = self.runtime.credentials.get("volcengine_api_key", "")
        if not api_key:
            yield self.create_text_message("❌ 错误：请配置火山引擎 API Key")
            return
        
        # 解析参数 - 直接使用工作流配置的模型
        # 注意：Seedream 是火山引擎的公共图像模型，不需要通过 endpoint 访问
        # volcengine_endpoint_id 仅用于视频生成等需要自定义 endpoint 的场景
        model = tool_parameters.get("model", "doubao-seedream-4-5-251128")
            
        prompt = tool_parameters.get("prompt", "").strip()
        negative_prompt = tool_parameters.get("negative_prompt", "").strip()
        reference_images_str = tool_parameters.get("reference_images", "").strip()
        size = tool_parameters.get("size", self.DEFAULT_SIZE)
        num_images = int(tool_parameters.get("num_images", 1))
        seed = tool_parameters.get("seed")
        guidance_scale = tool_parameters.get("guidance_scale")
        watermark = tool_parameters.get("watermark", False)
        response_format = tool_parameters.get("response_format", "url")
        
        # 解析参考图URL列表
        reference_images = []
        if reference_images_str:
            # 支持逗号分隔的多个URL
            for url in reference_images_str.split(","):
                url = url.strip()
                if url and (url.startswith("http://") or url.startswith("https://")):
                    reference_images.append(url)
            # 限制最多14张参考图
            if len(reference_images) > 14:
                reference_images = reference_images[:14]
        
        # 判断是否为图生图模式（有参考图）
        is_i2i_mode = len(reference_images) > 0
        
        # 参数验证
        if not prompt:
            yield self.create_text_message("❌ 错误：图片描述不能为空")
            return
        
        # 解析尺寸 - 增强验证
        # 确保 size 是有效格式: WIDTHxHEIGHT, 1k, 2k, 4k, auto
        valid_size = False
        auto_size_detected = False
        size_adjusted_for_i2i = False
        orig_w, orig_h = 0, 0
        size_str = str(size).strip().lower() if size else ""
        
        # 检查是否需要自动获取尺寸
        if size_str == "auto" or not size_str:
            # 尝试从参考图自动获取尺寸
            if reference_images:
                detected_size = self._get_image_size_from_url(reference_images[0])
                if detected_size:
                    orig_w, orig_h = detected_size
                    size = self._find_closest_supported_size(orig_w, orig_h, is_i2i=is_i2i_mode)
                    valid_size = True
                    auto_size_detected = True
        
        # 如果不是 auto 模式，验证 size 格式
        if not valid_size and size_str:
            if size_str in ['1k', '2k', '4k']:
                valid_size = True
                size = size_str
            elif 'x' in size_str:
                try:
                    w, h = map(int, size_str.split("x"))
                    if w > 0 and h > 0:
                        valid_size = True
                        size = size_str
                except ValueError:
                    pass
        
        if not valid_size:
            # 无效的 size 格式，根据模式使用默认值
            size = self.DEFAULT_SIZE_I2I if is_i2i_mode else self.DEFAULT_SIZE
        
        # 图生图模式：强制检查并调整尺寸
        # 火山引擎图生图要求至少 3686400 像素
        if is_i2i_mode:
            size_lower = str(size).lower()
            needs_adjustment = False
            
            # 检查当前尺寸是否满足要求
            if size_lower in ['1k', '2k', '4k']:
                # 1k 不满足，2k 和 4k 满足
                if size_lower == '1k':
                    needs_adjustment = True
            elif 'x' in size_lower:
                try:
                    w, h = map(int, size_lower.split("x"))
                    pixels = w * h
                    if pixels < self.I2I_MIN_PIXELS:
                        needs_adjustment = True
                except ValueError:
                    needs_adjustment = True
            else:
                needs_adjustment = True
            
            if needs_adjustment:
                size_adjusted_for_i2i = True
                size = "2k"  # 图生图模式强制使用 2k
        
        model_name = self.VOLCENGINE_MODELS.get(model, {}).get("name", model)
        
        # 构建提示信息
        generation_mode = "图生图" if is_i2i_mode else "文生图"
        size_info = f"{size}"
        if auto_size_detected and orig_w > 0:
            size_info += f" (自动检测: {orig_w}x{orig_h} → {size})"
        elif size_adjusted_for_i2i:
            size_info += f" (图生图模式自动调整为 2k)"
        
        info_text = (
            f"🎨 **提交图片生成任务**\n\n"
            f"🏢 平台: 火山引擎\n"
            f"📝 模型: {model_name}\n"
            f"🔄 模式: {generation_mode}\n"
            f"📐 尺寸: {size_info}\n"
            f"🖼️ 数量: {num_images}张\n"
        )
        if reference_images:
            info_text += f"🖼️ 参考图: {len(reference_images)}张\n"
        if seed is not None:
            info_text += f"🎲 种子: {seed}\n"
        if guidance_scale is not None:
            info_text += f"🎯 引导系数: {guidance_scale}\n"
        if watermark:
            info_text += f"💧 水印: 已开启\n"
        info_text += f"💬 提示词: {prompt[:80]}{'...' if len(prompt) > 80 else ''}"
        if negative_prompt:
            info_text += f"\n🚫 负面提示词: {negative_prompt[:50]}{'...' if len(negative_prompt) > 50 else ''}"
        
        yield self.create_text_message(info_text)
        
        # 构建请求头
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建请求体 - 使用 OpenAI 兼容的 images/generations API
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "n": num_images,
            "response_format": response_format
        }
        
        # 添加参考图参数（图生图功能）
        if reference_images:
            # 将参考图 URL 转换为 base64 格式
            # 这是为了解决火山引擎无法访问 Dify 内部文件 URL 的问题
            converted_images, success_count, fail_count = self._prepare_reference_images(reference_images)
            
            if fail_count > 0:
                yield self.create_text_message(f"⚠️ 警告: {fail_count}张参考图下载失败")
            
            if not converted_images:
                yield self.create_text_message("❌ 错误: 所有参考图都下载失败，无法进行图生图")
                yield self.create_json_message({
                    "success": False,
                    "provider": "volcengine",
                    "model": model,
                    "error_message": "参考图下载失败"
                })
                return
            
            # 单张图片传字符串，多张图片传数组
            if len(converted_images) == 1:
                payload["image"] = converted_images[0]
            else:
                payload["image"] = converted_images
        
        # 添加可选参数
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if seed is not None:
            payload["seed"] = int(seed)
        if guidance_scale is not None:
            payload["guidance_scale"] = float(guidance_scale)
        if watermark:
            payload["watermark"] = True
        
        try:
            # 发送请求 - 使用 images/generations 端点
            response = requests.post(
                f"{self.VOLCENGINE_API_BASE}/images/generations",
                headers=headers,
                json=payload,
                timeout=120  # 图片生成可能需要较长时间
            )
            
            if response.status_code != 200:
                error_text = response.text
                try:
                    error_json = response.json()
                    error_text = error_json.get("error", {}).get("message", error_text)
                except Exception:
                    pass
                yield self.create_text_message(f"❌ 生成失败: {response.status_code} - {error_text}")
                yield self.create_json_message({
                    "success": False,
                    "provider": "volcengine",
                    "model": model,
                    "error_message": error_text
                })
                return
            
            result = response.json()
            
            # 解析返回结果
            images_data = result.get("data", [])
            
            if not images_data:
                yield self.create_text_message("❌ 生成失败: 未返回图片数据")
                yield self.create_json_message({
                    "success": False,
                    "provider": "volcengine",
                    "model": model,
                    "error_message": "未返回图片数据"
                })
                return
            
            # 处理返回的图片
            image_urls = []
            for i, img_data in enumerate(images_data):
                if response_format == "url":
                    img_url = img_data.get("url", "")
                    if img_url:
                        image_urls.append(img_url)
                        # 输出图片URL
                        yield self.create_text_message(
                            f"📷 **图片 {i + 1}**\n{img_url}"
                        )
                        # 显示图片预览
                        yield self.create_image_message(img_url)
                else:
                    # Base64 格式
                    b64_data = img_data.get("b64_json", "")
                    if b64_data:
                        image_urls.append(f"data:image/png;base64,{b64_data[:50]}...")
                        yield self.create_text_message(f"📷 **图片 {i + 1}** (Base64格式)")
                        # Base64 图片需要特殊处理
                        yield self.create_blob_message(
                            blob=bytes(b64_data, 'utf-8'),
                            meta={"mime_type": "image/png"}
                        )
            
            # 成功消息
            yield self.create_text_message(
                f"\n---\n"
                f"🎉 **图片生成完成！**\n"
                f"✅ 成功生成 {len(image_urls)} 张图片"
            )
            
            # 返回 JSON 结果
            result_json = {
                "success": True,
                "provider": "volcengine",
                "model": model,
                "mode": "image_to_image" if reference_images else "text_to_image",
                "prompt": prompt,
                "size": size,
                "num_images": len(image_urls),
                "image_urls": image_urls,
                "response_format": response_format
            }
            if reference_images:
                result_json["reference_images"] = reference_images
            yield self.create_json_message(result_json)
                
        except requests.Timeout:
            yield self.create_text_message("❌ 错误: 请求超时，图片生成时间较长，请稍后重试")
            yield self.create_json_message({
                "success": False,
                "provider": "volcengine",
                "model": model,
                "error_message": "请求超时"
            })
        except requests.RequestException as e:
            yield self.create_text_message(f"❌ 网络错误: {str(e)}")
            yield self.create_json_message({
                "success": False,
                "provider": "volcengine",
                "model": model,
                "error_message": str(e)
            })
        except Exception as e:
            yield self.create_text_message(f"❌ 错误: {str(e)}")
            yield self.create_json_message({
                "success": False,
                "provider": "volcengine",
                "model": model,
                "error_message": str(e)
            })

