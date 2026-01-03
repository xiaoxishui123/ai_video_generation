# 🔧 火山引擎音频参数修复报告

**修复时间**: 2026-01-03  
**版本**: 0.0.45 → 0.0.46 (建议)  
**修复内容**: 添加火山引擎 Seedance I2V 音频参数支持

---

## ✅ 已修改的文件

### 1. `tools/image_to_video.py` (核心修复)

#### 修改位置：第 611-644 行

**原代码**：
```python
full_prompt = f"{prompt} --duration {duration}"
```

**修改后**：
```python
# 🆕 读取音频参数
enable_audio = params.get("enable_audio", True)
audio_url_raw = params.get("audio_url", "")
narration = params.get("narration", "")

# 🆕 构建完整的 prompt（包含音频参数）
full_prompt = f"{prompt} --duration {duration}"

# 添加音频参数
if enable_audio and "--audio" not in full_prompt:
    full_prompt = f"{full_prompt} --audio enable"
elif not enable_audio and "--audio" not in full_prompt:
    full_prompt = f"{full_prompt} --audio disable"

# 如果提供了自定义音频URL
if audio_url and "--audio-url" not in full_prompt:
    full_prompt = f"{full_prompt} --audio-url {audio_url}"

# 如果有旁白文本，合并到 prompt 中
if narration and enable_audio and not audio_url:
    enhanced_prompt = f"{prompt}。旁白内容：{narration}"
    full_prompt = f"{enhanced_prompt} --duration {duration}"
    if enable_audio and "--audio" not in full_prompt:
        full_prompt = f"{full_prompt} --audio enable"
```

#### 修改位置：第 663-682 行（用户提示信息）

**新增**：显示音频配置状态
```python
# 构建音频配置信息
audio_info = ""
if audio_url:
    audio_info = f"🎵 音频: 使用自定义音频\n"
elif enable_audio:
    audio_info = f"🎤 配音: 自动生成\n"
else:
    audio_info = f"🔇 音频: 无声视频\n"
if narration and enable_audio and not audio_url:
    audio_info += f"📜 旁白: {narration[:30]}...\n"
```

---

### 2. `tools/image_to_video.yaml` (配置文件)

#### 修改内容：

**参数 `enable_audio`** (行 215-216)：
```yaml
# 修改前
zh_Hans: 【仅通义万相2.5/2.6】为视频自动生成语音旁白

# 修改后
zh_Hans: 为视频自动生成语音旁白（通义万相2.5/2.6、火山引擎Seedance支持）
```

**参数 `audio_url`** (行 226-228)：
```yaml
# 添加说明：仅通义万相支持自定义音频URL
zh_Hans: 自定义音频文件URL（可选，传入后会使用此音频而非自动生成，仅通义万相支持）
```

**参数 `narration`** (行 237-238)：
```yaml
# 修改前
zh_Hans: 旁白文本，模型会根据此文本自动生成配音（需启用自动配音）

# 修改后
zh_Hans: 旁白文本，模型会根据此文本自动生成配音（需启用自动配音，通义万相/火山引擎支持）
```

---

## 🔬 测试验证建议

### 测试场景 1: 默认自动配音

```yaml
provider: volcengine
model: doubao-seedance-1-5-pro-251215
image_url: "https://example.com/test.jpg"
prompt: "让图片动起来"
enable_audio: true    # 默认值
duration: "5"
```

**预期结果**：
- 提示信息显示 "🎤 配音: 自动生成"
- 提交的 prompt: `让图片动起来 --duration 5 --audio enable`
- 生成的视频应该有声音

---

### 测试场景 2: 禁用音频

```yaml
provider: volcengine
model: doubao-seedance-1-5-pro-251215
image_url: "https://example.com/test.jpg"
prompt: "让图片动起来"
enable_audio: false
duration: "5"
```

**预期结果**：
- 提示信息显示 "🔇 音频: 无声视频"
- 提交的 prompt: `让图片动起来 --duration 5 --audio disable`
- 生成的视频没有声音

---

### 测试场景 3: 带旁白文本

```yaml
provider: volcengine
model: doubao-seedance-1-5-pro-251215
image_url: "https://example.com/test.jpg"
prompt: "美丽的风景画面"
narration: "这是一个宁静的早晨，阳光洒在大地上"
enable_audio: true
duration: "5"
```

**预期结果**：
- 提示信息显示 "🎤 配音: 自动生成" 和 "📜 旁白: 这是一个宁静的早晨..."
- 提交的 prompt: `美丽的风景画面。旁白内容：这是一个宁静的早晨，阳光洒在大地上 --duration 5 --audio enable`
- 生成的视频配音应该包含旁白内容

---

## ⚠️ 已知限制

1. **自定义音频URL**: 火山引擎可能不支持 `--audio-url` 参数，需要实际测试验证
2. **参数名称**: 使用的是 `--audio enable/disable`，可能需要根据官方文档调整
3. **旁白文本**: 通过将旁白内容合并到 prompt 实现，效果需要验证

---

## 🎯 下一步行动

1. **立即测试**: 在 Dify 中导入更新后的插件并测试
2. **验证参数**: 检查生成的视频是否有声音
3. **调整参数**: 如果 `--audio enable` 无效，尝试其他参数名：
   - `--audio true`
   - `--sound on`
   - `--enable-audio`
4. **反馈官方**: 如果所有参数都无效，联系火山引擎技术支持确认正确参数

---

## 📝 备份文件

原文件已备份至：
- `tools/image_to_video.py.backup`

如需恢复：
```bash
cp tools/image_to_video.py.backup tools/image_to_video.py
```

---

## 📚 参考资料

- [火山方舟快速入门](https://www.volcengine.com/docs/82379/1399008)
- [火山方舟模型列表](https://www.volcengine.com/docs/82379/1330310)
- 问题分析报告: `/tmp/volcengine_audio_issue_analysis.md`

