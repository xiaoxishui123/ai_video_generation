# 🚀 版本更新说明 v0.0.52

**发布日期**: 2026-01-04  
**版本号**: v0.0.52

---

## ✨ 新功能

### 1. 火山方舟支持3种视频时长设置方式 🎬

根据火山方舟官方控制台，现在支持以下3种时长设置方式：

- **按秒数** (`duration_mode: "seconds"`) - 直接指定秒数（默认方式）
- **按帧数** (`duration_mode: "frames"`) - 指定视频帧数
- **智能时长** (`duration_mode: "smart"`) - 由模型自动智能选择时长

**新增参数**:
- `duration_mode`: 时长模式选择（seconds/frames/smart）
- `frames`: 帧数（按帧数模式时使用）

### 2. 新增高级参数支持 🔧

**火山方舟新增参数**:
- `fixed_camera`: 固定镜头（禁用镜头运动）
- `seed`: 种子值（-1表示随机，其他值可用于复现结果）

---

## 🐛 重要修复

### 1. 修复火山方舟参数传递问题 ⚠️

**问题**: 部分参数被错误地添加到 prompt 文本中，而不是通过 `parameters` 对象传递。

**修复内容**:
- ✅ `duration` 参数：从 prompt 中移除，改为通过 `parameters.duration` 传递（整数类型）
- ✅ `aspect_ratio` 参数：从 prompt 中移除，改为通过 `parameters.aspect_ratio` 传递（仅文生视频）
- ✅ 图生视频：移除 `aspect_ratio` 参数（由图片决定比例）

**影响范围**:
- 图生视频工具 (`image_to_video.py`)
- 文生视频工具 (`text_to_video.py`)

### 2. 修复音频参数优先级问题 🎵

**问题**: 当提供自定义音频URL时，仍然传递了 `generate_audio` 参数。

**修复**: 
- ✅ 当有 `audio_url` 时，不传递 `generate_audio` 参数（`audio_url` 优先级更高）
- ✅ 当 `enable_audio=False` 时，不传递任何音频相关参数

### 3. 修复文生视频工具在I2V模式下的参数传递 🔄

**问题**: 文生视频工具在检测到图片参数切换到I2V模式时，仍然传递了 `aspect_ratio` 参数。

**修复**: I2V模式下不传递 `aspect_ratio` 参数（图生视频由图片决定比例）

---

## 📊 测试覆盖

### 新增测试

1. **参数传递测试** (`test_volcengine_parameters.py`)
   - ✅ 图生视频参数传递验证
   - ✅ 文生视频参数传递验证
   - ✅ 边界情况测试

2. **图片和旁白参数测试** (`test_i2v_image_narration.py`)
   - ✅ 图片URL处理测试
   - ✅ 旁白参数处理测试
   - ✅ 自定义音频URL测试
   - ✅ 音频参数优先级测试

3. **模式切换测试** (`test_i2v_mode_in_t2v_tool.py`)
   - ✅ I2V模式参数传递验证
   - ✅ T2V模式参数传递验证

**测试结果**: 44项测试全部通过 ✅

---

## 📝 文档更新

### 新增文档

1. **VOLCENGINE_PARAMETER_FIX.md** - 火山方舟参数传递问题修复报告
2. **PARAMETER_TEST_REPORT.md** - 参数传递测试报告
3. **DURATION_SETTINGS_ANALYSIS.md** - 视频时长设置方式分析
4. **AUDIO_FIX_2026.md** - 音频问题修复文档

---

## 🔄 向后兼容性

### 兼容性说明

- ✅ **完全向后兼容**: 所有现有参数继续有效
- ✅ **默认行为**: 如果不指定 `duration_mode`，默认使用"按秒数"模式（与之前行为一致）
- ✅ **参数验证**: 空值或无效值会自动使用默认值，不会导致错误

### 迁移指南

**无需迁移**: 现有工作流和配置无需修改即可继续使用。

**可选升级**: 如需使用新功能（按帧数、智能时长、固定镜头、种子值），只需在工具参数中添加相应配置即可。

---

## 📋 技术细节

### 参数传递方式变更

**修复前**:
```python
# ❌ 错误：参数添加到 prompt 中
full_prompt = f"{prompt} --dur {duration} --ratio {aspect_ratio}"
```

**修复后**:
```python
# ✅ 正确：参数通过 parameters 对象传递
api_parameters = {
    "duration": int(duration),
    "aspect_ratio": aspect_ratio  # 仅文生视频
}
```

### 时长模式实现

```python
if duration_mode == "frames" and frames:
    api_parameters["frames"] = frames
elif duration_mode == "smart":
    api_parameters["smart_duration"] = True
else:
    api_parameters["duration"] = int(duration)
```

---

## 🎯 使用示例

### 按秒数模式（默认）

```yaml
duration_mode: "seconds"
duration: "5"
```

### 按帧数模式

```yaml
duration_mode: "frames"
frames: 150  # 150帧
```

### 智能时长模式

```yaml
duration_mode: "smart"
```

### 固定镜头

```yaml
fixed_camera: true
```

### 种子值（复现结果）

```yaml
seed: 12345  # 固定种子值，可复现相同结果
```

---

## ⚠️ 注意事项

1. **火山方舟时长范围**: 代码中未限制时长范围，建议查看官方文档确认支持范围
2. **参数验证**: 无效值会自动使用默认值，不会报错
3. **平台差异**: 
   - 阿里云 wan2.5: 固定5秒
   - 阿里云 wan2.6: 支持5/10/15秒
   - 火山方舟: 支持按秒数/按帧数/智能时长
   - JXINCM: 固定15秒

---

## 📚 参考链接

- [火山方舟视频生成文档](https://www.volcengine.com/docs/82379/1366799)
- [GitHub 仓库](https://github.com/xiaoxishui123/ai_video_generation)

---

## 🙏 致谢

感谢所有测试和反馈的用户！

---

**更新内容总结**:
- ✨ 新增3种时长设置方式
- 🐛 修复参数传递问题
- 🐛 修复音频参数优先级
- ✅ 44项测试全部通过
- 📝 完善文档和测试覆盖

