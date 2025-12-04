# AI视频生成插件

> **版本**: v0.0.2  
> **作者**: xiaoxishui  
> **更新日期**: 2025-12-04

## 功能概述

这是一个Dify工具插件，支持**阿里云百炼**和**火山引擎**双平台的AI视频生成功能。

> **参考**: [Doubao Image and Video Generator](https://marketplace.dify.ai/plugins/allenwriter/doubao_image)

### ✨ 主要功能

- 📝 **文本生成视频 (T2V)** - 根据文本描述生成视频
- 🖼️ **图片生成视频 (I2V)** - 基于输入图片生成视频
- 🔍 **任务状态查询** - 查询视频生成任务的状态和结果
- 📐 **多宽高比支持** - 16:9、9:16、4:3、1:1

### 支持的模型

| 平台 | 模型ID | 功能 | 说明 |
|------|--------|------|------|
| 阿里云百炼 | `wan2.5-t2v-preview` | 文生视频 | 通义万相 T2V |
| 阿里云百炼 | `wan2.5-i2v-preview` | 图生视频 | 通义万相 I2V |
| 火山引擎 | `doubao-seedance-1-0-lite-t2v-250428` | 文生视频 | Seedance Lite T2V |
| 火山引擎 | `doubao-seaweed-241128` | 图生视频 | Seaweed I2V |

---

## 🚀 快速开始

### 1. 获取 API Key

#### 阿里云百炼
1. 访问 [阿里云百炼控制台](https://bailian.console.aliyun.com/)
2. 创建 API Key
3. 确保已开通通义万相视频生成服务

#### 火山引擎
1. 访问 [火山引擎控制台](https://console.volcengine.com/home)
2. 开通智能视觉服务
3. 获取 API Key

> **测试 API Key**: `719f1aec-26af-4bac-b1df-1fc26a95df73`（仅供测试使用）

### 2. 安装插件

1. 在 Dify 插件市场搜索 "AI视频生成"
2. 点击安装
3. 配置授权凭证

### 3. 配置凭证

在 Dify 中导航至 `工具 > AI视频生成 > 授权`，配置以下凭证（至少配置一个平台）：

| 凭证 | 说明 | 必填 |
|------|------|------|
| 阿里云百炼 API Key | DashScope API 密钥 | 否 |
| 火山引擎 API Key | 视觉智能平台 API 密钥 | 否 |

---

## 📋 使用示例

### 文本生成视频

```yaml
工具: 文本生成视频
参数:
  provider: volcengine                           # 平台：volcengine / aliyun
  model: doubao-seedance-1-0-lite-t2v-250428    # 模型
  prompt: "一只可爱的小猫在阳光下奔跑，草地上充满了小花"
  aspect_ratio: "16:9"                          # 宽高比
  duration: "5"                                  # 时长：5秒或10秒
  wait_for_completion: true                      # 等待完成
```

### 图片生成视频

```yaml
工具: 图片生成视频
参数:
  provider: volcengine
  model: doubao-seaweed-241128
  image_url: "https://example.com/image.jpg"     # 图片URL
  prompt: "让图片动起来，添加微风吹动的效果"
  duration: "5"
  wait_for_completion: true
```

### 查询任务状态

当 `wait_for_completion` 设为 false 时，使用此工具查询：

```yaml
工具: 查询任务状态
参数:
  provider: volcengine
  task_id: "xxxxx-task-id-xxxxx"
```

---

## 📊 输出格式

### 成功输出

```json
{
  "success": true,
  "provider": "volcengine",
  "model": "doubao-seedance-1-0-lite-t2v-250428",
  "task_id": "xxxxx-task-id-xxxxx",
  "status": "done",
  "video_url": "https://xxx.volces.com/xxx.mp4",
  "cover_url": "https://xxx.volces.com/xxx.jpg"
}
```

### 失败输出

```json
{
  "success": false,
  "provider": "volcengine",
  "task_id": "xxxxx-task-id-xxxxx",
  "status": "failed",
  "error_message": "内容违规，请修改提示词后重试"
}
```

---

## ⚙️ 技术规格

### 参数差异

| 参数 | 阿里云百炼 | 火山引擎 |
|------|-----------|----------|
| 时长 | 固定5秒 | 5/10秒 |
| 宽高比 | 16:9, 9:16, 4:3, 1:1 | 16:9, 9:16, 4:3, 1:1 |
| 任务状态 | PENDING/RUNNING/SUCCEEDED/FAILED | not_start/running/done/failed |

### 性能参考

| 功能 | 预计耗时 |
|------|----------|
| 文生视频 | 30-90秒 |
| 图生视频 | 20-60秒 |

---

## 🎯 最佳实践

### 提示词工程

- **具体描述**: 包含风格、光照、构图等细节
- **使用形容词**: 如 "鲜艳色彩"、"柔和光线"、"电影感"
- **指定情绪**: 如 "宁静"、"戏剧性"、"奇幻"

### 示例提示词

**文生视频**: 
> "雪山之巅的日出美景，金光洒在原始的高山湖泊上，照片级真实风格"

**图生视频**: 
> "为这个风景添加微妙的动感 - 树叶摇摆、流水潺潺、云朵飘移"

---

## 🔧 故障排除

### 常见问题

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| API Key 无效 | 凭证配置错误 | 检查并重新配置 API Key |
| 请求超时 | 网络问题 | 检查网络连接，稍后重试 |
| 任务超时 | 生成时间过长 | 使用 query_task 手动查询 |
| 内容违规 | 提示词不合规 | 修改提示词内容 |

### 错误代码

| 代码 | 说明 |
|------|------|
| `401` | 认证失败 - 检查 API 密钥 |
| `429` | 频率限制 - 请等待后重试 |
| `500` | 服务器错误 - 联系技术支持 |

---

## 📁 目录结构

```
ai_video_generation/
├── manifest.yaml           # 插件清单
├── requirements.txt        # Python依赖
├── icon.svg               # 插件图标
├── README.md              # 本文档
├── main.py                # 入口文件
├── provider/              # Provider 目录
│   ├── ai_video.py        # 凭证验证逻辑
│   └── ai_video.yaml      # 凭证配置（包含工具列表）
└── tools/                 # 工具目录
    ├── text_to_video.py   # 文生视频工具
    ├── text_to_video.yaml # 文生视频配置
    ├── image_to_video.py  # 图生视频工具
    ├── image_to_video.yaml# 图生视频配置
    ├── query_task.py      # 任务查询工具
    └── query_task.yaml    # 任务查询配置
```

---

## 📚 参考链接

- [Dify 插件开发文档](https://docs.dify.ai/zh-hans/plugins/quick-start/develop-plugins)
- [阿里云视频生成 API](https://help.aliyun.com/zh/model-studio/video-generation-api-reference/)
- [火山引擎视觉智能文档](https://www.volcengine.com/docs/85128/1526761)
- [参考插件: Doubao Image](https://marketplace.dify.ai/plugins/allenwriter/doubao_image)

---

## 📄 许可证

本项目遵循 MIT 许可证。

---

**用 AI 的力量将创意转化为精彩视觉** ✨
