# 📊 视频时长设置方式分析报告

**分析时间**: 2026-01-04  
**分析范围**: 所有平台和模型的视频时长设置方式
**更新**: 已支持火山方舟的3种时长设置方式

---

## 📋 视频时长设置方式总览

### 火山方舟支持3种时长模式

根据火山方舟控制台截图，视频时长有**3种设置方式**：

| 模式 | 参数名 | 说明 |
|------|--------|------|
| **按秒数** | `duration` | 直接指定秒数（整数） |
| **按帧数** | `frames` | 指定帧数（整数） |
| **智能时长** | `smart_duration` | 自动智能选择时长 |

### 其他支持的参数（火山方舟）

| 参数 | 说明 |
|------|------|
| `resolution` | 分辨率（480p/720p） |
| `aspect_ratio` | 视频比例（21:9/16:9/4:3/1:1/3:4/9:16/智能比例） |
| `camera_control` | 固定镜头（禁用镜头运动） |
| `seed` | 种子值（-1表示随机） |
| `generate_audio` | 声音开关（生成有声视频） |

---

## 🏢 各平台时长设置详情

### 1. 阿里云百炼平台

#### 1.1 通义万相 2.5 (wan2.5)
- **设置方式**: 通过 `parameters.duration` 传递
- **支持值**: **固定5秒**（不可更改）
- **参数类型**: 整数（但实际固定为5）
- **代码位置**: `tools/image_to_video.py` 第422行
- **说明**: 即使传递其他值，也会被固定为5秒

```python
# wan2.5 不支持自定义时长，固定5秒
# 代码中虽然可以传递duration，但API会忽略
```

#### 1.2 通义万相 2.6 (wan2.6)
- **设置方式**: 通过 `parameters.duration` 传递
- **支持值**: **5秒、10秒、15秒**
- **参数类型**: 整数
- **代码位置**: `tools/image_to_video.py` 第422行
- **默认值**: 5秒
- **配置选项**: 
  - `"5"` - 5秒
  - `"10"` - 10秒
  - `"15"` - 15秒（仅wan2.6支持）

```python
# wan2.6 支持自定义时长
payload["parameters"]["duration"] = int(duration)  # 5, 10, 或 15
```

---

### 2. 火山方舟平台

#### 2.1 图生视频 (I2V)
- **设置方式**: 通过 `parameters.duration` 传递
- **支持值**: **整数类型**（具体支持范围需查看官方文档）
- **参数类型**: 整数
- **代码位置**: `tools/image_to_video.py` 第645-650行
- **默认值**: 5秒
- **处理逻辑**:
  ```python
  if duration:
      try:
          api_parameters["duration"] = int(duration)
      except ValueError:
          api_parameters["duration"] = 5  # 默认值
  ```

#### 2.2 文生视频 (T2V)
- **设置方式**: 通过 `parameters.duration` 传递
- **支持值**: **整数类型**（具体支持范围需查看官方文档）
- **参数类型**: 整数
- **代码位置**: `tools/text_to_video.py` 第575-580行
- **默认值**: 5秒
- **处理逻辑**:
  ```python
  if duration:
      try:
          api_parameters["duration"] = int(duration)
      except ValueError:
          api_parameters["duration"] = 5  # 默认值
  ```

**注意**: 火山方舟的duration参数支持范围需要查看官方文档确认，代码中只做了基本的类型转换和默认值处理。

---

### 3. JXINCM平台 (Sora-2)

- **设置方式**: 通过 `payload.duration` 传递
- **支持值**: **固定15秒**（不可更改）
- **参数类型**: 整数（固定为15）
- **代码位置**: 
  - `tools/image_to_video.py` 第925行
  - `tools/text_to_video.py` 第844行
- **说明**: 即使传递其他值，也会被固定为15秒

```python
# JXINCM 固定15秒
payload = {
    "duration": 15,  # 固定值
    # ...
}
```

---

## 📝 参数传递方式对比

| 平台 | 模型 | 参数位置 | 参数类型 | 支持值 | 默认值 | 是否可自定义 |
|------|------|---------|---------|--------|--------|------------|
| 阿里云 | wan2.5 | `parameters.duration` | 整数 | 固定5秒 | 5 | ❌ 否 |
| 阿里云 | wan2.6 | `parameters.duration` | 整数 | 5/10/15秒 | 5 | ✅ 是 |
| 火山方舟 | I2V/T2V | `parameters.duration` | 整数 | 需查文档 | 5 | ✅ 是 |
| JXINCM | Sora-2 | `payload.duration` | 整数 | 固定15秒 | 15 | ❌ 否 |

---

## 🔍 代码中的处理逻辑

### 1. 参数获取和验证

所有平台都使用相同的参数获取逻辑：

```python
# 处理 duration 参数，确保空字符串或无效值使用默认值
duration_raw = params.get("duration", "5")
if not duration_raw or (isinstance(duration_raw, str) and not duration_raw.strip()):
    duration = "5"
else:
    duration = str(duration_raw).strip()
```

### 2. 参数转换

#### 阿里云平台
```python
# wan2.6 支持自定义时长
if is_wan26:
    payload["parameters"]["duration"] = int(duration)
```

#### 火山方舟平台
```python
# 添加时长参数（整数类型）
if duration:
    try:
        api_parameters["duration"] = int(duration)
    except ValueError:
        api_parameters["duration"] = 5  # 默认值
```

#### JXINCM平台
```python
# 固定15秒
payload = {
    "duration": 15,  # 固定值，不读取参数
    # ...
}
```

---

## ⚠️ 注意事项

### 1. 参数验证
- ✅ 所有平台都会验证duration参数
- ✅ 空值或无效值会使用默认值（5秒）
- ✅ 类型转换错误会回退到默认值

### 2. 平台限制
- ⚠️ **wan2.5**: 固定5秒，传递其他值无效
- ⚠️ **wan2.6**: 仅支持5/10/15秒，其他值可能无效
- ⚠️ **JXINCM**: 固定15秒，传递其他值无效
- ⚠️ **火山方舟**: 支持范围需查看官方文档

### 3. 默认值处理
- 所有平台默认值都是5秒（JXINCM除外，固定15秒）
- 如果参数为空或无效，会自动使用默认值

---

## 📊 配置选项（YAML文件）

### 图生视频工具 (`image_to_video.yaml`)
```yaml
- name: duration
  type: select
  default: "5"
  options:
    - value: "5"
      label: 5秒
    - value: "10"
      label: 10秒
    - value: "15"
      label: 15秒 (仅通义万相2.6)
```

### 文生视频工具 (`text_to_video.yaml`)
```yaml
- name: duration
  type: select
  default: "5"
  options:
    - value: "5"
      label: 5秒
    - value: "10"
      label: 10秒
    - value: "15"
      label: 15秒 (仅通义万相2.6)
```

---

## 🔧 建议改进

### 1. 火山方舟时长范围
- ⚠️ **问题**: 代码中未明确火山方舟支持的时长范围
- ✅ **建议**: 查看官方文档，添加时长范围验证

### 2. 参数验证增强
- ⚠️ **问题**: 当前只验证类型，未验证值范围
- ✅ **建议**: 根据平台和模型添加值范围验证

### 3. 错误提示
- ⚠️ **问题**: 无效值会静默使用默认值
- ✅ **建议**: 添加警告提示，告知用户使用了默认值

---

## 📝 总结

### 视频时长设置方式：

1. **通过参数传递**（主要方式）
   - 参数名: `duration`
   - 参数类型: 字符串（转换为整数）
   - 默认值: "5"（5秒）

2. **平台特定限制**:
   - 阿里云 wan2.5: 固定5秒
   - 阿里云 wan2.6: 5/10/15秒可选
   - 火山方舟: 整数类型（范围需查文档）
   - JXINCM: 固定15秒

3. **参数处理流程**:
   ```
   获取参数 → 验证非空 → 转换为整数 → 传递给API
   ```

---

**最后更新**: 2026-01-04

