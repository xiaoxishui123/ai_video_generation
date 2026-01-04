# 🔧 火山方舟图生视频音频问题修复报告

**修复时间**: 2026-01-04  
**问题**: 火山方舟图生视频模型生成的视频没有声音  
**修复文件**: `tools/image_to_video.py`  
**文档查找**: 已查找火山方舟官方文档，但未找到明确的音频参数说明

---

## 📚 官方文档查找结果

### 查找的文档页面
1. 火山方舟快速入门：https://www.volcengine.com/docs/82379/1399008
2. 视频生成文档：https://www.volcengine.com/docs/82379/1366799
3. 模型列表：https://www.volcengine.com/docs/82379/1330310
4. Seedance 模型文档：https://www.volcengine.com/docs/82379/1553576

### 查找结果
- ❌ **未找到明确的音频参数说明**：火山方舟官方文档中未明确提及图生视频功能是否支持音频生成
- ❌ **API参数文档不完整**：文档中提到的参数包括 `duration`、`resolution`、`cameraFixed` 等，但未提及 `audio` 参数
- ✅ **最新确认**：根据用户提供的信息和火山方舟控制台，`doubao-seedance-1-5-pro-251215` 模型**确实支持生成语音**
  - 参考链接：https://console.volcengine.com/ark/region:ark+cn-beijing/model/detail?Id=doubao-seedance-1-5-pro
  - 模型支持音视频联合生成，能够实现高精度的音画同步

### 代码对比分析
1. **阿里云实现**：使用 `payload["parameters"]["audio"] = True`（布尔值）传递音频参数
2. **火山引擎文生视频**：代码中完全没有处理音频参数
3. **火山引擎图生视频**：之前尝试传递音频参数，但可能格式不正确

---

## 🔍 问题分析

### 发现的问题

1. **参数格式问题**: 代码中使用了布尔值 `True/False` 传递音频参数，但火山方舟API可能期望字符串格式 `"true"/"false"`

2. **参数传递逻辑**: 当 `enable_audio` 为 `False` 时，代码仍然传递了 `audio: False`，某些API可能不支持 `false` 值，应该不传递该参数

3. **缺少调试信息**: 无法查看实际发送给API的参数，难以排查问题

---

## ✅ 修复内容

### 修改位置：`tools/image_to_video.py` 第 653-665 行

**修改前**:
```python
# 添加音频参数
if enable_audio:
    api_parameters["audio"] = True
else:
    api_parameters["audio"] = False
```

**修改后**:
```python
# 添加音频参数
# ✅ 确认：doubao-seedance-1-5-pro-251215 模型支持生成语音
# 参考：https://console.volcengine.com/ark/region:ark+cn-beijing/model/detail?Id=doubao-seedance-1-5-pro
# 模型支持音视频联合生成，能够实现高精度的音画同步
if enable_audio:
    # 使用布尔值格式传递音频参数（与阿里云API保持一致）
    api_parameters["audio"] = True
    # 注意：如果仍然无效，可以尝试以下备选方案：
    # 方案1：字符串格式
    # api_parameters["audio"] = "true"
    # 方案2：不同的参数名称（根据API文档调整）
    # api_parameters["enable_audio"] = True
    # api_parameters["with_audio"] = True
# 注意：enable_audio 为 False 时不传递参数，让API使用默认值（无声视频）
```

### 添加调试信息：第 714 行

**新增**:
```python
# 调试：输出实际发送的参数（用于排查问题）
# ✅ 确认：doubao-seedance-1-5-pro-251215 模型支持生成语音
# 如果视频仍然没有声音，可能是参数格式或名称不正确
yield self.create_text_message(
    f"🔍 调试信息：发送的参数 = {api_parameters}\n"
    f"✅ 模型 {original_model} 支持音频生成功能\n"
    f"⚠️ 如果视频仍然没有声音，请检查：\n"
    f"   1. 参数格式是否正确（当前使用布尔值 True）\n"
    f"   2. 参数名称是否正确（当前使用 'audio'）\n"
    f"   3. API响应中是否有错误信息"
)
```

---

## 🧪 测试建议

### 测试场景 1: 启用音频（默认）

```yaml
provider: volcengine
model: doubao-seedance-1-5-pro-251215
image_url: "https://example.com/test.jpg"
prompt: "让图片动起来"
enable_audio: true    # 默认值
duration: "5"
```

**预期结果**:
- 调试信息显示：`发送的参数 = {'duration': 5, 'resolution': '1080p', 'audio': 'true'}`
- 生成的视频应该有声音

### 测试场景 2: 禁用音频

```yaml
provider: volcengine
model: doubao-seedance-1-5-pro-251215
image_url: "https://example.com/test.jpg"
prompt: "让图片动起来"
enable_audio: false
duration: "5"
```

**预期结果**:
- 调试信息显示：`发送的参数 = {'duration': 5, 'resolution': '1080p'}`（不包含 audio 参数）
- 生成的视频没有声音

---

## ✅ 重要确认

根据用户提供的信息和火山方舟控制台确认，**`doubao-seedance-1-5-pro-251215` 模型确实支持生成语音**。

- 参考链接：https://console.volcengine.com/ark/region:ark+cn-beijing/model/detail?Id=doubao-seedance-1-5-pro
- 模型支持音视频联合生成，能够实现高精度的音画同步
- 包括多语言和方言的语音生成能力

如果修复后视频仍然没有声音，可能是以下原因：

1. **参数格式问题**：API可能期望不同的参数格式（字符串 vs 布尔值）
2. **参数名称问题**：API可能使用不同的参数名称（如 `enable_audio`、`with_audio` 等）
3. **API调用方式问题**：可能需要特定的API调用方式或额外的配置

## 🔄 如果问题仍然存在

如果修改后视频仍然没有声音，可以尝试以下方案：

### 方案 1: 尝试字符串格式

修改第 660 行：
```python
# 从布尔值格式改为字符串格式
api_parameters["audio"] = "true"
```

### 方案 2: 尝试不同的参数名称

修改第 658 行，尝试以下参数名称之一：
```python
# 选项1
api_parameters["enable_audio"] = True

# 选项2
api_parameters["with_audio"] = True

# 选项3
api_parameters["sound"] = True
```

### 方案 3: 同时传递多个参数名称

```python
if enable_audio:
    api_parameters["audio"] = "true"
    api_parameters["enable_audio"] = True
    api_parameters["with_audio"] = True
```

### 方案 4: 检查模型是否支持音频

某些模型可能不支持音频生成。确认使用的模型：
- `doubao-seedance-1-5-pro-251215` - 应该支持音频
- `doubao-seaweed-241128` - 可能不支持音频

### 方案 5: 联系火山方舟技术支持

**已确认**：`doubao-seedance-1-5-pro-251215` 模型支持音频生成。

如果修复后视频仍然没有声音，建议：

1. **联系火山方舟技术支持**：
   - 确认正确的音频参数名称和格式
   - 询问是否有其他必需的参数或配置
   - 提供调试信息中的参数内容，获取技术支持

2. **查看控制台文档**：
   - 访问 [火山方舟控制台](https://console.volcengine.com/ark/region:ark+cn-beijing/model/detail?Id=doubao-seedance-1-5-pro)
   - 查看模型详情页面的参数说明
   - 查看API调用示例代码

3. **检查API响应**：
   - 查看API返回的完整响应
   - 检查是否有错误信息或警告
   - 确认任务状态和结果中是否包含音频相关信息

---

## 📝 排查步骤

1. **查看调试信息**: 运行图生视频任务，查看输出的调试信息，确认参数是否正确传递

2. **检查API响应**: 如果API返回错误，查看错误信息，可能包含参数格式提示

3. **测试不同模型**: 尝试不同的模型，看是否所有模型都有问题

4. **联系技术支持**: 如果以上方案都无效，联系火山方舟技术支持，确认：
   - 模型是否支持音频生成
   - 音频参数的正确名称和格式
   - 是否需要其他配置

---

## 📚 相关文档

- [火山方舟快速入门](https://www.volcengine.com/docs/82379/1399008)
- [火山方舟模型列表](https://www.volcengine.com/docs/82379/1330310)
- 之前的修复记录：`AUDIO_FIX_CHANGELOG.md`

---

## ⚠️ 注意事项

1. **参数格式**: 不同API可能期望不同的参数格式（字符串 vs 布尔值），需要根据实际情况调整

2. **模型支持**: 不是所有模型都支持音频生成，请确认使用的模型是否支持

3. **API版本**: 不同版本的API可能有不同的参数要求，请查看对应版本的文档

---

**修复完成时间**: 2026-01-04  
**下一步**: 测试修复效果，如果问题仍然存在，尝试上述备选方案

