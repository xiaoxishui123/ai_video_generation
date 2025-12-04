"""
图片生成视频工具 (Image-to-Video)

支持双平台：
- 阿里云百炼：通义万相 wan2.5-i2v-preview
- 火山方舟：豆包 Seaweed I2V 模型

功能：
- 基于输入图片生成视频
- 支持运动描述提示词
- 轮询任务状态
- 返回视频URL和封面URL

参考: https://marketplace.dify.ai/plugins/allenwriter/doubao_image
"""

import time
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
    # 视觉智能开放平台API地址
    VOLCENGINE_API_BASE = "https://visual.volcengineapi.com"
    VOLCENGINE_MODELS = {
        "doubao-seaweed-241128": {"name": "Seaweed I2V"},
    }

    # 轮询配置
    POLL_INTERVAL = 5  # 轮询间隔（秒）
    MAX_POLL_ATTEMPTS = 120  # 最大轮询次数（10分钟）

    def _invoke(
        self, tool_parameters: dict[str, Any]
    ) -> Generator[ToolInvokeMessage, None, None]:
        """
        执行工具调用 - 根据平台分发
        
        Args:
            tool_parameters: 工具参数
            
        Yields:
            ToolInvokeMessage: 工具调用消息
        """
        provider = tool_parameters.get("provider", "aliyun")
        image_url = tool_parameters.get("image_url", "").strip()
        
        # 参数验证
        if not image_url:
            yield self.create_text_message("❌ 错误：图片URL不能为空")
            return
        
        # 验证URL格式
        if not image_url.startswith(("http://", "https://")):
            yield self.create_text_message("❌ 错误：图片URL格式无效，必须以http://或https://开头")
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
        调用阿里云百炼 DashScope API (图生视频)
        
        API文档：https://help.aliyun.com/zh/model-studio/image-to-video-api-reference/
        """
        # 获取凭证
        api_key = self.runtime.credentials.get("aliyun_api_key", "")
        if not api_key:
            yield self.create_text_message("❌ 错误：请配置阿里云百炼 API Key")
            return
        
        # 解析参数
        model = params.get("model", "wan2.5-i2v-preview")
        image_url = params.get("image_url", "")
        prompt = params.get("prompt", "让图片动起来")
        resolution = params.get("resolution", "720p")
        wait_for_completion = params.get("wait_for_completion", True)
        
        # 分辨率映射
        size = "1280*720" if resolution == "720p" else "1920*1080"
        
        model_name = self.ALIYUN_MODELS.get(model, {}).get("name", model)
        yield self.create_text_message(
            f"🚀 **提交图生视频任务**\n\n"
            f"🏢 平台: 阿里云百炼\n"
            f"📝 模型: {model_name}\n"
            f"🖼️ 图片: {image_url[:60]}{'...' if len(image_url) > 60 else ''}\n"
            f"📐 分辨率: {resolution}\n"
            f"💬 动作描述: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
        )
        
        # 构建请求
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"  # 启用异步模式
        }
        
        payload = {
            "model": model,
            "input": {
                "prompt": prompt,
                "image_url": image_url
            },
            "parameters": {
                "size": size,
                "duration": 5  # 阿里云目前只支持5秒
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
                        "cover_url": cover_url,
                        "duration": 5.0
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
            f"⏰ 任务超时（等待超过{self.MAX_POLL_ATTEMPTS * self.POLL_INTERVAL}秒）\n"
            f"🔖 任务ID: `{task_id}`\n"
            f"请使用任务查询工具手动查询结果"
        )
        yield self.create_json_message({
            "success": False,
            "provider": "aliyun",
            "model": model,
            "task_id": task_id,
            "status": "TIMEOUT",
            "error_message": "任务超时"
        })

    # ========== 火山方舟实现 ==========
    def _invoke_volcengine(
        self, params: dict
    ) -> Generator[ToolInvokeMessage, None, None]:
        """
        调用火山方舟视觉智能平台 Seaweed API (图生视频)
        
        API文档：https://www.volcengine.com/docs/85128/1526761
        参考: https://marketplace.dify.ai/plugins/allenwriter/doubao_image
        """
        # 获取凭证
        api_key = self.runtime.credentials.get("volcengine_api_key", "")
        if not api_key:
            yield self.create_text_message("❌ 错误：请配置火山方舟 API Key")
            return
        
        # 解析参数
        model = params.get("model", "doubao-seaweed-241128")
        image_url = params.get("image_url", "")
        prompt = params.get("prompt", "让图片动起来")
        duration = int(params.get("duration", "5"))
        wait_for_completion = params.get("wait_for_completion", True)
        
        model_name = self.VOLCENGINE_MODELS.get(model, {}).get("name", model)
        yield self.create_text_message(
            f"🚀 **提交图生视频任务**\n\n"
            f"🏢 平台: 火山方舟\n"
            f"📝 模型: {model_name}\n"
            f"🖼️ 图片: {image_url[:60]}{'...' if len(image_url) > 60 else ''}\n"
            f"⏱️ 时长: {duration}秒\n"
            f"💬 动作描述: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
        )
        
        # 构建请求头
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建请求体 - 火山方舟视觉智能平台格式（图生视频）
        payload = {
            "req_key": "jimeng_vgfm_i2v",  # 图生视频接口标识
            "prompt": prompt,
            "model_version": model,
            "image_url": image_url,
            "duration": duration
        }
        
        try:
            # 提交任务
            response = requests.post(
                f"{self.VOLCENGINE_API_BASE}/cv/v1/video_gen_async",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            result = response.json()
            
            # 检查错误
            if result.get("code") != 10000:
                error_msg = result.get("message", str(result))
                yield self.create_text_message(f"❌ 提交失败: {error_msg}")
                yield self.create_json_message({
                    "success": False,
                    "provider": "volcengine",
                    "error_message": error_msg
                })
                return
            
            # 获取任务ID
            task_id = result.get("data", {}).get("task_id")
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
                    "status": "Pending"
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
        轮询火山方舟任务状态
        
        状态说明：
        - not_start/submitted: 任务等待中
        - running: 任务运行中
        - done: 任务成功
        - failed: 任务失败
        """
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        for attempt in range(self.MAX_POLL_ATTEMPTS):
            try:
                # 火山方舟视觉智能平台查询接口
                payload = {
                    "req_key": "jimeng_vgfm_i2v",
                    "task_id": task_id
                }
                
                response = requests.post(
                    f"{self.VOLCENGINE_API_BASE}/cv/v1/video_gen_async/query",
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                result = response.json()
                
                # 检查API响应状态
                if result.get("code") != 10000:
                    error_msg = result.get("message", "查询失败")
                    yield self.create_text_message(f"❌ 查询失败: {error_msg}")
                    yield self.create_json_message({
                        "success": False,
                        "provider": "volcengine",
                        "model": model,
                        "task_id": task_id,
                        "status": "Failed",
                        "error_message": error_msg
                    })
                    return
                
                data = result.get("data", {})
                status = data.get("status", "unknown")
                
                if status == "done":
                    # 获取视频URL - 火山方舟返回格式
                    video_list = data.get("video_list", [])
                    video_url = video_list[0] if video_list else ""
                    cover_url = data.get("cover_url", "")
                    
                    yield self.create_text_message(
                        f"🎉 **视频生成完成！**\n\n"
                        f"📹 视频: {video_url}\n"
                        f"🖼️ 封面: {cover_url if cover_url else '无'}"
                    )
                    yield self.create_json_message({
                        "success": True,
                        "provider": "volcengine",
                        "model": model,
                        "task_id": task_id,
                        "status": "done",
                        "video_url": video_url,
                        "cover_url": cover_url
                    })
                    return
                    
                elif status == "failed":
                    error_msg = data.get("err_msg", data.get("error_message", "未知错误"))
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
                    
                else:
                    # 每30秒输出一次进度
                    if attempt % 6 == 0:
                        elapsed = attempt * self.POLL_INTERVAL
                        status_text = {
                            "not_start": "等待中",
                            "submitted": "已提交",
                            "running": "生成中"
                        }.get(status, status)
                        yield self.create_text_message(
                            f"⏳ 正在生成... {status_text} ({elapsed}秒)"
                        )
                    time.sleep(self.POLL_INTERVAL)
                    
            except Exception as e:
                time.sleep(self.POLL_INTERVAL)
        
        # 超时
        yield self.create_text_message(
            f"⏰ 任务超时（等待超过{self.MAX_POLL_ATTEMPTS * self.POLL_INTERVAL}秒）\n"
            f"🔖 任务ID: `{task_id}`\n"
            f"请使用任务查询工具手动查询结果"
        )
        yield self.create_json_message({
            "success": False,
            "provider": "volcengine",
            "model": model,
            "task_id": task_id,
            "status": "TIMEOUT",
            "error_message": "任务超时"
        })

