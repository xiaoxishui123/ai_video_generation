# AI视频生成插件 v0.0.60 更新日志

**发布日期**: 2026-01-05

## 🐛 Bug 修复

### 1. 修复文生视频工具 narration 参数未生效的问题

**问题描述**：
- 在文生视频工具（火山方舟平台）中，`narration`（旁白文本）参数虽然被正确传递到工具，但没有被发送给火山方舟 API
- 导致生成的视频配音是模型根据画面描述自动生成的，而不是用户提供的口播文案

**修复内容**：
- 在 `text_to_video.py` 中添加了 narration 参数的处理逻辑
- 当启用配音（`enable_audio=True`）且提供了 narration 时，将旁白内容合并到 prompt 中
- 格式：`{prompt}\n\n【配音旁白】{narration}`

**影响范围**：
- 文生视频工具（text_to_video）- 火山方舟平台
- 修复后，视频配音将根据用户提供的旁白文本生成

**代码变更**：
```python
# 修复前
full_prompt = prompt

# 修复后
if narration and enable_audio:
    full_prompt = f"{prompt}\n\n【配音旁白】{narration}"
else:
    full_prompt = prompt
```

---

## ✨ 功能优化

### 2. 优化图生视频工具"动作描述"参数的配置

**问题描述**：
- 图生视频工具的"动作描述"（prompt）参数在 Dify 工作流中无法通过 `{x}` 按钮选择上游节点的变量
- 原因是参数配置中使用了 `default` 预填充值

**优化内容**：
- 将 `default: 让图片动起来` 改为 `placeholder` 占位提示
- 移除预填充值，使 Dify UI 能够显示变量选择器

**修复后**：
- 用户可以在工作流中引用上游节点的变量作为动作描述
- 例如：`{{#code_build_prompt.video_prompt#}}`

**配置变更**：
```yaml
# 修复前
- name: prompt
  form: llm
  default: 让图片动起来

# 修复后
- name: prompt
  form: llm
  placeholder:
    zh_Hans: 让图片动起来
    en_US: Make the image come alive
```

---

## 📝 更新说明

### 升级指南

1. 下载 `ai_video_generation-v0.0.60.difypkg`
2. 在 Dify 插件管理中卸载旧版本
3. 安装新版本插件
4. **重要**：如果工作流中使用了图生视频工具，需要删除旧节点并重新添加，才能看到更新后的参数配置

### 兼容性

- 本次更新向后兼容
- 不影响现有工作流的其他功能
- 阿里云平台的 narration 处理逻辑保持不变（原本就正确）

---

## 📊 变更文件

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `tools/text_to_video.py` | Bug 修复 | 添加 narration 参数处理 |
| `tools/image_to_video.yaml` | 功能优化 | prompt 参数改用 placeholder |
| `manifest.yaml` | 版本更新 | 0.0.59 → 0.0.60 |

