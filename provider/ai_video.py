"""
AI视频生成工具 - Provider凭证验证模块

支持的平台：
- 阿里云百炼 (DashScope)
- 火山引擎视觉智能平台 (Volcengine Visual Intelligence)

参考: https://marketplace.dify.ai/plugins/allenwriter/doubao_image
"""

import requests
from typing import Any
from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError


class AIVideoProvider(ToolProvider):
    """AI视频生成工具提供者"""

    # 阿里云百炼API基础地址
    ALIYUN_API_BASE = "https://dashscope.aliyuncs.com/api/v1"
    
    # 火山引擎视觉智能平台API基础地址
    VOLCENGINE_API_BASE = "https://visual.volcengineapi.com"

    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        """
        验证凭证有效性
        
        至少需要配置一个平台的凭证：
        - 阿里云：aliyun_api_key
        - 火山引擎：volcengine_api_key
        
        Args:
            credentials: 凭证字典
            
        Raises:
            ToolProviderCredentialValidationError: 凭证验证失败时抛出
        """
        aliyun_key = credentials.get("aliyun_api_key", "").strip()
        volcengine_key = credentials.get("volcengine_api_key", "").strip()
        
        # 检查是否至少配置了一个平台
        has_aliyun = bool(aliyun_key)
        has_volcengine = bool(volcengine_key)
        
        if not has_aliyun and not has_volcengine:
            raise ToolProviderCredentialValidationError(
                "请至少配置一个平台的凭证：\n"
                "- 阿里云百炼：需要 API Key\n"
                "- 火山引擎：需要 API Key"
            )
        
        # 验证阿里云凭证
        if has_aliyun:
            self._validate_aliyun_credentials(aliyun_key)
        
        # 验证火山引擎凭证
        if has_volcengine:
            self._validate_volcengine_credentials(volcengine_key)

    def _validate_aliyun_credentials(self, api_key: str) -> None:
        """
        验证阿里云百炼凭证
        
        通过调用模型列表API来验证API Key是否有效
        
        Args:
            api_key: 阿里云百炼 API Key
            
        Raises:
            ToolProviderCredentialValidationError: 验证失败时抛出
        """
        try:
            # 使用查询任务状态的方式验证（使用一个不存在的任务ID）
            # 如果返回401则凭证无效，返回其他错误则凭证有效
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # 尝试查询一个不存在的任务
            response = requests.get(
                f"{self.ALIYUN_API_BASE}/tasks/test-validation-task",
                headers=headers,
                timeout=10
            )
            
            # 401 表示凭证无效
            if response.status_code == 401:
                raise ToolProviderCredentialValidationError(
                    "阿里云百炼 API Key 无效，请检查是否正确配置"
                )
            
            # 其他状态码（如404任务不存在）表示凭证有效
            
        except requests.RequestException as e:
            raise ToolProviderCredentialValidationError(
                f"阿里云百炼凭证验证失败: 网络错误 - {str(e)}"
            )

    def _validate_volcengine_credentials(self, api_key: str) -> None:
        """
        验证火山引擎凭证
        
        Args:
            api_key: 火山引擎 API Key
            
        Raises:
            ToolProviderCredentialValidationError: 验证失败时抛出
        """
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # 尝试查询一个不存在的任务来验证凭证
            payload = {
                "req_key": "jimeng_vgfm_t2v_l20",
                "task_id": "test-validation-task"
            }
            
            response = requests.post(
                f"{self.VOLCENGINE_API_BASE}/cv/v1/video_gen_async/query",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            result = response.json()
            
            # 检查是否是认证错误（code 50001 通常表示认证失败）
            if result.get("code") == 50001:
                raise ToolProviderCredentialValidationError(
                    "火山引擎 API Key 无效，请检查是否正确配置"
                )
            
            # 其他错误码（如任务不存在等）表示凭证有效
            
        except requests.RequestException as e:
            raise ToolProviderCredentialValidationError(
                f"火山引擎凭证验证失败: 网络错误 - {str(e)}"
            )

