# AI视频生成插件 v0.0.62 更新日志

## 发布日期
2026-01-05

## 🎯 核心更新：视频时长精确获取

本版本专注于解决**视频时长与旁白时长不一致**的问题，确保口播视频工作流中视频片段能够精确对齐。

---

## ✨ 新增功能

### 1. 视频时长自动提取
- **从视频URL获取实际时长**：当火山方舟API未返回duration字段时，自动从视频文件提取
- **MP4解析**：解析MP4 moov/mvhd atom获取精确时长
- **智能下载**：使用HTTP Range请求，仅下载视频头部（128KB），避免完整下载

### 2. 多重时长获取策略
```
优先级：
1. 火山方舟API返回的duration字段
2. 从视频URL解析MP4头部获取
3. 场景预估时长（字数/4秒）
```

---

## 🔧 技术改进

### 新增方法

#### `_get_video_duration_from_url(video_url)`
从视频URL获取实际时长：
- 使用 Range 请求下载前128KB
- 解析MP4文件结构
- 对于小文件（<10MB）支持完整下载解析

#### `_parse_mp4_duration(data)`
解析MP4文件数据：
- 查找 moov atom
- 解析 mvhd atom
- 支持32位和64位版本
- 计算：`时长 = duration / timescale`

### 调试日志增强
```python
logging.info(f"[火山方舟] API返回结构: {result}")
logging.info(f"[火山方舟] content字段: {content}")
logging.info(f"[火山方舟] API返回的时长: {video_duration}")
logging.info(f"[火山方舟] 从视频URL提取的时长: {video_duration}")
```

---

## 📋 变更列表

### text_to_video.py
- ✅ 新增 `_get_video_duration_from_url()` 方法
- ✅ 新增 `_parse_mp4_duration()` 方法
- ✅ 火山方舟轮询结果增加时长提取逻辑
- ✅ JSON返回添加 `duration` 字段
- ✅ 增强调试日志输出

### manifest.yaml
- ✅ 版本号：0.0.61 → 0.0.62

---

## 🔄 兼容性

- 向后兼容 v0.0.61 及之前版本
- 需要配合更新后的口播视频工作流使用

---

## 📦 配套更新

### 口播文生视频工作流
- `code_extract_video` 节点优化：优先使用工具返回的实际视频时长
- 时长优先级：视频实际时长 > 场景预估时长 > 默认8秒

---

## 🧪 测试建议

1. 运行口播视频工作流
2. 查看Dify日志中 `[火山方舟]` 开头的输出
3. 确认视频时长是否正确提取
4. 检查剪映草稿中视频片段是否精确对齐

---

## 📝 已知限制

- MP4文件的moov atom必须在文件头部或文件较小（<10MB）时才能正确解析
- 某些CDN可能不支持Range请求，此时会回退到预估时长

