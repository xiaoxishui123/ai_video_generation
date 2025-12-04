"""
任务状态查询工具 (Query Task)

支持双平台：
- 阿里云百炼：查询DashScope任务状态
- 火山方舟：查询Ark任务状态

参考: https://marketplace.dify.ai/plugins/allenwriter/doubao_image
"""

import requests
from typing import Any, Generator
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class QueryTaskTool(Tool):
    """任务状态查询工具 - 双平台支持"""

    ALIYUN_API_BASE = "https://dashscope.aliyuncs.com/api/v1"
    VOLCENGINE_API_BASE = "https://ark.cn-beijing.volces.com/api/v3"
    
    ALIYUN_STATUS_MAP = {
        "PENDING": "等待中",
        "RUNNING": "生成中",
        "SUCCEEDED": "已完成",
        "FAILED": "失败",
        "UNKNOWN": "未知"
    }
    
    VOLCENGINE_STATUS_MAP = {
        "running": "生成中",
        "succeeded": "已完成",
        "failed": "失败",
        "canceled": "已取消",
        "unknown": "未知"
    }

    def _invoke(
        self, tool_parameters: dict[str, Any]
    ) -> Generator[ToolInvokeMessage, None, None]:
        """查询任务状态"""
        provider = tool_parameters.get("provider", "aliyun")
        task_id = tool_parameters.get("task_id", "").strip()
        
        if not task_id:
            yield self.create_text_message("❌ 错误：任务ID不能为空")
            return
        
        if provider == "aliyun":
            yield from self._query_aliyun(task_id)
        elif provider == "volcengine":
            yield from self._query_volcengine(task_id)
        else:
            yield self.create_text_message(f"❌ 错误：不支持的平台 {provider}")

    def _query_aliyun(
        self, task_id: str
    ) -> Generator[ToolInvokeMessage, None, None]:
        """查询阿里云百炼任务状态"""
        api_key = self.runtime.credentials.get("aliyun_api_key", "")
        if not api_key:
            yield self.create_text_message("❌ 错误：请配置阿里云百炼 API Key")
            return
        
        yield self.create_text_message(
            f"🔍 **查询任务状态**\n\n"
            f"🏢 平台: 阿里云百炼\n"
            f"🔖 任务ID: `{task_id}`"
        )
        
        headers = {"Authorization": f"Bearer {api_key}"}
        
        try:
            response = requests.get(
                f"{self.ALIYUN_API_BASE}/tasks/{task_id}",
                headers=headers,
                timeout=30
            )
            
            result = response.json()
            
            if response.status_code != 200:
                error_msg = result.get("message", str(result))
                yield self.create_text_message(f"❌ 查询失败: {error_msg}")
                yield self.create_json_message({
                    "success": False,
                    "provider": "aliyun",
                    "task_id": task_id,
                    "error_message": error_msg
                })
                return
            
            output = result.get("output", {})
            status = output.get("task_status", "UNKNOWN")
            status_text = self.ALIYUN_STATUS_MAP.get(status, status)
            
            if status == "SUCCEEDED":
                video_url = output.get("video_url", "")
                cover_url = output.get("cover_url", "")
                
                yield self.create_text_message(
                    f"✅ **任务已完成**\n\n"
                    f"📊 状态: {status_text}\n"
                    f"📹 视频: {video_url}\n"
                    f"🖼️ 封面: {cover_url}"
                )
                yield self.create_json_message({
                    "success": True,
                    "provider": "aliyun",
                    "task_id": task_id,
                    "status": status,
                    "status_text": status_text,
                    "video_url": video_url,
                    "cover_url": cover_url
                })
                
            elif status == "FAILED":
                error_msg = output.get("message", "未知错误")
                yield self.create_text_message(
                    f"❌ **任务失败**\n\n"
                    f"📊 状态: {status_text}\n"
                    f"💬 原因: {error_msg}"
                )
                yield self.create_json_message({
                    "success": True,
                    "provider": "aliyun",
                    "task_id": task_id,
                    "status": status,
                    "status_text": status_text,
                    "error_message": error_msg
                })
                
            else:
                yield self.create_text_message(
                    f"⏳ **任务进行中**\n\n"
                    f"📊 状态: {status_text}\n"
                    f"💡 提示: 请稍后再次查询"
                )
                yield self.create_json_message({
                    "success": True,
                    "provider": "aliyun",
                    "task_id": task_id,
                    "status": status,
                    "status_text": status_text
                })
                
        except requests.Timeout:
            yield self.create_text_message("❌ 错误: 请求超时")
        except Exception as e:
            yield self.create_text_message(f"❌ 错误: {str(e)}")

    def _query_volcengine(
        self, task_id: str
    ) -> Generator[ToolInvokeMessage, None, None]:
        """查询火山方舟任务状态 (Ark API)"""
        api_key = self.runtime.credentials.get("volcengine_api_key", "")
        if not api_key:
            yield self.create_text_message("❌ 错误：请配置火山方舟 API Key")
            return
        
        yield self.create_text_message(
            f"🔍 **查询任务状态**\n\n"
            f"🏢 平台: 火山方舟\n"
            f"🔖 任务ID: `{task_id}`"
        )
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        try:
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
                    "task_id": task_id,
                    "error_message": response.text
                })
                return
            
            result = response.json()
            status = result.get("status", "unknown")
            status_text = self.VOLCENGINE_STATUS_MAP.get(status, status)
            
            if status == "succeeded":
                video_url = result.get("content", {}).get("video_url", "")
                
                yield self.create_text_message(
                    f"✅ **任务已完成**\n\n"
                    f"📊 状态: {status_text}\n"
                    f"📹 视频: {video_url}"
                )
                if video_url:
                    yield self.create_image_message(video_url)
                yield self.create_text_message("⚠️ 视频链接有效期24小时")
                yield self.create_json_message({
                    "success": True,
                    "provider": "volcengine",
                    "task_id": task_id,
                    "status": status,
                    "status_text": status_text,
                    "video_url": video_url
                })
                
            elif status == "failed":
                error_msg = result.get("error", {}).get("message", "未知错误")
                yield self.create_text_message(
                    f"❌ **任务失败**\n\n"
                    f"📊 状态: {status_text}\n"
                    f"💬 原因: {error_msg}"
                )
                yield self.create_json_message({
                    "success": True,
                    "provider": "volcengine",
                    "task_id": task_id,
                    "status": status,
                    "status_text": status_text,
                    "error_message": error_msg
                })
            
            elif status == "canceled":
                yield self.create_text_message(
                    f"❌ **任务已取消**\n\n"
                    f"📊 状态: {status_text}"
                )
                yield self.create_json_message({
                    "success": True,
                    "provider": "volcengine",
                    "task_id": task_id,
                    "status": status,
                    "status_text": status_text
                })
                
            else:
                yield self.create_text_message(
                    f"⏳ **任务进行中**\n\n"
                    f"📊 状态: {status_text}\n"
                    f"💡 提示: 请稍后再次查询"
                )
                yield self.create_json_message({
                    "success": True,
                    "provider": "volcengine",
                    "task_id": task_id,
                    "status": status,
                    "status_text": status_text
                })
                
        except requests.Timeout:
            yield self.create_text_message("❌ 错误: 请求超时")
        except Exception as e:
            yield self.create_text_message(f"❌ 错误: {str(e)}")
