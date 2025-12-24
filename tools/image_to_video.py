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
        "wan2.5-i2v-preview": {"name": "通义万相 2.5 I2V", "type": "i2v"},
        "wan2.6-i2v": {"name": "通义万相 2.6 I2V", "type": "i2v"},
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
    
    # wan2.6 支持的分辨率映射 (支持480p/720p/1080p)
    ALIYUN_26_SIZE_MAP = {
        "480p": {
            "16:9": "832*480",
            "9:16": "480*832",
            "1:1": "480*480",
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
    POLL_INTERVAL = 5
    MAX_POLL_ATTEMPTS = 96  # 96 * 5 = 480秒 = 8分钟

    def _convert_to_internal_url(self, image_url: str) -> str:
        """将 Dify 外部文件 URL 转换为内部访问 URL"""
        dify_internal_url = self.runtime.credentials.get("dify_internal_url", "").strip()
        if not dify_internal_url:
            return image_url
        
        from urllib.parse import urlparse, urlunparse
        try:
            parsed = urlparse(image_url)
            internal_parsed = urlparse(dify_internal_url)
            # 替换 scheme、host 和 port，保留 path、query 和 fragment
            new_url = urlunparse((
                internal_parsed.scheme or parsed.scheme,
                internal_parsed.netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            return new_url
        except Exception:
            return image_url

    def _convert_image_to_base64(self, image_url: str) -> tuple[str, str]:
        """下载图片并转换为Base64格式"""
        # 尝试转换为内部 URL
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
            # 如果内部 URL 失败且与原 URL 不同，尝试原 URL
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
                    return "", f"图片处理失败: 内部URL({internal_url})错误:{str(e)}, 原URL错误:{str(e2)}"
            return "", f"图片处理失败: {str(e)}"

    def _is_public_accessible_url(self, url: str) -> bool:
        """判断URL是否可能被火山引擎公网访问
        
        注意：Dify 生成的图片 URL 通常带有签名参数，且使用非标准端口(如 8080)
        火山引擎服务器可能无法访问这些 URL，因此需要转换为 Base64
        
        只有标准端口(80/443)的公网 URL 才认为是可直接访问的
        """
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            host = parsed.hostname or ""
            
            # 私有网络地址（一定需要转 Base64）
            private_patterns = [
                'localhost', '127.0.0.1', '127.',  # 本地回环
                '10.',                               # 10.0.0.0/8
                '172.16.', '172.17.', '172.18.', '172.19.',  # 172.16.0.0/12
                '172.20.', '172.21.', '172.22.', '172.23.', 
                '172.24.', '172.25.', '172.26.', '172.27.', 
                '172.28.', '172.29.', '172.30.', '172.31.', 
                '192.168.',                          # 192.168.0.0/16
                '169.254.',                          # 链路本地
            ]
            
            for pattern in private_patterns:
                if host.startswith(pattern) or host == pattern.rstrip('.'):
                    return False
            
            # 非标准端口也需要转 Base64（火山引擎可能无法访问带签名的 Dify URL）
            port = parsed.port
            if port and port not in [80, 443]:
                return False
            
            return True
        except Exception:
            return False

    def _extract_image_url(self, image_param: Any) -> tuple[str, str]:
        """从参数中提取图片URL，返回 (url, error)"""
        if not image_param:
            return "", "图片参数为空"
        
        # 如果是字符串，直接作为 URL
        if isinstance(image_param, str):
            url = image_param.strip()
            if url.startswith(("http://", "https://")):
                return url, ""
            return "", "图片URL格式无效"
        
        # 如果是 Dify 文件对象（字典）
        if isinstance(image_param, dict):
            # 优先使用 url 字段
            url = image_param.get("url", "")
            if url:
                return url, ""
            # 其次使用 remote_url 字段
            url = image_param.get("remote_url", "")
            if url:
                return url, ""
            return "", "文件对象中未找到有效的URL"
        
        return "", f"不支持的图片参数类型: {type(image_param)}"

    def _invoke(
        self, tool_parameters: dict[str, Any]
    ) -> Generator[ToolInvokeMessage, None, None]:
        """执行工具调用"""
        provider = tool_parameters.get("provider", "aliyun")
        
        # 兼容 image (file类型) 和 image_url (string类型)
        image_param = tool_parameters.get("image") or tool_parameters.get("image_url")
        image_url, error = self._extract_image_url(image_param)
        
        if error:
            yield self.create_text_message(f"❌ 错误：{error}")
            return
        
        # 将提取的 URL 放回参数中供后续使用
        tool_parameters["image_url"] = image_url
        
        if provider == "aliyun":
            yield from self._invoke_aliyun(tool_parameters)
        elif provider == "volcengine":
            yield from self._invoke_volcengine(tool_parameters)
        else:
            yield self.create_text_message(f"❌ 错误：不支持的平台 {provider}")

    def _url_has_query_params(self, url: str) -> bool:
        """检查URL是否带有查询参数（签名等）"""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            return bool(parsed.query)
        except Exception:
            return False

    # ========== 阿里云百炼实现 ==========
    def _invoke_aliyun(
        self, params: dict
    ) -> Generator[ToolInvokeMessage, None, None]:
        """
        调用阿里云百炼 DashScope API (图生视频)
        
        支持的模型:
        - wan2.5-i2v-preview: 通义万相 2.5 (固定5秒)
        - wan2.6-i2v: 通义万相 2.6 (支持5/10/15秒，多分辨率)
        """
        api_key = self.runtime.credentials.get("aliyun_api_key", "")
        if not api_key:
            yield self.create_text_message("❌ 错误：请配置阿里云百炼 API Key")
            return
        
        model = params.get("model", "wan2.5-i2v-preview")
        image_url = params.get("image_url", "")
        prompt = params.get("prompt", "让图片动起来")
        aspect_ratio = params.get("aspect_ratio", "16:9")
        duration = params.get("duration", "5")
        resolution = params.get("resolution", "720p")
        wait_for_completion = params.get("wait_for_completion", True)
        
        # 判断是否为 wan2.6 模型
        is_wan26 = model.startswith("wan2.6")
        
        # 分辨率映射
        if is_wan26:
            size_map = self.ALIYUN_26_SIZE_MAP.get(resolution, self.ALIYUN_26_SIZE_MAP["720p"])
            size = size_map.get(aspect_ratio, "1280*720")
        else:
            size = self.ALIYUN_SIZE_MAP.get(aspect_ratio, "1280*720")
        
        # 检查URL是否需要转换为Base64（阿里云不接受带签名参数的URL）
        final_image_url = image_url
        used_base64 = False
        
        if self._url_has_query_params(image_url) or not self._is_public_accessible_url(image_url):
            yield self.create_text_message(f"🔄 检测到图片URL带有签名参数，正在转换为Base64格式...")
            base64_url, error = self._convert_image_to_base64(image_url)
            if error:
                yield self.create_text_message(f"❌ 图片转换失败: {error}")
                yield self.create_json_message({"success": False, "provider": "aliyun", "error_message": error})
                return
            final_image_url = base64_url
            used_base64 = True
            yield self.create_text_message(f"✅ 图片转换成功")
        
        model_name = self.ALIYUN_MODELS.get(model, {}).get("name", model)
        
        # 构建提示信息
        info_text = (
            f"🚀 **提交图生视频任务**\n\n"
            f"🏢 平台: 阿里云百炼\n"
            f"📝 模型: {model_name}\n"
            f"🖼️ 图片: {'Base64' if used_base64 else image_url[:60]}...\n"
            f"📐 分辨率: {size}\n"
        )
        if is_wan26:
            info_text += f"⏱️ 时长: {duration}秒\n"
        info_text += f"💬 描述: {prompt[:50]}..."
        
        yield self.create_text_message(info_text)
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"
        }
        
        payload = {
            "model": model,
            "input": {
                "prompt": prompt,
                "image_url": final_image_url
            },
            "parameters": {
                "size": size
            }
        }
        
        # wan2.6 支持额外参数
        if is_wan26:
            payload["parameters"]["duration"] = int(duration)
        
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

    # ========== 火山方舟实现 (Ark API) ==========
    def _submit_volcengine_task(
        self, api_key: str, model: str, image_url: str, full_prompt: str
    ) -> tuple[dict, str]:
        """提交火山引擎任务，返回 (result, error)"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": full_prompt}
            ]
        }
        try:
            response = requests.post(
                f"{self.VOLCENGINE_API_BASE}/contents/generations/tasks",
                headers=headers, json=payload, timeout=30
            )
            if response.status_code != 200:
                return {}, f"{response.status_code} - {response.text}"
            return response.json(), ""
        except Exception as e:
            return {}, str(e)

    def _invoke_volcengine(
        self, params: dict
    ) -> Generator[ToolInvokeMessage, None, None]:
        """调用火山方舟 Ark API (图生视频) - 智能重试"""
        api_key = self.runtime.credentials.get("volcengine_api_key", "")
        if not api_key:
            yield self.create_text_message("❌ 错误：请配置火山方舟 API Key")
            return
        
        # 获取 endpoint_id，如果配置了则使用 endpoint_id，否则使用 model 名称
        endpoint_id = self.runtime.credentials.get("volcengine_endpoint_id", "").strip()
        model = params.get("model", "doubao-seaweed-241128")
        
        # 火山方舟 Ark API 需要使用 endpoint_id 作为 model 参数
        if endpoint_id:
            model = endpoint_id
        image_url = params.get("image_url", "")
        prompt = params.get("prompt", "让图片动起来")
        duration = params.get("duration", "5")
        wait_for_completion = params.get("wait_for_completion", True)
        
        full_prompt = f"{prompt} --duration {duration}"
        model_name = self.VOLCENGINE_MODELS.get(model, {}).get("name", model)
        
        # 智能策略：判断是否需要预先转换 Base64
        need_base64 = not self._is_public_accessible_url(image_url)
        final_image_url = image_url
        used_base64 = False
        
        if need_base64:
            # 明确的内网地址，直接转 Base64
            yield self.create_text_message(f"🔄 检测到内网图片地址，正在转换为Base64格式...")
            base64_url, error = self._convert_image_to_base64(image_url)
            if error:
                yield self.create_text_message(f"❌ 图片转换失败: {error}")
                return
            final_image_url = base64_url
            used_base64 = True
            yield self.create_text_message(f"✅ 图片转换成功")
        
        yield self.create_text_message(
            f"🚀 **提交图生视频任务**\n\n"
            f"🏢 平台: 火山方舟\n"
            f"📝 模型: {model_name}\n"
            f"🖼️ 图片: {'Base64' if used_base64 else image_url[:60]}\n"
            f"⏱️ 时长: {duration}秒\n"
            f"💬 描述: {prompt[:50]}..."
        )
        
        # 第一次尝试提交
        result, error = self._submit_volcengine_task(api_key, model, final_image_url, full_prompt)
        
        # 智能重试：如果是 URL 方式且返回 "image not found" 错误，自动转 Base64 重试
        if error and not used_base64 and "image" in error.lower() and "not found" in error.lower():
            yield self.create_text_message(f"⚠️ 火山引擎无法访问图片URL，自动转换为Base64重试...")
            base64_url, convert_error = self._convert_image_to_base64(image_url)
            if convert_error:
                yield self.create_text_message(f"❌ 图片转换失败: {convert_error}")
                yield self.create_json_message({"success": False, "provider": "volcengine", "error_message": convert_error})
                return
            yield self.create_text_message(f"✅ 图片转换成功，重新提交...")
            result, error = self._submit_volcengine_task(api_key, model, base64_url, full_prompt)
            used_base64 = True
        
        if error:
            yield self.create_text_message(f"❌ 提交失败: {error}")
            yield self.create_json_message({"success": False, "provider": "volcengine", "error_message": error})
            return
        
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
                
                # 调试日志：输出原始响应
                if attempt == 0:
                    yield self.create_text_message(f"📋 首次轮询响应: status={status}, keys={list(result.keys())}")
                
                # 状态统一转小写，兼容不同格式
                status_lower = status.lower() if isinstance(status, str) else "unknown"
                
                if status_lower == "succeeded" or status_lower == "done":
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
                    
                elif status_lower == "failed":
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
                
                elif status_lower == "canceled" or status_lower == "cancelled":
                    yield self.create_text_message("❌ 任务已被取消")
                    return
                    
                else:
                    if attempt % 6 == 0:
                        elapsed = attempt * self.POLL_INTERVAL
                        yield self.create_text_message(f"⏳ 正在生成... ({elapsed}秒)")
                    time.sleep(self.POLL_INTERVAL)
                    
            except Exception:
                time.sleep(self.POLL_INTERVAL)
        
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
