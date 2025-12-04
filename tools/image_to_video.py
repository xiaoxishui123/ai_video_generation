"""
图片生成视频工具 (Image-to-Video)

支持双平台：
- 阿里云百炼：通义万相 wan2.5-i2v-preview
- 火山方舟：豆包 Seaweed I2V 模型

参考: https://marketplace.dify.ai/plugins/allenwriter/doubao_image
"""

import time
import base64
import requests
from typing import Any, Generator
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class ImageToVideoTool(Tool):
    """图片生成视频工具 - 双平台支持"""

    # ========== 阿里云百炼配置 ==========
    ALIYUN_API_BASE = "https://dashscope.aliyuncs.com/api/v1"
    ALIYUN_MODELS = {
        "wan2.5-i2v-preview": {"name": "通义万相 I2V", "type": "i2v"},
    }

    # ========== 火山方舟配置 ==========
    VOLCENGINE_API_BASE = "https://ark.cn-beijing.volces.com/api/v3"
    VOLCENGINE_MODELS = {
        "doubao-seaweed-241128": {"name": "Seaweed I2V"},
    }

    # 阿里云分辨率映射 - 宽高比 -> size格式(宽*高)
    ALIYUN_SIZE_MAP = {
        "16:9": "1280*720",
        "9:16": "720*1280",
        "1:1": "720*720",
    }

    # 轮询配置
    POLL_INTERVAL = 5
    MAX_POLL_ATTEMPTS = 120

    def _convert_image_to_base64(self, image_url: str) -> tuple[str, str]:
        """下载图片并转换为Base64格式"""
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
        except Exception as e:
            return "", f"图片处理失败: {str(e)}"

    def _is_public_accessible_url(self, url: str) -> bool:
        """判断URL是否可能是公网可访问的"""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            host = parsed.hostname or ""
            private_patterns = ['localhost', '127.0.0.1', '10.', '172.16.', '172.17.', '172.18.', 
                '172.19.', '172.20.', '172.21.', '172.22.', '172.23.', '172.24.', '172.25.', 
                '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.', '192.168.']
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
        """执行工具调用"""
        provider = tool_parameters.get("provider", "aliyun")
        image_url = tool_parameters.get("image_url", "").strip()
        
        if not image_url:
            yield self.create_text_message("❌ 错误：图片URL不能为空")
            return
        
        if not image_url.startswith(("http://", "https://")):
            yield self.create_text_message("❌ 错误：图片URL格式无效")
            return
        
        if provider == "aliyun":
            yield from self._invoke_aliyun(tool_parameters)
        elif provider == "volcengine":
            yield from self._invoke_volcengine(tool_parameters)
        else:
            yield self.create_text_message(f"❌ 错误：不支持的平台 {provider}")

    # ========== 阿里云百炼实现 ==========
    def _invoke_aliyun(
        self, params: dict
    ) -> Generator[ToolInvokeMessage, None, None]:
        """调用阿里云百炼 DashScope API (图生视频)"""
        api_key = self.runtime.credentials.get("aliyun_api_key", "")
        if not api_key:
            yield self.create_text_message("❌ 错误：请配置阿里云百炼 API Key")
            return
        
        model = params.get("model", "wan2.5-i2v-preview")
        image_url = params.get("image_url", "")
        prompt = params.get("prompt", "让图片动起来")
        aspect_ratio = params.get("aspect_ratio", "16:9")
        wait_for_completion = params.get("wait_for_completion", True)
        
        size = self.ALIYUN_SIZE_MAP.get(aspect_ratio, "1280*720")
        
        model_name = self.ALIYUN_MODELS.get(model, {}).get("name", model)
        yield self.create_text_message(
            f"🚀 **提交图生视频任务**\n\n"
            f"🏢 平台: 阿里云百炼\n"
            f"📝 模型: {model_name}\n"
            f"🖼️ 图片: {image_url[:60]}...\n"
            f"📐 分辨率: {size}\n"
            f"💬 描述: {prompt[:50]}..."
        )
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"
        }
        
        payload = {
            "model": model,
            "input": {
                "prompt": prompt,
                "image_url": image_url
            },
            "parameters": {
                "size": size
            }
        }
        
        try:
            response = requests.post(
                f"{self.ALIYUN_API_BASE}/services/aigc/video-generation/generation",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            result = response.json()
            
            if response.status_code != 200:
                error_msg = result.get("message", str(result))
                yield self.create_text_message(f"❌ 提交失败: {error_msg}")
                yield self.create_json_message({
                    "success": False,
                    "provider": "aliyun",
                    "error_message": error_msg
                })
                return
            
            task_id = result.get("output", {}).get("task_id")
            if not task_id:
                yield self.create_text_message(f"❌ 提交失败: 未获取到任务ID")
                return
            
            yield self.create_text_message(f"✅ 任务已提交\n🔖 任务ID: `{task_id}`")
            
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
        except Exception as e:
            yield self.create_text_message(f"❌ 错误: {str(e)}")

    def _poll_aliyun(
        self, api_key: str, task_id: str, model: str
    ) -> Generator[ToolInvokeMessage, None, None]:
        """轮询阿里云任务状态"""
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
                    if attempt % 6 == 0:
                        elapsed = attempt * self.POLL_INTERVAL
                        yield self.create_text_message(f"⏳ 正在生成... {status} ({elapsed}秒)")
                    time.sleep(self.POLL_INTERVAL)
                    
            except Exception:
                time.sleep(self.POLL_INTERVAL)
        
        yield self.create_text_message(f"⏰ 任务超时\n🔖 任务ID: `{task_id}`")
        yield self.create_json_message({
            "success": False,
            "provider": "aliyun",
            "model": model,
            "task_id": task_id,
            "status": "TIMEOUT",
            "error_message": "任务超时"
        })

    # ========== 火山方舟实现 (Ark API) ==========
    def _invoke_volcengine(
        self, params: dict
    ) -> Generator[ToolInvokeMessage, None, None]:
        """调用火山方舟 Ark API (图生视频)"""
        api_key = self.runtime.credentials.get("volcengine_api_key", "")
        if not api_key:
            yield self.create_text_message("❌ 错误：请配置火山方舟 API Key")
            return
        
        model = params.get("model", "doubao-seaweed-241128")
        image_url = params.get("image_url", "")
        prompt = params.get("prompt", "让图片动起来")
        duration = params.get("duration", "5")
        wait_for_completion = params.get("wait_for_completion", True)
        
        # 构建带参数的 prompt
        full_prompt = f"{prompt} --duration {duration}"
        model_name = self.VOLCENGINE_MODELS.get(model, {}).get("name", model)
        
        # 检查图片URL是否公网可访问，如果不是则转换为Base64
        final_image_url = image_url
        if not self._is_public_accessible_url(image_url):
            yield self.create_text_message(f"🔄 检测到内网图片地址，正在转换为Base64格式...")
            base64_url, error = self._convert_image_to_base64(image_url)
            if error:
                yield self.create_text_message(f"❌ 图片转换失败: {error}")
                return
            final_image_url = base64_url
            yield self.create_text_message(f"✅ 图片转换成功")
        
        yield self.create_text_message(
            f"🚀 **提交图生视频任务**\n\n"
            f"🏢 平台: 火山方舟\n"
            f"📝 模型: {model_name}\n"
            f"🖼️ 图片: {'Base64' if final_image_url.startswith('data:') else image_url[:60]}\n"
            f"⏱️ 时长: {duration}秒\n"
            f"💬 描述: {prompt[:50]}..."
        )
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Ark API 格式 - 图生视频
        payload = {
            "model": model,
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": final_image_url}
                },
                {
                    "type": "text",
                    "text": full_prompt
                }
            ]
        }
        
        try:
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
            task_id = result.get("id")
            if not task_id:
                yield self.create_text_message(f"❌ 提交失败: 未获取到任务ID")
                return
            
            yield self.create_text_message(f"✅ 任务已提交\n🔖 任务ID: `{task_id}`")
            
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
        except Exception as e:
            yield self.create_text_message(f"❌ 错误: {str(e)}")

    def _poll_volcengine(
        self, api_key: str, task_id: str, model: str
    ) -> Generator[ToolInvokeMessage, None, None]:
        """轮询火山方舟任务状态 (Ark API)"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        for attempt in range(self.MAX_POLL_ATTEMPTS):
            try:
                response = requests.get(
                    f"{self.VOLCENGINE_API_BASE}/contents/generations/tasks/{task_id}",
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code != 200:
                    yield self.create_text_message(f"❌ 查询失败: {response.text}")
                    return
                
                result = response.json()
                status = result.get("status", "unknown")
                
                if status == "succeeded":
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
                    return
                    
                else:
                    if attempt % 6 == 0:
                        elapsed = attempt * self.POLL_INTERVAL
                        yield self.create_text_message(f"⏳ 正在生成... ({elapsed}秒)")
                    time.sleep(self.POLL_INTERVAL)
                    
            except Exception:
                time.sleep(self.POLL_INTERVAL)
        
        yield self.create_text_message(f"⏰ 任务超时\n🔖 任务ID: `{task_id}`")
        yield self.create_json_message({
            "success": False,
            "provider": "volcengine",
            "model": model,
            "task_id": task_id,
            "status": "timeout",
            "error_message": "任务超时"
        })
