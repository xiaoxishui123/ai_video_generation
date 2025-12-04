"""
任务状态查询工具 (Query Task)

支持双平台：
- 阿里云百炼：查询DashScope任务状态
- 火山方舟：查询视觉智能平台任务状态

功能：
- 根据task_id查询任务状态
- 返回任务结果（视频URL、封面URL等）

参考: https://marketplace.dify.ai/plugins/allenwriter/doubao_image
"""

import requests
from typing import Any, Generator
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class QueryTaskTool(Tool):
    """任务状态查询工具 - 双平台支持"""

    # ========== 阿里云百炼配置 ==========
    ALIYUN_API_BASE = "https://dashscope.aliyuncs.com/api/v1"
    
    # ========== 火山方舟配置 ==========
    # 视觉智能开放平台API地址
    VOLCENGINE_API_BASE = "https://visual.volcengineapi.com"
    
    # 状态映射
    ALIYUN_STATUS_MAP = {
        "PENDING": "等待中",
        "RUNNING": "生成中",
        "SUCCEEDED": "已完成",
        "FAILED": "失败",
        "UNKNOWN": "未知"
    }
    
    VOLCENGINE_STATUS_MAP = {
        "not_start": "等待中",
        "submitted": "已提交",
        "running": "生成中",
        "done": "已完成",
        "failed": "失败",
        "unknown": "未知"
    }

    def _invoke(
        self, tool_parameters: dict[str, Any]
    ) -> Generator[ToolInvokeMessage, None, None]:
        """
        执行工具调用 - 查询任务状态
        
        Args:
            tool_parameters: 工具参数
            
        Yields:
            ToolInvokeMessage: 工具调用消息
        """
        provider = tool_parameters.get("provider", "aliyun")
        task_id = tool_parameters.get("task_id", "").strip()
        
        # 参数验证
        if not task_id:
            yield self.create_text_message("❌ 错误：任务ID不能为空")
            return
        
        # 根据平台分发调用
        if provider == "aliyun":
            yield from self._query_aliyun(task_id)
        elif provider == "volcengine":
            yield from self._query_volcengine(task_id)
        else:
            yield self.create_text_message(f"❌ 错误：不支持的平台 {provider}")

    def _query_aliyun(
        self, task_id: str
    ) -> Generator[ToolInvokeMessage, None, None]:
        """
        查询阿里云百炼任务状态
        """
        # 获取凭证
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
            
            # 检查HTTP错误
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
            
            # 解析结果
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
                # PENDING 或 RUNNING
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
        except requests.RequestException as e:
            yield self.create_text_message(f"❌ 网络错误: {str(e)}")
        except Exception as e:
            yield self.create_text_message(f"❌ 错误: {str(e)}")

    def _query_volcengine(
        self, task_id: str
    ) -> Generator[ToolInvokeMessage, None, None]:
        """
        查询火山方舟任务状态
        
        使用视觉智能开放平台API
        """
        # 获取凭证
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
            # 尝试文生视频查询
            payload = {
                "req_key": "jimeng_vgfm_t2v_l20",
                "task_id": task_id
            }
            
            response = requests.post(
                f"{self.VOLCENGINE_API_BASE}/cv/v1/video_gen_async/query",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            result = response.json()
            
            # 如果文生视频查询失败，尝试图生视频查询
            if result.get("code") != 10000:
                payload["req_key"] = "jimeng_vgfm_i2v"
                response = requests.post(
                    f"{self.VOLCENGINE_API_BASE}/cv/v1/video_gen_async/query",
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                result = response.json()
            
            # 检查API响应状态
            if result.get("code") != 10000:
                error_msg = result.get("message", str(result))
                yield self.create_text_message(f"❌ 查询失败: {error_msg}")
                yield self.create_json_message({
                    "success": False,
                    "provider": "volcengine",
                    "task_id": task_id,
                    "error_message": error_msg
                })
                return
            
            # 解析结果
            data = result.get("data", {})
            status = data.get("status", "unknown")
            status_text = self.VOLCENGINE_STATUS_MAP.get(status, status)
            
            if status == "done":
                video_list = data.get("video_list", [])
                video_url = video_list[0] if video_list else ""
                cover_url = data.get("cover_url", "")
                
                yield self.create_text_message(
                    f"✅ **任务已完成**\n\n"
                    f"📊 状态: {status_text}\n"
                    f"📹 视频: {video_url}\n"
                    f"🖼️ 封面: {cover_url if cover_url else '无'}"
                )
                yield self.create_json_message({
                    "success": True,
                    "provider": "volcengine",
                    "task_id": task_id,
                    "status": status,
                    "status_text": status_text,
                    "video_url": video_url,
                    "cover_url": cover_url
                })
                
            elif status == "failed":
                error_msg = data.get("err_msg", data.get("error_message", "未知错误"))
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
                
            else:
                # not_start / submitted / running
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
        except requests.RequestException as e:
            yield self.create_text_message(f"❌ 网络错误: {str(e)}")
        except Exception as e:
            yield self.create_text_message(f"❌ 错误: {str(e)}")

