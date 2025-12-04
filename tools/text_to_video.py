"""
文本生成视频工具 (Text-to-Video)

支持双平台：
- 阿里云百炼：通义万相 wan2.5-t2v-preview
- 火山方舟：豆包 Seedance 系列模型

功能：
- 提交视频生成任务
- 轮询任务状态
- 返回视频URL和封面URL

参考: https://marketplace.dify.ai/plugins/allenwriter/doubao_image
"""

import time
import requests
from typing import Any, Generator
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class TextToVideoTool(Tool):
    """文本生成视频工具 - 双平台支持"""

    # ========== 阿里云百炼配置 ==========
    ALIYUN_API_BASE = "https://dashscope.aliyuncs.com/api/v1"
    ALIYUN_MODELS = {
        "wan2.5-t2v-preview": {"name": "通义万相 T2V", "type": "t2v"},
    }

    # ========== 火山方舟配置 ==========
    # 使用 Ark API (与官方 doubao_image 插件一致)
    VOLCENGINE_API_BASE = "https://ark.cn-beijing.volces.com/api/v3"
    VOLCENGINE_MODELS = {
        "doubao-seedance-1-0-lite-t2v-250428": {"name": "Seedance Lite T2V"},
    }
    
    # 阿里云分辨率映射 - 注意：宽*高 格式
    ALIYUN_SIZE_MAP = {
        "16:9": "1280*720",
        "9:16": "720*1280",
        "1:1": "720*720",
    }

    # 轮询配置
    POLL_INTERVAL = 5  # 轮询间隔（秒）
    MAX_POLL_ATTEMPTS = 120  # 最大轮询次数（10分钟）

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
        
        # 根据平台分发调用
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
        """
        调用阿里云百炼 DashScope API
        
        API文档：https://help.aliyun.com/zh/model-studio/video-generation-api-reference/
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
        wait_for_completion = params.get("wait_for_completion", True)
        
        # 宽高比映射到分辨率
        size = self.ALIYUN_SIZE_MAP.get(aspect_ratio, "1280*720")
        
        model_name = self.ALIYUN_MODELS.get(model, {}).get("name", model)
        yield self.create_text_message(
            f"🚀 **提交视频生成任务**\n\n"
            f"🏢 平台: 阿里云百炼\n"
            f"📝 模型: {model_name}\n"
            f"📐 宽高比: {aspect_ratio} ({size})\n"
            f"💬 提示词: {prompt[:80]}{'...' if len(prompt) > 80 else ''}"
        )
        
        # 构建请求
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"  # 启用异步模式
        }
        
        payload = {
            "model": model,
            "input": {"prompt": prompt},
            "parameters": {
                "size": size
            }
        }
        
        try:
            # 提交任务
            response = requests.post(
                f"{self.ALIYUN_API_BASE}/services/aigc/video-generation/generation",
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
                    
                    yield self.create_text_message(
                        f"🎉 **视频生成完成！**\n\n"
                        f"📹 视频: {video_url}\n"
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
        
        # 超时
        yield self.create_text_message(
            f"⏰ 任务超时\n🔖 任务ID: `{task_id}`\n请使用任务查询工具手动查询结果"
        )
        yield self.create_json_message({
            "success": False,
            "provider": "aliyun",
            "model": model,
            "task_id": task_id,
            "status": "TIMEOUT",
            "error_message": "任务超时"
        })

    # ========== 火山方舟实现 (使用 Ark API) ==========
    def _invoke_volcengine(
        self, params: dict
    ) -> Generator[ToolInvokeMessage, None, None]:
        """
        调用火山方舟 Ark API (与官方 doubao_image 插件一致)
        
        API: https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks
        """
        # 获取凭证
        api_key = self.runtime.credentials.get("volcengine_api_key", "")
        if not api_key:
            yield self.create_text_message("❌ 错误：请配置火山方舟 API Key")
            return
        
        # 解析参数
        model = params.get("model", "doubao-seedance-1-0-lite-t2v-250428")
        prompt = params.get("prompt", "")
        duration = params.get("duration", "5")
        aspect_ratio = params.get("aspect_ratio", "16:9")
        wait_for_completion = params.get("wait_for_completion", True)
        
        # 构建带参数的 prompt (与官方插件一致)
        full_prompt = prompt
        if aspect_ratio and "--ratio" not in prompt:
            full_prompt = f"{full_prompt} --ratio {aspect_ratio}"
        if duration and "--duration" not in prompt and "--dur" not in prompt:
            full_prompt = f"{full_prompt} --duration {duration}"
        
        model_name = self.VOLCENGINE_MODELS.get(model, {}).get("name", model)
        yield self.create_text_message(
            f"🚀 **提交视频生成任务**\n\n"
            f"🏢 平台: 火山方舟\n"
            f"📝 模型: {model_name}\n"
            f"⏱️ 时长: {duration}秒\n"
            f"📐 宽高比: {aspect_ratio}\n"
            f"💬 提示词: {prompt[:80]}{'...' if len(prompt) > 80 else ''}"
        )
        
        # 构建请求头
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建请求体 - 与官方 doubao_image 插件一致
        payload = {
            "model": model,
            "content": [
                {
                    "type": "text",
                    "text": full_prompt
                }
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
                    
                    yield self.create_text_message(
                        f"🎉 **视频生成完成！**\n\n"
                        f"📹 视频: {video_url}"
                    )
                    # 显示视频
                    if video_url:
                        yield self.create_image_message(video_url)
                    yield self.create_text_message("⚠️ 视频链接有效期24小时，请及时下载保存")
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
        
        # 超时
        yield self.create_text_message(
            f"⏰ 任务超时\n🔖 任务ID: `{task_id}`\n请使用任务查询工具手动查询结果"
        )
        yield self.create_json_message({
            "success": False,
            "provider": "volcengine",
            "model": model,
            "task_id": task_id,
            "status": "timeout",
            "error_message": "任务超时"
        })
