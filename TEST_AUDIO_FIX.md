# 🧪 音频修复测试指南

## 快速测试步骤

### 1️⃣ 重新打包插件

```bash
cd /home/dify/ai_video_generation
./build.sh
```

### 2️⃣ 在 Dify 中重新安装

1. 卸载旧版本插件
2. 上传新的 `.difypkg` 文件
3. 安装并配置火山引擎 API Key

### 3️⃣ 测试音频功能

**测试1: 默认配音（推荐先测试这个）**

在工作流中添加"图片生成视频"节点：
- 平台: `volcengine`
- 模型: `doubao-seedance-1-5-pro-251215`
- 图片: 上传任意图片
- 提示词: `让图片动起来`
- 启用自动配音: `true` (默认)
- 时长: `5`

**查看提示信息**：
应该显示 "🎤 配音: 自动生成"

**检查生成结果**：
下载视频并播放，检查是否有声音

---

**测试2: 禁用音频**

- 启用自动配音: `false`

**查看提示信息**：
应该显示 "🔇 音频: 无声视频"

---

**测试3: 带旁白**

- 提示词: `美丽的风景`
- 旁白文本: `这是一个宁静的早晨`
- 启用自动配音: `true`

**查看提示信息**：
应该显示 "📜 旁白: 这是一个宁静的早晨"

---

## 🔍 调试技巧

### 查看实际提交的 prompt

在插件日志中应该能看到类似：

```
提交的 prompt: 让图片动起来 --duration 5 --audio enable
```

### 如果视频仍然没有声音

尝试以下参数替换 (需要修改代码)：

1. `--audio true` (替换 `--audio enable`)
2. `--audio on`
3. `--sound enable`
4. `--enable-audio`

### 快速修改测试

编辑 `tools/image_to_video.py` 第 627-630 行：

```python
# 当前
if enable_audio and "--audio" not in full_prompt:
    full_prompt = f"{full_prompt} --audio enable"

# 尝试1: 改为 true
if enable_audio and "--audio" not in full_prompt:
    full_prompt = f"{full_prompt} --audio true"

# 尝试2: 改为 on
if enable_audio and "--audio" not in full_prompt:
    full_prompt = f"{full_prompt} --audio on"
```

---

## ✅ 成功标志

1. 提示信息正确显示音频配置
2. 生成的视频有声音
3. 禁用音频时视频无声
4. 旁白文本能影响配音内容

---

## ❌ 如果还是没声音

可能原因：
1. 火山引擎不支持 `--audio` 参数 (需要查官方文档)
2. 参数名称错误 (需要测试其他参数名)
3. Seedance 1.5 Pro 本身不支持音频 (需要确认)

建议：
- 临时使用阿里云 `wan2.6-i2v` (已验证有音频功能)
- 联系火山引擎技术支持确认参数

