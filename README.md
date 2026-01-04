# AI视频/图片生成插件

> **版本**: v0.0.51  
> **作者**: xiaoxishui  
> **更新日期**: 2026-01-04
> **变更说明**: 
> - 🐛 回滚目录结构调整 (actions -> tools)，以解决安装失败问题
> - 🐛 修复火山方舟模型参数传递问题
> - 🔧 优化 API 调用逻辑

## 功能概述

这是一个Dify工具插件，支持**阿里云百炼**、**火山引擎**和**JXINCM(Sora2)**三大平台的AI视频和图片生成功能。

> ⚠️ **注意**: JXINCM (Sora2) 是第三方代理服务，稳定性和持续性不做保证。请谨慎在生产环境使用。

> **参考**: [Doubao Image and Video Generator](https://marketplace.dify.ai/plugins/allenwriter/doubao_image)

### ✨ 主要功能

- 📝 **文本生成视频 (T2V)** - 根据文本描述生成视频
- 🖼️ **图片生成视频 (I2V)** - 基于输入图片生成视频
- 🎨 **文本生成图片 (T2I)** - 根据文本描述生成图片（火山引擎 Seedream）
- 🖼️ **参考图生图 (I2I)** - 基于参考图片生成一致性图片（最多14张参考图）
- 🔍 **任务状态查询** - 查询视频生成任务的状态和结果
- 📐 **多尺寸支持** - 支持多种视频宽高比和图片尺寸

### 支持的模型

#### 视频生成模型

| 平台 | 模型ID | 功能 | 说明 |
|------|--------|------|------|
| 阿里云百炼 | `wan2.6-t2v` | 文生视频 | 通义万相 2.6 T2V (推荐) |
| 阿里云百炼 | `wan2.6-i2v` | 图生视频 | 通义万相 2.6 I2V (推荐) |
| 阿里云百炼 | `wan2.5-t2v-preview` | 文生视频 | 通义万相 2.5 T2V |
| 阿里云百炼 | `wan2.5-i2v-preview` | 图生视频 | 通义万相 2.5 I2V |
| 火山引擎 | `doubao-seedance-1-5-pro-251215` | 文生视频 + 图生视频 | Seedance 1.5 Pro (最新，推荐) |
| 火山引擎 | `doubao-seedance-1-0-lite-t2v-250428` | 文生视频 | Seedance Lite T2V |
| 火山引擎 | `doubao-seaweed-241128` | 图生视频 | Seaweed I2V |
| JXINCM | `sora-2` | 文生视频 + 图生视频 | Sora-2 (标准) ⚠️第三方 |
| JXINCM | `sora-2-pro` | 文生视频 + 图生视频 | Sora-2 Pro (高质量) ⚠️第三方 |

#### 图片生成模型

| 平台 | 模型ID | 功能 | 说明 |
|------|--------|------|------|
| 火山引擎 | `doubao-seedream-4-5-251128` | 文生图 + **参考图生图** | Seedream 4.5 (最新，推荐，支持最多14张参考图) |
| 火山引擎 | `doubao-seedream-3-0-t2i-250110` | 文生图 | Seedream 3.0 T2I (仅支持文生图) |

#### 通义万相 2.6 vs 2.5 对比

| 特性 | 通义万相 2.6 | 通义万相 2.5 |
|------|-------------|-------------|
| 视频时长 | 5/10/15 秒 | 固定 5 秒 |
| 分辨率 | 480p/720p/1080p | 720p |
| 多镜头叙事 | ✅ 支持 | ❌ 不支持 |
| 自动配音 | ✅ 支持 | ❌ 不支持 |

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

#### JXINCM (Sora2) ⚠️第三方服务
1. 访问 JXINCM 平台注册账号
2. 获取 API Key
3. 参考: [GitHub - wwwzhouhui/sora2](https://github.com/wwwzhouhui/sora2)

> ⚠️ **风险提示**: JXINCM 是第三方代理服务，非官方 API。稳定性和持续性不做保证，请谨慎使用。

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
| 火山引擎 Endpoint ID | Ark 推理接入点 ID | 否 |
| JXINCM API Key | Sora2 第三方服务 API 密钥 | 否 |
| Dify 内部访问地址 | 插件访问 Dify 文件服务的内部 URL | 否 |

#### ⚠️ 关于 "Dify 内部访问地址" 配置

如果使用**图生视频**功能时遇到 `404 Client Error` 或 `图片转换失败` 错误，需要配置此项。

这是因为插件运行在 Docker 容器内，无法访问 Dify 对外暴露的文件 URL。配置内部访问地址后，插件会使用 Docker 内部网络来下载文件。

| 部署方式 | 推荐配置值 |
|---------|-----------|
| Docker Compose | `http://api:5001` |
| Docker Desktop (Mac/Windows) | `http://host.docker.internal:5001` |
| 自定义部署 | 根据实际网络配置填写 |

---

## 📋 使用示例

### 文本生成视频

```yaml
工具: 文本生成视频
参数:
  provider: volcengine                           # 平台：volcengine / aliyun
  model: doubao-seedance-1-5-pro-251215         # 模型（推荐使用最新的 Seedance 1.5 Pro）
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
  model: doubao-seedance-1-5-pro-251215         # 推荐使用最新的 Seedance 1.5 Pro
  image_url: "https://example.com/image.jpg"     # 图片URL
  prompt: "让图片动起来，添加微风吹动的效果"
  duration: "5"
  wait_for_completion: true
```

### JXINCM (Sora2) 视频生成 ⚠️第三方

```yaml
工具: 视频生成
参数:
  provider: jxincm                               # 第三方平台
  model: sora-2-pro                              # Sora-2 Pro 高质量模型
  prompt: "一只金毛犬在阳光明媚的公园里奔跑"
  orientation: landscape                          # 横屏/竖屏
  watermark: false                                # 是否添加水印
  wait_for_completion: true
# 注意：视频时长固定为15秒
```

### 文本生成图片

```yaml
工具: 文本生成图片
参数:
  model: doubao-seedream-4-5-251128         # Seedream 4.5 模型（推荐）
  prompt: "一只可爱的小猫在阳光下玩耍，水彩风格，柔和的色调"
  negative_prompt: "模糊、低质量、变形"      # 负面提示词（可选）
  size: "1024x1024"                          # 图片尺寸
  num_images: 1                              # 生成数量
  guidance_scale: 7.5                        # 引导系数（可选）
```

### 参考图生图 (图生图) 🆕

```yaml
工具: 文本生成图片
参数:
  model: doubao-seedream-4-5-251128         # 必须使用 Seedream 4.5
  prompt: "角色在森林中奔跑，阳光透过树叶，动态姿态"
  reference_images: "https://example.com/character.jpg"  # 参考图URL
  size: "1280x720"                          # 图片尺寸
  num_images: 1                              # 生成数量
```

**多张参考图示例**（角色一致性场景）：

```yaml
工具: 文本生成图片
参数:
  model: doubao-seedream-4-5-251128
  prompt: "角色在城市街道行走，现代都市背景，电影感光线"
  reference_images: "https://example.com/char1.jpg, https://example.com/char2.jpg"
  # 多个URL用英文逗号分隔，最多支持14张参考图
  size: "1280x720"
```

> **提示**: 参考图生图功能可以用于：
> - 🎭 **角色一致性** - 保持角色外观在不同场景中一致
> - 🎨 **风格迁移** - 参考某张图片的风格生成新图
> - 🖼️ **图片变换** - 基于原图生成不同视角/姿态的图片

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
  "model": "doubao-seedance-1-5-pro-251215",
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

| 参数 | 通义万相 2.6 | 通义万相 2.5 | 火山引擎 |
|------|-------------|-------------|----------|
| 时长 | 5/10/15秒 | 固定5秒 | 5/10秒 |
| 分辨率 | 480p/720p/1080p | 720p | 480p/720p/1080p |
| 宽高比 | 16:9, 9:16, 1:1 | 16:9, 9:16, 1:1 | 16:9, 9:16, 4:3, 1:1 |
| 任务状态 | PENDING/RUNNING/SUCCEEDED/FAILED | PENDING/RUNNING/SUCCEEDED/FAILED | running/succeeded/failed |

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
| 任务超时 | 生成时间过长 | 使用 query_task 手动查询（见下方说明） |
| killed by timeout | Dify 插件超时 | 视频仍在生成中，使用返回的任务ID查询结果 |
| 内容违规 | 提示词不合规 | 修改提示词内容 |

### 超时问题处理

**问题**: Dify 插件有 10 分钟的硬性超时限制，而视频生成可能需要更长时间。

**解决方案**: 当看到 "killed by timeout" 或 "视频生成仍在进行中" 消息时：

1. **记下任务 ID** - 消息中会显示任务 ID
2. **使用【查询任务状态】工具** - 输入平台和任务 ID 查询结果
3. **等待并重试** - 视频生成可能还在进行中，过几分钟再查询

**建议**: 如果经常遇到超时，可以将 `wait_for_completion` 设为 `false`，让工具只返回任务 ID，然后使用【查询任务状态】工具手动查询。

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
    ├── text_to_image.py   # 文生图/参考图生图工具（Seedream）
    ├── text_to_image.yaml # 文生图/参考图生图配置
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
