"""
文本生成图片工具 (Text-to-Image)

使用火山引擎豆包 Seedream 系列模型根据文本描述生成图片。

支持的模型:
- doubao-seedream-4-5-251128: Seedream 4.5 (推荐，最新版本)
- doubao-seedream-3-0-t2i-250110: Seedream 3.0 T2I

API 文档参考:
- 火山引擎 Ark API: https://www.volcengine.com/docs/82379/1298454
"""

import requests
from typing import Any, Generator
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
    
    # 默认参数
    DEFAULT_SIZE = "1024x1024"
    DEFAULT_GUIDANCE_SCALE = 7.5

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
        
        # 获取 endpoint_id，如果配置了则使用 endpoint_id，否则使用 model 名称
        endpoint_id = self.runtime.credentials.get("volcengine_endpoint_id", "").strip()
        
        # 解析参数
        model = tool_parameters.get("model", "doubao-seedream-4-5-251128")
        
        # 如果配置了 endpoint_id，则使用它
        if endpoint_id:
            model = endpoint_id
            
        prompt = tool_parameters.get("prompt", "").strip()
        negative_prompt = tool_parameters.get("negative_prompt", "").strip()
        size = tool_parameters.get("size", self.DEFAULT_SIZE)
        num_images = int(tool_parameters.get("num_images", 1))
        seed = tool_parameters.get("seed")
        guidance_scale = tool_parameters.get("guidance_scale")
        watermark = tool_parameters.get("watermark", False)
        response_format = tool_parameters.get("response_format", "url")
        
        # 参数验证
        if not prompt:
            yield self.create_text_message("❌ 错误：图片描述不能为空")
            return
        
        # 解析尺寸
        try:
            width, height = map(int, size.split("x"))
        except ValueError:
            width, height = 1024, 1024
        
        model_name = self.VOLCENGINE_MODELS.get(model, {}).get("name", model)
        
        # 构建提示信息
        info_text = (
            f"🎨 **提交图片生成任务**\n\n"
            f"🏢 平台: 火山引擎\n"
            f"📝 模型: {model_name}\n"
            f"📐 尺寸: {size}\n"
            f"🖼️ 数量: {num_images}张\n"
        )
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
            yield self.create_json_message({
                "success": True,
                "provider": "volcengine",
                "model": model,
                "prompt": prompt,
                "size": size,
                "num_images": len(image_urls),
                "image_urls": image_urls,
                "response_format": response_format
            })
                
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

