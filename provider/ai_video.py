"""
AI视频生成工具 - Provider凭证验证模块

支持的平台：
- 阿里云百炼 (DashScope)
- 火山方舟 (Ark API)

参考: https://marketplace.dify.ai/plugins/allenwriter/doubao_image
"""

import requests
from typing import Any
from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError


class AIVideoProvider(ToolProvider):
    """AI视频生成工具提供者"""

    ALIYUN_API_BASE = "https://dashscope.aliyuncs.com/api/v1"
    VOLCENGINE_API_BASE = "https://ark.cn-beijing.volces.com/api/v3"

    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        """
        验证凭证有效性
        
        至少需要配置一个平台的凭证
        """
        aliyun_key = credentials.get("aliyun_api_key", "").strip()
        volcengine_key = credentials.get("volcengine_api_key", "").strip()
        
        has_aliyun = bool(aliyun_key)
        has_volcengine = bool(volcengine_key)
        
        if not has_aliyun and not has_volcengine:
            raise ToolProviderCredentialValidationError(
                "请至少配置一个平台的凭证：\n"
                "- 阿里云百炼：需要 API Key\n"
                "- 火山方舟：需要 API Key"
            )
        
        # 验证阿里云凭证
        if has_aliyun:
            self._validate_aliyun_credentials(aliyun_key)
        
        # 验证火山引擎凭证
        if has_volcengine:
            self._validate_volcengine_credentials(volcengine_key)

    def _validate_aliyun_credentials(self, api_key: str) -> None:
        """验证阿里云百炼凭证"""
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # 查询一个不存在的任务来验证凭证
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
        """验证火山方舟凭证 (Ark API)"""
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # 查询一个不存在的任务来验证凭证
            response = requests.get(
                f"{self.VOLCENGINE_API_BASE}/contents/generations/tasks/test-validation",
                headers=headers,
                timeout=10
            )
            
            # 401/403 表示凭证无效
            if response.status_code in [401, 403]:
                raise ToolProviderCredentialValidationError(
                    "火山方舟 API Key 无效，请检查是否正确配置"
                )
            
            # 其他状态码表示凭证有效（如404任务不存在）
            
        except requests.RequestException as e:
            raise ToolProviderCredentialValidationError(
                f"火山方舟凭证验证失败: 网络错误 - {str(e)}"
            )
