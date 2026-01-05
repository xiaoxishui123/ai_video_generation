# Changelog v0.0.65 - 配音模式时长自动匹配修复

## 发布日期
2026-01-05

## 🔧 核心修复

### 配音模式时长自动匹配
- **问题**：启用配音（generate_audio）时，视频时长与配音内容不匹配
- **原因**：传递了固定的 duration 参数，覆盖了火山方舟的自动时长计算
- **修复**：当启用配音时，不再传递 duration 参数，让模型根据配音文本长度自动决定视频时长

### 参数传递方式优化
- 移除无效的 `smart_duration` 参数（火山方舟不支持）
- 参数通过 `--xx` 格式附加到 prompt 文本末尾（符合官方文档）
- 固定镜头参数使用 `--cf true` 格式传递

## 📝 代码变更

```python
# 之前（错误）
if duration_mode != "smart":
    prompt_params.append(f"--dur {int(duration)}")

# 现在（正确）
if enable_audio:
    pass  # 配音模式：不传递 duration，让模型自动决定
elif duration_mode != "smart":
    prompt_params.append(f"--dur {int(duration)}")
```

## 🎯 预期效果

| 配音文字 | 预期视频时长 |
|---------|------------|
| 30字 | ~5秒 |
| 60字 | ~10秒 |
| 100字 | ~15秒（受限于12秒最大值）|

## ⚠️ 注意事项

- Seedance 系列模型最大支持 **12秒** 视频时长
- 配音文本过长时建议拆分成多个场景
- 火山方舟配音功能仅 Seedance 1.5 Pro 支持

## 📦 升级方式

1. 下载 `ai_video_generation-v0.0.65.difypkg`
2. 在 Dify 后台更新插件
3. 重新发布工作流

## 🔗 相关文档

- [火山方舟 Seedance API 文档](https://www.volcengine.com/docs/82379/1631633)

