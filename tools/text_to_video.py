"""
视频生成工具 (Video Generation)

支持三大平台：
- 阿里云百炼：通义万相 wan2.5-t2v-preview（仅文生视频）
- 火山方舟：豆包 Seedance 系列模型（支持文生视频和图生视频）
- JXINCM：Sora-2 系列模型（第三方服务，固定15秒时长）

火山方舟：传入图片参数时自动切换为图生视频(I2V)模式

参考: 
- https://marketplace.dify.ai/plugins/allenwriter/doubao_image
- https://github.com/wwwzhouhui/sora2 (JXINCM Sora2)
"""

import time
import base64
import requests
from typing import Any, Generator
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class TextToVideoTool(Tool):
    """文本生成视频工具 - 三平台支持"""

    # ========== 阿里云百炼配置 ==========
    ALIYUN_API_BASE = "https://dashscope.aliyuncs.com/api/v1"
    ALIYUN_MODELS = {
        "wan2.5-t2v-preview": {"name": "通义万相 2.5 T2V", "type": "t2v"},
        "wan2.6-t2v": {"name": "通义万相 2.6 T2V", "type": "t2v"},
    }

    # ========== 火山方舟配置 ==========
    # 使用 Ark API (与官方 doubao_image 插件一致)
    VOLCENGINE_API_BASE = "https://ark.cn-beijing.volces.com/api/v3"
    VOLCENGINE_MODELS = {
        "doubao-seedance-1-0-lite-t2v-250428": {"name": "Seedance Lite T2V"},
        "doubao-seedance-1-5-pro-251215": {"name": "Seedance 1.5 Pro (推荐)"},
    }

    # ========== JXINCM (Sora2) 配置 ==========
    # 第三方服务 - https://github.com/wwwzhouhui/sora2
    JXINCM_API_BASE = "https://api.jxincm.cn/v1"
    JXINCM_MODELS = {
        "sora-2": {"name": "Sora-2 (标准)"},
        "sora-2-pro": {"name": "Sora-2 Pro (高质量)"},
    }
    
    # 阿里云分辨率映射 - 宽高比 -> size格式(宽*高)
    ALIYUN_SIZE_MAP = {
        "16:9": "1280*720",
        "9:16": "720*1280",
        "1:1": "720*720",
    }
    
    # wan2.6 支持的分辨率映射
    # 注意：阿里云 wan2.6-t2v 只支持 720p 和 1080p，480p 会自动回退到 720p
    ALIYUN_26_SIZE_MAP = {
        "480p": {
            # 阿里云不支持 480p，自动使用 720p 尺寸
            "16:9": "1280*720",
            "9:16": "720*1280",
            "1:1": "720*720",
        },
        "720p": {
            "16:9": "1280*720",
            "9:16": "720*1280",
            "1:1": "720*720",
        },
        "1080p": {
            "16:9": "1920*1080",
            "9:16": "1080*1920",
            "1:1": "1080*1080",
        }
    }

    # 轮询配置 - Dify 插件有 10 分钟硬性超时，设置 8 分钟以留出余量
    POLL_INTERVAL = 5  # 轮询间隔（秒）
    MAX_POLL_ATTEMPTS = 96  # 96 * 5 = 480秒 = 8分钟

    # ========== 图片处理方法（用于火山方舟 I2V 模式）==========
    def _extract_image_url(self, image_param: Any) -> tuple[str, str]:
        """从参数中提取图片URL，返回 (url, error)"""
        if not image_param:
            return "", ""  # 图片是可选的，没有图片不算错误
        
        if isinstance(image_param, str):
            url = image_param.strip()
            if url.startswith(("http://", "https://")):
                return url, ""
            return "", "图片URL格式无效"
        
        if isinstance(image_param, dict):
            url = image_param.get("url", "") or image_param.get("remote_url", "")
            if url:
                return url, ""
            return "", "文件对象中未找到有效的URL"
        
        return "", f"不支持的图片参数类型: {type(image_param)}"

    def _convert_to_internal_url(self, image_url: str) -> str:
        """将 Dify 外部文件 URL 转换为内部访问 URL"""
        dify_internal_url = self.runtime.credentials.get("dify_internal_url", "").strip()
        if not dify_internal_url:
            return image_url
        
        from urllib.parse import urlparse, urlunparse
        try:
            parsed = urlparse(image_url)
            internal_parsed = urlparse(dify_internal_url)
            new_url = urlunparse((
                internal_parsed.scheme or parsed.scheme,
                internal_parsed.netloc,
                parsed.path, parsed.params, parsed.query, parsed.fragment
            ))
            return new_url
        except Exception:
            return image_url

    def _convert_image_to_base64(self, image_url: str) -> tuple[str, str]:
        """下载图片并转换为Base64格式"""
        internal_url = self._convert_to_internal_url(image_url)
        
        try:
            response = requests.get(internal_url, timeout=30, stream=True)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            if not content_type.startswith('image/'):
                content_type = 'image/jpeg'
            image_format = content_type.split('/')[-1].lower()
            format_map = {'jpg': 'jpeg', 'png': 'png', 'webp': 'webp', 'gif': 'gif'}
            image_format = format_map.get(image_format, 'jpeg')
            base64_data = base64.b64encode(response.content).decode('utf-8')
            return f"data:image/{image_format};base64,{base64_data}", ""
        except Exception as e:
            if internal_url != image_url:
                try:
                    response = requests.get(image_url, timeout=30, stream=True)
                    response.raise_for_status()
                    content_type = response.headers.get('Content-Type', 'image/jpeg')
                    if not content_type.startswith('image/'):
                        content_type = 'image/jpeg'
                    image_format = content_type.split('/')[-1].lower()
                    format_map = {'jpg': 'jpeg', 'png': 'png', 'webp': 'webp', 'gif': 'gif'}
                    image_format = format_map.get(image_format, 'jpeg')
                    base64_data = base64.b64encode(response.content).decode('utf-8')
                    return f"data:image/{image_format};base64,{base64_data}", ""
                except Exception as e2:
                    return "", f"图片处理失败: {str(e2)}"
            return "", f"图片处理失败: {str(e)}"

    def _is_public_accessible_url(self, url: str) -> bool:
        """判断URL是否可被火山引擎公网访问"""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            host = parsed.hostname or ""
            private_patterns = [
                'localhost', '127.0.0.1', '127.', '10.',
                '172.16.', '172.17.', '172.18.', '172.19.',
                '172.20.', '172.21.', '172.22.', '172.23.',
                '172.24.', '172.25.', '172.26.', '172.27.',
                '172.28.', '172.29.', '172.30.', '172.31.',
                '192.168.', '169.254.',
            ]
            for pattern in private_patterns:
                if host.startswith(pattern) or host == pattern.rstrip('.'):
                    return False
            port = parsed.port
            if port and port not in [80, 443]:
                return False
            return True
        except Exception:
            return False

    def _invoke(
        self, tool_parameters: dict[str, Any]
    ) -> Generator[ToolInvokeMessage, None, None]:
        """
        执行工具调用 - 根据平台分发
        """
        provider = tool_parameters.get("provider", "aliyun")
        prompt = tool_parameters.get("prompt", "").strip()
        
        # 参数验证
        if not prompt:
            yield self.create_text_message("❌ 错误：视频描述不能为空")
            return
        
        # 处理图片参数（仅火山方舟支持）
        image_param = tool_parameters.get("image")
        image_url, img_error = self._extract_image_url(image_param)
        
        if img_error:
            yield self.create_text_message(f"❌ 错误：{img_error}")
            return
        
        # 如果阿里云平台传入了图片，提示用户使用专用工具
        if provider == "aliyun" and image_url:
            yield self.create_text_message(
                "⚠️ 阿里云百炼平台不支持在此工具中使用图片\n"
                "请使用【图片生成视频】工具进行图生视频操作"
            )
            return
        
        # 将图片URL存入参数供后续使用
        tool_parameters["_image_url"] = image_url
        
        # 根据平台分发调用
        if provider == "aliyun":
            yield from self._invoke_aliyun(tool_parameters)
        elif provider == "volcengine":
            yield from self._invoke_volcengine(tool_parameters)
        elif provider == "jxincm":
            yield from self._invoke_jxincm(tool_parameters)
        else:
            yield self.create_text_message(f"❌ 错误：不支持的平台 {provider}")

    # ========== 阿里云百炼实现 ==========
    def _invoke_aliyun(
        self, params: dict
    ) -> Generator[ToolInvokeMessage, None, None]:
        """
        调用阿里云百炼 DashScope API
        
        API文档：https://help.aliyun.com/zh/model-studio/video-generation-api-reference/
        
        支持的模型:
        - wan2.5-t2v-preview: 通义万相 2.5 (固定5秒)
        - wan2.6-t2v: 通义万相 2.6 (支持5/10/15秒，多分辨率)
        """
        # 获取凭证
        api_key = self.runtime.credentials.get("aliyun_api_key", "")
        if not api_key:
            yield self.create_text_message("❌ 错误：请配置阿里云百炼 API Key")
            return
        
        # 解析参数
        model = params.get("model", "wan2.5-t2v-preview")
        prompt = params.get("prompt", "")
        aspect_ratio = params.get("aspect_ratio", "16:9")
        duration = params.get("duration", "5")
        resolution = params.get("resolution", "720p")
        wait_for_completion = params.get("wait_for_completion", True)
        
        # wan2.6 专属参数
        prompt_extend = params.get("prompt_extend", False)  # 智能扩写
        multi_shot = params.get("multi_shot", False)  # 智能镜头（多镜头叙事）
        
        # 音频相关参数（wan2.5/wan2.6 支持）
        # 参考文档：https://help.aliyun.com/zh/model-studio/video-generation-api-reference/
        enable_audio = params.get("enable_audio", False)  # 启用自动配音（对应 API 的 audio 参数）
        narration = params.get("narration", "")  # 旁白文本（合并到 prompt 中）
        
        # 判断是否为 wan2.6 模型
        is_wan26 = model.startswith("wan2.6")
        
        # 阿里云支持的宽高比
        aliyun_supported_ratios = ["16:9", "9:16", "1:1"]
        ratio_warning = ""
        
        # 检查宽高比是否支持
        if aspect_ratio not in aliyun_supported_ratios:
            original_ratio = aspect_ratio
            # 回退到最接近的支持比例
            if aspect_ratio in ["21:9", "4:3"]:
                aspect_ratio = "16:9"  # 横屏回退到 16:9
            elif aspect_ratio == "3:4":
                aspect_ratio = "9:16"  # 竖屏回退到 9:16
            ratio_warning = f"⚠️ 阿里云不支持 {original_ratio}，已自动调整为 {aspect_ratio}\n"
        
        # 宽高比映射到size (宽*高格式)
        if is_wan26:
            # wan2.6 支持多分辨率
            size_map = self.ALIYUN_26_SIZE_MAP.get(resolution, self.ALIYUN_26_SIZE_MAP["720p"])
            size = size_map.get(aspect_ratio, "1280*720")
        else:
            # wan2.5 使用固定映射
            size = self.ALIYUN_SIZE_MAP.get(aspect_ratio, "1280*720")
        
        model_name = self.ALIYUN_MODELS.get(model, {}).get("name", model)
        
        # 构建提示信息
        info_text = (
            f"🚀 **提交视频生成任务**\n\n"
            f"🏢 平台: 阿里云百炼\n"
            f"📝 模型: {model_name}\n"
        )
        if ratio_warning:
            info_text += ratio_warning
        info_text += f"📐 宽高比: {aspect_ratio} ({size})\n"
        if is_wan26:
            info_text += f"📺 分辨率: {resolution}\n"
            info_text += f"⏱️ 时长: {duration}秒\n"
            # 显示 wan2.6 专属功能状态
            features = []
            if prompt_extend:
                features.append("智能扩写")
            if multi_shot:
                features.append("智能镜头")
            if features:
                info_text += f"✨ 增强功能: {', '.join(features)}\n"
        # 音频相关信息
        if enable_audio:
            info_text += f"🎤 配音: 自动生成\n"
        if narration:
            info_text += f"📜 旁白: {narration[:30]}{'...' if len(narration) > 30 else ''}\n"
        info_text += f"💬 提示词: {prompt[:80]}{'...' if len(prompt) > 80 else ''}"
        
        yield self.create_text_message(info_text)
        
        # 构建请求
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"  # 启用异步模式
        }
        
        # 构建请求体
        payload = {
            "model": model,
            "input": {"prompt": prompt},
            "parameters": {
                "size": size
            }
        }
        
        # wan2.5/wan2.6 支持音频参数
        if model.startswith("wan2.5") or is_wan26:
            # audio参数：True=启用自动配音（语音旁白）
            if enable_audio:
                payload["parameters"]["audio"] = True
        
        # wan2.6 支持额外参数
        if is_wan26:
            payload["parameters"]["duration"] = int(duration)
            # 智能扩写：自动优化提示词
            if prompt_extend:
                payload["parameters"]["prompt_extend"] = True
            # 智能镜头：多镜头叙事，保持主体一致
            if multi_shot:
                payload["parameters"]["multi_shot"] = True
            # 如果有旁白文本，将其合并到prompt中帮助模型理解配音内容
            if narration and enable_audio:
                enhanced_prompt = f"{prompt}。旁白内容：{narration}"
                payload["input"]["prompt"] = enhanced_prompt
        
        try:
            # 提交任务 - 使用 video-synthesis 端点
            response = requests.post(
                f"{self.ALIYUN_API_BASE}/services/aigc/video-generation/video-synthesis",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            result = response.json()
            
            # 检查错误
            if response.status_code != 200:
                error_msg = result.get("message", str(result))
                yield self.create_text_message(f"❌ 提交失败: {error_msg}")
                yield self.create_json_message({
                    "success": False,
                    "provider": "aliyun",
                    "error_message": error_msg
                })
                return
            
            # 获取任务ID
            task_id = result.get("output", {}).get("task_id")
            if not task_id:
                yield self.create_text_message(f"❌ 提交失败: 未获取到任务ID - {result}")
                return
            
            yield self.create_text_message(f"✅ 任务已提交\n🔖 任务ID: `{task_id}`")
            
            # 是否等待完成
            if wait_for_completion:
                yield from self._poll_aliyun(api_key, task_id, model)
            else:
                yield self.create_json_message({
                    "success": True,
                    "provider": "aliyun",
                    "model": model,
                    "task_id": task_id,
                    "status": "PENDING"
                })
                
        except requests.Timeout:
            yield self.create_text_message("❌ 错误: 请求超时")
        except requests.RequestException as e:
            yield self.create_text_message(f"❌ 网络错误: {str(e)}")
        except Exception as e:
            yield self.create_text_message(f"❌ 错误: {str(e)}")

    def _poll_aliyun(
        self, api_key: str, task_id: str, model: str
    ) -> Generator[ToolInvokeMessage, None, None]:
        """
        轮询阿里云任务状态
        """
        headers = {"Authorization": f"Bearer {api_key}"}
        
        for attempt in range(self.MAX_POLL_ATTEMPTS):
            try:
                response = requests.get(
                    f"{self.ALIYUN_API_BASE}/tasks/{task_id}",
                    headers=headers,
                    timeout=30
                )
                
                output = response.json().get("output", {})
                status = output.get("task_status", "UNKNOWN")
                
                if status == "SUCCEEDED":
                    video_url = output.get("video_url", "")
                    cover_url = output.get("cover_url", "")
                    
                    # 方案2：视频URL放在最前面，便于工作流提取
                    yield self.create_text_message(
                        f"{video_url}\n\n"
                        f"---\n"
                        f"🎉 **视频生成完成！**\n"
                        f"📹 视频链接已在上方（可直接复制使用）\n"
                        f"🖼️ 封面: {cover_url}"
                    )
                    yield self.create_json_message({
                        "success": True,
                        "provider": "aliyun",
                        "model": model,
                        "task_id": task_id,
                        "status": "SUCCEEDED",
                        "video_url": video_url,
                        "cover_url": cover_url
                    })
                    return
                    
                elif status == "FAILED":
                    error_msg = output.get("message", "未知错误")
                    yield self.create_text_message(f"❌ 视频生成失败: {error_msg}")
                    yield self.create_json_message({
                        "success": False,
                        "provider": "aliyun",
                        "model": model,
                        "task_id": task_id,
                        "status": "FAILED",
                        "error_message": error_msg
                    })
                    return
                    
                else:
                    # 每30秒输出一次进度
                    if attempt % 6 == 0:
                        elapsed = attempt * self.POLL_INTERVAL
                        yield self.create_text_message(
                            f"⏳ 正在生成... {status} ({elapsed}秒)"
                        )
                    time.sleep(self.POLL_INTERVAL)
                    
            except Exception as e:
                time.sleep(self.POLL_INTERVAL)
        
        # 超时 - 任务仍在进行中
        yield self.create_text_message(
            f"⏰ 视频生成仍在进行中，已超过等待时间\n"
            f"🔖 任务ID: `{task_id}`\n\n"
            f"💡 请使用【查询任务状态】工具，输入以下信息查询结果：\n"
            f"   - 平台: aliyun\n"
            f"   - 任务ID: {task_id}"
        )
        yield self.create_json_message({
            "success": True,  # 改为 True，因为任务仍在进行中
            "provider": "aliyun",
            "model": model,
            "task_id": task_id,
            "status": "RUNNING",
            "error_message": "等待超时，任务仍在进行中，请使用query_task查询结果"
        })

    # ========== 火山方舟实现 (使用 Ark API) ==========
    def _invoke_volcengine(
        self, params: dict
    ) -> Generator[ToolInvokeMessage, None, None]:
        """
        调用火山方舟 Ark API - 支持文生视频(T2V)和图生视频(I2V)
        
        API: https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks
        - T2V: content 只包含 text
        - I2V: content 包含 image_url + text
        """
        # 获取凭证
        api_key = self.runtime.credentials.get("volcengine_api_key", "")
        if not api_key:
            yield self.create_text_message("❌ 错误：请配置火山方舟 API Key")
            return
        
        # 获取 endpoint_id，如果配置了则使用 endpoint_id，否则使用 model 名称
        endpoint_id = self.runtime.credentials.get("volcengine_endpoint_id", "").strip()
        
        # 解析参数
        original_model = params.get("model", "doubao-seedance-1-0-lite-t2v-250428")
        
        # 火山方舟 Ark API 需要使用 endpoint_id 作为 model 参数
        # 保存原始 model 用于显示，使用 endpoint_id 作为 API 调用的 model
        if endpoint_id:
            model = endpoint_id  # API 调用使用 endpoint_id
        else:
            model = original_model  # 没有 endpoint_id 时使用原始 model
        prompt = params.get("prompt", "")
        duration = params.get("duration", "5")
        aspect_ratio = params.get("aspect_ratio", "16:9")
        resolution = params.get("resolution", "1080p")
        camera_control = params.get("camera_control", "auto")
        wait_for_completion = params.get("wait_for_completion", True)
        
        # 检查是否有图片参数（I2V 模式）
        image_url = params.get("_image_url", "")
        is_i2v_mode = bool(image_url)
        final_image_url = ""
        need_base64 = False
        
        # 处理图片（如果是 I2V 模式）
        if is_i2v_mode:
            need_base64 = not self._is_public_accessible_url(image_url)
            if need_base64:
                yield self.create_text_message("🔄 检测到内网图片地址，正在转换为Base64格式...")
                base64_url, error = self._convert_image_to_base64(image_url)
                if error:
                    yield self.create_text_message(f"❌ 图片转换失败: {error}")
                    return
                final_image_url = base64_url
                yield self.create_text_message("✅ 图片转换成功")
            else:
                final_image_url = image_url
        
        # 构建带参数的 prompt (火山方舟使用命令行参数格式)
        full_prompt = prompt
        # 添加视频比例（文生视频时）
        if not is_i2v_mode and aspect_ratio and "--ratio" not in prompt:
            full_prompt = f"{full_prompt} --ratio {aspect_ratio}"
        # 添加时长
        if duration and "--duration" not in prompt and "--dur" not in prompt:
            full_prompt = f"{full_prompt} --duration {duration}"
        # 添加分辨率
        if resolution and "--resolution" not in prompt:
            full_prompt = f"{full_prompt} --resolution {resolution}"
        # 添加镜头控制（固定镜头）
        if camera_control == "fixed" and "--camera" not in prompt:
            full_prompt = f"{full_prompt} --camera fixed"
        
        # 显示时使用原始 model 的名称（如果存在），否则使用 endpoint_id
        model_name = self.VOLCENGINE_MODELS.get(original_model, {}).get("name", original_model)
        if endpoint_id and original_model != endpoint_id:
            model_name = f"{model_name} (Endpoint: {endpoint_id[:20]}...)" if len(endpoint_id) > 20 else f"{model_name} (Endpoint: {endpoint_id})"
        mode_text = "图生视频 (I2V)" if is_i2v_mode else "文生视频 (T2V)"
        
        info_text = (
            f"🚀 **提交{mode_text}任务**\n\n"
            f"🏢 平台: 火山方舟\n"
            f"📝 模型: {model_name}\n"
            f"📺 分辨率: {resolution}\n"
            f"⏱️ 时长: {duration}秒\n"
        )
        if is_i2v_mode:
            info_text += f"🖼️ 图片: {'Base64' if need_base64 else '公网URL'}\n"
        else:
            info_text += f"📐 宽高比: {aspect_ratio}\n"
        if camera_control == "fixed":
            info_text += f"📷 镜头: 固定\n"
        info_text += f"💬 提示词: {prompt[:80]}{'...' if len(prompt) > 80 else ''}"
        
        yield self.create_text_message(info_text)
        
        # 构建请求头
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建请求体 - 根据模式选择 T2V 或 I2V
        if is_i2v_mode:
            # I2V 模式：包含图片 + 文本
            payload = {
                "model": model,
                "content": [
                    {"type": "image_url", "image_url": {"url": final_image_url}},
                    {"type": "text", "text": full_prompt}
                ]
            }
        else:
            # T2V 模式：只有文本
            payload = {
                "model": model,
                "content": [
                    {"type": "text", "text": full_prompt}
                ]
            }
        
        try:
            # 提交任务
            response = requests.post(
                f"{self.VOLCENGINE_API_BASE}/contents/generations/tasks",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                yield self.create_text_message(f"❌ 提交失败: {response.status_code} - {response.text}")
                yield self.create_json_message({
                    "success": False,
                    "provider": "volcengine",
                    "error_message": response.text
                })
                return
            
            result = response.json()
            
            # 获取任务ID
            task_id = result.get("id")
            if not task_id:
                yield self.create_text_message(f"❌ 提交失败: 未获取到任务ID - {result}")
                return
            
            yield self.create_text_message(f"✅ 任务已提交\n🔖 任务ID: `{task_id}`")
            
            # 是否等待完成
            if wait_for_completion:
                yield from self._poll_volcengine(api_key, task_id, model)
            else:
                yield self.create_json_message({
                    "success": True,
                    "provider": "volcengine",
                    "model": model,
                    "task_id": task_id,
                    "status": "running"
                })
                
        except requests.Timeout:
            yield self.create_text_message("❌ 错误: 请求超时")
        except requests.RequestException as e:
            yield self.create_text_message(f"❌ 网络错误: {str(e)}")
        except Exception as e:
            yield self.create_text_message(f"❌ 错误: {str(e)}")

    def _poll_volcengine(
        self, api_key: str, task_id: str, model: str
    ) -> Generator[ToolInvokeMessage, None, None]:
        """
        轮询火山方舟任务状态 (Ark API)
        
        状态: running, succeeded, failed, canceled
        """
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        for attempt in range(self.MAX_POLL_ATTEMPTS):
            try:
                # 查询任务状态 - GET 请求
                response = requests.get(
                    f"{self.VOLCENGINE_API_BASE}/contents/generations/tasks/{task_id}",
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code != 200:
                    yield self.create_text_message(f"❌ 查询失败: {response.status_code} - {response.text}")
                    yield self.create_json_message({
                        "success": False,
                        "provider": "volcengine",
                        "model": model,
                        "task_id": task_id,
                        "status": "failed",
                        "error_message": response.text
                    })
                    return
                
                result = response.json()
                status = result.get("status", "unknown")
                
                if status == "succeeded":
                    # 获取视频URL
                    video_url = result.get("content", {}).get("video_url", "")
                    
                    # 方案2：视频URL放在最前面，便于工作流提取
                    yield self.create_text_message(
                        f"{video_url}\n\n"
                        f"---\n"
                        f"🎉 **视频生成完成！**\n"
                        f"📹 视频链接已在上方（可直接复制使用）\n"
                        f"⚠️ 视频链接有效期24小时，请及时下载保存"
                    )
                    # 显示视频预览
                    if video_url:
                        yield self.create_image_message(video_url)
                    yield self.create_json_message({
                        "success": True,
                        "provider": "volcengine",
                        "model": model,
                        "task_id": task_id,
                        "status": "succeeded",
                        "video_url": video_url
                    })
                    return
                    
                elif status == "failed":
                    error_msg = result.get("error", {}).get("message", "未知错误")
                    yield self.create_text_message(f"❌ 视频生成失败: {error_msg}")
                    yield self.create_json_message({
                        "success": False,
                        "provider": "volcengine",
                        "model": model,
                        "task_id": task_id,
                        "status": "failed",
                        "error_message": error_msg
                    })
                    return
                
                elif status == "canceled":
                    yield self.create_text_message("❌ 任务已被取消")
                    yield self.create_json_message({
                        "success": False,
                        "provider": "volcengine",
                        "model": model,
                        "task_id": task_id,
                        "status": "canceled",
                        "error_message": "任务已被取消"
                    })
                    return
                    
                else:
                    # 每30秒输出一次进度
                    if attempt % 6 == 0:
                        elapsed = attempt * self.POLL_INTERVAL
                        yield self.create_text_message(
                            f"⏳ 正在生成... ({elapsed}秒)"
                        )
                    time.sleep(self.POLL_INTERVAL)
                    
            except Exception as e:
                time.sleep(self.POLL_INTERVAL)
        
        # 超时 - 任务仍在进行中
        yield self.create_text_message(
            f"⏰ 视频生成仍在进行中，已超过等待时间\n"
            f"🔖 任务ID: `{task_id}`\n\n"
            f"💡 请使用【查询任务状态】工具，输入以下信息查询结果：\n"
            f"   - 平台: volcengine\n"
            f"   - 任务ID: {task_id}"
        )
        yield self.create_json_message({
            "success": True,  # 改为 True，因为任务仍在进行中
            "provider": "volcengine",
            "model": model,
            "task_id": task_id,
            "status": "running",
            "error_message": "等待超时，任务仍在进行中，请使用query_task查询结果"
        })

    # ========== JXINCM (Sora2) 实现 ==========
    def _invoke_jxincm(
        self, params: dict
    ) -> Generator[ToolInvokeMessage, None, None]:
        """
        调用 JXINCM Sora-2 API (第三方服务)
        
        API文档参考: https://github.com/wwwzhouhui/sora2
        
        支持的模型:
        - sora-2: 标准质量
        - sora-2-pro: 高质量
        
        注意：视频时长固定为15秒
        """
        # 获取凭证
        api_key = self.runtime.credentials.get("jxincm_api_key", "")
        if not api_key:
            yield self.create_text_message("❌ 错误：请配置 JXINCM API Key")
            return
        
        # 解析参数
        model = params.get("model", "sora-2")
        prompt = params.get("prompt", "")
        orientation = params.get("orientation", "landscape")
        watermark = params.get("watermark", False)
        wait_for_completion = params.get("wait_for_completion", True)
        
        # 检查是否有图片参数（I2V 模式）
        image_url = params.get("_image_url", "")
        is_i2v_mode = bool(image_url)
        image_urls = [image_url] if is_i2v_mode else []
        
        model_name = self.JXINCM_MODELS.get(model, {}).get("name", model)
        mode_text = "图生视频 (I2V)" if is_i2v_mode else "文生视频 (T2V)"
        
        info_text = (
            f"🚀 **提交{mode_text}任务**\n\n"
            f"⚠️ **注意：这是第三方服务，稳定性不做保证**\n\n"
            f"🏢 平台: JXINCM (Sora2)\n"
            f"📝 模型: {model_name}\n"
            f"📐 方向: {'横屏' if orientation == 'landscape' else '竖屏'}\n"
            f"⏱️ 时长: 15秒 (固定)\n"
        )
        if is_i2v_mode:
            info_text += f"🖼️ 图片: {image_url[:50]}...\n"
        if watermark:
            info_text += f"💧 水印: 已开启\n"
        info_text += f"💬 提示词: {prompt[:80]}{'...' if len(prompt) > 80 else ''}"
        
        yield self.create_text_message(info_text)
        
        # 构建请求头
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建请求体
        payload = {
            "prompt": prompt,
            "model": model,
            "orientation": orientation,
            "size": "large",
            "duration": 15,
            "watermark": watermark,
            "private": True,
            "images": image_urls
        }
        
        try:
            # 提交任务
            response = requests.post(
                f"{self.JXINCM_API_BASE}/video/create",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                error_text = response.text
                try:
                    error_json = response.json()
                    error_text = error_json.get("error", {}).get("message", error_text)
                except Exception:
                    pass
                yield self.create_text_message(f"❌ 提交失败: {response.status_code} - {error_text}")
                yield self.create_json_message({
                    "success": False,
                    "provider": "jxincm",
                    "error_message": error_text
                })
                return
            
            result = response.json()
            
            # 获取任务ID
            task_id = result.get("id")
            if not task_id:
                yield self.create_text_message(f"❌ 提交失败: 未获取到任务ID - {result}")
                return
            
            yield self.create_text_message(f"✅ 任务已提交\n🔖 任务ID: `{task_id}`")
            
            # 是否等待完成
            if wait_for_completion:
                yield from self._poll_jxincm(api_key, task_id, model)
            else:
                yield self.create_json_message({
                    "success": True,
                    "provider": "jxincm",
                    "model": model,
                    "task_id": task_id,
                    "status": "running"
                })
                
        except requests.Timeout:
            yield self.create_text_message("❌ 错误: 请求超时")
        except requests.RequestException as e:
            yield self.create_text_message(f"❌ 网络错误: {str(e)}")
        except Exception as e:
            yield self.create_text_message(f"❌ 错误: {str(e)}")

    def _poll_jxincm(
        self, api_key: str, task_id: str, model: str
    ) -> Generator[ToolInvokeMessage, None, None]:
        """
        轮询 JXINCM 任务状态
        
        状态: queued, processing, completed, failed
        """
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        for attempt in range(self.MAX_POLL_ATTEMPTS):
            try:
                # 查询任务状态
                response = requests.get(
                    f"{self.JXINCM_API_BASE}/video/query?id={task_id}",
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code != 200:
                    yield self.create_text_message(f"❌ 查询失败: {response.status_code} - {response.text}")
                    yield self.create_json_message({
                        "success": False,
                        "provider": "jxincm",
                        "model": model,
                        "task_id": task_id,
                        "status": "failed",
                        "error_message": response.text
                    })
                    return
                
                result = response.json()
                status = result.get("status", "unknown")
                progress = result.get("progress", 0)
                
                if status == "completed":
                    # 获取视频信息
                    detail = result.get("detail", {})
                    video_url = detail.get("url", "")
                    thumbnail_url = detail.get("thumbnail", "")
                    gif_url = detail.get("gif", "")
                    
                    # 视频URL放在最前面，便于工作流提取
                    yield self.create_text_message(
                        f"{video_url}\n\n"
                        f"---\n"
                        f"🎉 **视频生成完成！**\n"
                        f"📹 视频链接已在上方（可直接复制使用）\n"
                        f"🖼️ 缩略图: {thumbnail_url}\n"
                        f"🎬 GIF预览: {gif_url}"
                    )
                    # 显示视频预览
                    if video_url:
                        yield self.create_image_message(video_url)
                    yield self.create_json_message({
                        "success": True,
                        "provider": "jxincm",
                        "model": model,
                        "task_id": task_id,
                        "status": "completed",
                        "video_url": video_url,
                        "thumbnail_url": thumbnail_url,
                        "gif_url": gif_url
                    })
                    return
                    
                elif status == "failed":
                    error_msg = result.get("error", {}).get("message", "未知错误")
                    yield self.create_text_message(f"❌ 视频生成失败: {error_msg}")
                    yield self.create_json_message({
                        "success": False,
                        "provider": "jxincm",
                        "model": model,
                        "task_id": task_id,
                        "status": "failed",
                        "error_message": error_msg
                    })
                    return
                    
                else:
                    # 每30秒输出一次进度
                    if attempt % 6 == 0:
                        elapsed = attempt * self.POLL_INTERVAL
                        yield self.create_text_message(
                            f"⏳ 正在生成... {status} ({progress}% - {elapsed}秒)"
                        )
                    time.sleep(self.POLL_INTERVAL)
                    
            except Exception as e:
                time.sleep(self.POLL_INTERVAL)
        
        # 超时 - 任务仍在进行中
        yield self.create_text_message(
            f"⏰ 视频生成仍在进行中，已超过等待时间\n"
            f"🔖 任务ID: `{task_id}`\n\n"
            f"💡 请使用【查询任务状态】工具，输入以下信息查询结果：\n"
            f"   - 平台: jxincm\n"
            f"   - 任务ID: {task_id}"
        )
        yield self.create_json_message({
            "success": True,
            "provider": "jxincm",
            "model": model,
            "task_id": task_id,
            "status": "running",
            "error_message": "等待超时，任务仍在进行中，请使用query_task查询结果"
        })
