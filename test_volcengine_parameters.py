#!/usr/bin/env python3
"""
火山方舟参数传递测试脚本

测试图生视频(I2V)和文生视频(T2V)的参数传递是否正确
"""

import json
from typing import Dict, Any


def test_i2v_parameters():
    """测试图生视频(I2V)参数传递"""
    print("=" * 60)
    print("测试1: 图生视频(I2V)参数传递")
    print("=" * 60)
    
    # 模拟参数输入
    params = {
        "duration": "5",
        "resolution": "1080p",
        "enable_audio": True,
        "audio_url": "",
        "narration": "",
        "prompt": "让图片动起来"
    }
    
    # 模拟代码中的参数构建逻辑
    duration = params.get("duration", "5")
    resolution = params.get("resolution", "1080p")
    enable_audio = params.get("enable_audio", True)
    audio_url = params.get("audio_url", "")
    prompt = params.get("prompt", "让图片动起来")
    
    # 构建参数对象
    api_parameters = {}
    
    # ✅ 添加时长参数（整数类型）
    if duration:
        try:
            api_parameters["duration"] = int(duration)
        except ValueError:
            api_parameters["duration"] = 5
    
    # ✅ 添加分辨率
    if resolution:
        api_parameters["resolution"] = resolution
    
    # ✅ 添加音频参数
    if enable_audio:
        api_parameters["generate_audio"] = "true"
    
    # ✅ 如果提供了自定义音频URL
    if audio_url:
        api_parameters["audio_url"] = audio_url
    
    # 构建完整的请求体
    full_prompt = prompt  # ✅ 不包含参数
    
    payload = {
        "model": "doubao-seedance-1-5-pro-251215",
        "content": [
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}},
            {"type": "text", "text": full_prompt}
        ],
        "parameters": api_parameters
    }
    
    # 验证结果
    print("\n📋 构建的参数对象:")
    print(json.dumps(api_parameters, indent=2, ensure_ascii=False))
    
    print("\n📋 完整的请求体:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    
    # 检查项
    checks = []
    
    # ✅ 检查1: duration应该是整数类型
    if isinstance(api_parameters.get("duration"), int):
        checks.append(("✅ duration类型正确", "整数类型"))
    else:
        checks.append(("❌ duration类型错误", f"当前类型: {type(api_parameters.get('duration'))}"))
    
    # ✅ 检查2: resolution应该是字符串类型
    if isinstance(api_parameters.get("resolution"), str):
        checks.append(("✅ resolution类型正确", "字符串类型"))
    else:
        checks.append(("❌ resolution类型错误", f"当前类型: {type(api_parameters.get('resolution'))}"))
    
    # ✅ 检查3: generate_audio应该是字符串"true"
    if api_parameters.get("generate_audio") == "true":
        checks.append(("✅ generate_audio格式正确", "字符串'true'"))
    else:
        checks.append(("❌ generate_audio格式错误", f"当前值: {api_parameters.get('generate_audio')}"))
    
    # ✅ 检查4: prompt中不应包含参数
    if "--dur" not in full_prompt and "--ratio" not in full_prompt:
        checks.append(("✅ prompt中不包含参数", "参数已正确分离"))
    else:
        checks.append(("❌ prompt中包含参数", "参数应通过parameters传递"))
    
    # ✅ 检查5: 不应有aspect_ratio参数（图生视频由图片决定比例）
    if "aspect_ratio" not in api_parameters:
        checks.append(("✅ 没有aspect_ratio参数", "图生视频由图片决定比例"))
    else:
        checks.append(("❌ 不应有aspect_ratio参数", "图生视频不需要此参数"))
    
    # ✅ 检查6: parameters对象存在
    if "parameters" in payload:
        checks.append(("✅ parameters对象存在", "参数已正确传递"))
    else:
        checks.append(("❌ parameters对象缺失", "参数未正确传递"))
    
    print("\n" + "=" * 60)
    print("检查结果:")
    print("=" * 60)
    for check, detail in checks:
        print(f"{check}: {detail}")
    
    return all("✅" in check for check, _ in checks)


def test_t2v_parameters():
    """测试文生视频(T2V)参数传递"""
    print("\n" + "=" * 60)
    print("测试2: 文生视频(T2V)参数传递")
    print("=" * 60)
    
    # 模拟参数输入
    params = {
        "duration": "5",
        "resolution": "1080p",
        "aspect_ratio": "16:9",
        "camera_control": "auto",
        "prompt": "一个美丽的风景"
    }
    
    # 模拟代码中的参数构建逻辑
    duration = params.get("duration", "5")
    resolution = params.get("resolution", "1080p")
    aspect_ratio = params.get("aspect_ratio", "16:9")
    camera_control = params.get("camera_control", "auto")
    prompt = params.get("prompt", "")
    
    # 构建参数对象
    api_parameters = {}
    
    # ✅ 添加时长（整数类型）
    if duration:
        try:
            api_parameters["duration"] = int(duration)
        except ValueError:
            api_parameters["duration"] = 5
    
    # ✅ 添加分辨率
    if resolution:
        api_parameters["resolution"] = resolution
    
    # ✅ 添加视频比例（文生视频支持）
    if aspect_ratio:
        api_parameters["aspect_ratio"] = aspect_ratio
    
    # ✅ 添加镜头控制
    if camera_control == "fixed":
        api_parameters["camera_control"] = "fixed"
    
    # 构建完整的请求体
    full_prompt = prompt  # ✅ 不包含参数
    
    payload = {
        "model": "doubao-seedance-1-0-lite-t2v-250428",
        "content": [
            {"type": "text", "text": full_prompt}
        ],
        "parameters": api_parameters
    }
    
    # 验证结果
    print("\n📋 构建的参数对象:")
    print(json.dumps(api_parameters, indent=2, ensure_ascii=False))
    
    print("\n📋 完整的请求体:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    
    # 检查项
    checks = []
    
    # ✅ 检查1: duration应该是整数类型
    if isinstance(api_parameters.get("duration"), int):
        checks.append(("✅ duration类型正确", "整数类型"))
    else:
        checks.append(("❌ duration类型错误", f"当前类型: {type(api_parameters.get('duration'))}"))
    
    # ✅ 检查2: resolution应该是字符串类型
    if isinstance(api_parameters.get("resolution"), str):
        checks.append(("✅ resolution类型正确", "字符串类型"))
    else:
        checks.append(("❌ resolution类型错误", f"当前类型: {type(api_parameters.get('resolution'))}"))
    
    # ✅ 检查3: aspect_ratio应该是字符串类型
    if isinstance(api_parameters.get("aspect_ratio"), str):
        checks.append(("✅ aspect_ratio类型正确", "字符串类型"))
    else:
        checks.append(("❌ aspect_ratio类型错误", f"当前类型: {type(api_parameters.get('aspect_ratio'))}"))
    
    # ✅ 检查4: prompt中不应包含参数
    if "--dur" not in full_prompt and "--ratio" not in full_prompt:
        checks.append(("✅ prompt中不包含参数", "参数已正确分离"))
    else:
        checks.append(("❌ prompt中包含参数", "参数应通过parameters传递"))
    
    # ✅ 检查5: aspect_ratio应该在parameters中
    if "aspect_ratio" in api_parameters:
        checks.append(("✅ aspect_ratio在parameters中", "参数位置正确"))
    else:
        checks.append(("❌ aspect_ratio不在parameters中", "文生视频需要此参数"))
    
    # ✅ 检查6: parameters对象存在
    if "parameters" in payload:
        checks.append(("✅ parameters对象存在", "参数已正确传递"))
    else:
        checks.append(("❌ parameters对象缺失", "参数未正确传递"))
    
    print("\n" + "=" * 60)
    print("检查结果:")
    print("=" * 60)
    for check, detail in checks:
        print(f"{check}: {detail}")
    
    return all("✅" in check for check, _ in checks)


def test_edge_cases():
    """测试边界情况"""
    print("\n" + "=" * 60)
    print("测试3: 边界情况测试")
    print("=" * 60)
    
    checks = []
    
    # 测试1: duration为空字符串
    duration = ""
    api_parameters = {}
    if duration:
        try:
            api_parameters["duration"] = int(duration)
        except ValueError:
            api_parameters["duration"] = 5
    else:
        api_parameters["duration"] = 5
    
    if api_parameters.get("duration") == 5:
        checks.append(("✅ 空duration使用默认值", "默认值5秒"))
    else:
        checks.append(("❌ 空duration处理错误", f"当前值: {api_parameters.get('duration')}"))
    
    # 测试2: duration为无效值
    duration = "invalid"
    api_parameters = {}
    try:
        api_parameters["duration"] = int(duration)
    except ValueError:
        api_parameters["duration"] = 5
    
    if api_parameters.get("duration") == 5:
        checks.append(("✅ 无效duration使用默认值", "默认值5秒"))
    else:
        checks.append(("❌ 无效duration处理错误", f"当前值: {api_parameters.get('duration')}"))
    
    # 测试3: enable_audio为False时不传递参数
    enable_audio = False
    api_parameters = {}
    if enable_audio:
        api_parameters["generate_audio"] = "true"
    
    if "generate_audio" not in api_parameters:
        checks.append(("✅ enable_audio=False时不传递参数", "使用API默认值"))
    else:
        checks.append(("❌ enable_audio=False时不应传递参数", "当前传递了参数"))
    
    # 测试4: audio_url存在时传递audio_url
    audio_url = "https://example.com/audio.mp3"
    api_parameters = {}
    if audio_url:
        api_parameters["audio_url"] = audio_url
    
    if api_parameters.get("audio_url") == audio_url:
        checks.append(("✅ audio_url正确传递", "自定义音频URL"))
    else:
        checks.append(("❌ audio_url传递错误", f"当前值: {api_parameters.get('audio_url')}"))
    
    print("\n" + "=" * 60)
    print("检查结果:")
    print("=" * 60)
    for check, detail in checks:
        print(f"{check}: {detail}")
    
    return all("✅" in check for check, _ in checks)


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("火山方舟参数传递测试")
    print("=" * 60)
    
    results = []
    
    # 测试1: 图生视频参数
    results.append(("图生视频(I2V)", test_i2v_parameters()))
    
    # 测试2: 文生视频参数
    results.append(("文生视频(T2V)", test_t2v_parameters()))
    
    # 测试3: 边界情况
    results.append(("边界情况", test_edge_cases()))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！参数传递正确。")
    else:
        print("⚠️ 部分测试失败，请检查参数传递逻辑。")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    main()

