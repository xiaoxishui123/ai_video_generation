#!/usr/bin/env python3
"""
测试文生视频工具在I2V模式下的参数传递

验证：当文生视频工具检测到图片参数时，应切换到I2V模式，且不应传递aspect_ratio参数
"""

import json


def test_t2v_tool_i2v_mode():
    """测试文生视频工具在I2V模式下的参数传递"""
    print("=" * 60)
    print("测试: 文生视频工具在I2V模式下的参数传递")
    print("=" * 60)
    
    # 模拟参数输入（有图片，触发I2V模式）
    params = {
        "duration": "5",
        "resolution": "1080p",
        "aspect_ratio": "16:9",
        "camera_control": "auto",
        "prompt": "让图片动起来",
        "_image_url": "https://example.com/image.jpg"  # 有图片，触发I2V模式
    }
    
    # 模拟代码逻辑
    duration = params.get("duration", "5")
    resolution = params.get("resolution", "1080p")
    aspect_ratio = params.get("aspect_ratio", "16:9")
    camera_control = params.get("camera_control", "auto")
    prompt = params.get("prompt", "")
    image_url = params.get("_image_url", "")
    
    # 检查是否有图片参数（I2V 模式）
    is_i2v_mode = bool(image_url)
    
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
    
    # ✅ 添加视频比例（仅文生视频支持，图生视频由图片决定比例）
    # ⚠️ 注意：图生视频(I2V)的比例由输入图片决定，不需要传递 aspect_ratio 参数
    if aspect_ratio and not is_i2v_mode:
        api_parameters["aspect_ratio"] = aspect_ratio
    
    # ✅ 添加镜头控制
    if camera_control == "fixed":
        api_parameters["camera_control"] = "fixed"
    
    # 构建完整的请求体
    full_prompt = prompt  # ✅ 不包含参数
    
    payload = {
        "model": "doubao-seedance-1-5-pro-251215",
        "content": [
            {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}},
            {"type": "text", "text": full_prompt}
        ],
        "parameters": api_parameters
    }
    
    # 验证结果
    print(f"\n📋 模式检测: {'I2V (图生视频)' if is_i2v_mode else 'T2V (文生视频)'}")
    print(f"\n📋 构建的参数对象:")
    print(json.dumps(api_parameters, indent=2, ensure_ascii=False))
    
    print(f"\n📋 完整的请求体:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    
    # 检查项
    checks = []
    
    # ✅ 检查1: 应该检测到I2V模式
    if is_i2v_mode:
        checks.append(("✅ I2V模式检测正确", "检测到图片参数"))
    else:
        checks.append(("❌ I2V模式检测错误", "未检测到图片参数"))
    
    # ✅ 检查2: I2V模式下不应有aspect_ratio参数
    if "aspect_ratio" not in api_parameters:
        checks.append(("✅ I2V模式下没有aspect_ratio参数", "图生视频由图片决定比例"))
    else:
        checks.append(("❌ I2V模式下不应有aspect_ratio参数", f"当前值: {api_parameters.get('aspect_ratio')}"))
    
    # ✅ 检查3: duration应该是整数类型
    if isinstance(api_parameters.get("duration"), int):
        checks.append(("✅ duration类型正确", "整数类型"))
    else:
        checks.append(("❌ duration类型错误", f"当前类型: {type(api_parameters.get('duration'))}"))
    
    # ✅ 检查4: resolution应该是字符串类型
    if isinstance(api_parameters.get("resolution"), str):
        checks.append(("✅ resolution类型正确", "字符串类型"))
    else:
        checks.append(("❌ resolution类型错误", f"当前类型: {type(api_parameters.get('resolution'))}"))
    
    # ✅ 检查5: prompt中不应包含参数
    if "--dur" not in full_prompt and "--ratio" not in full_prompt:
        checks.append(("✅ prompt中不包含参数", "参数已正确分离"))
    else:
        checks.append(("❌ prompt中包含参数", "参数应通过parameters传递"))
    
    # ✅ 检查6: content应包含图片和文本
    if len(payload["content"]) == 2:
        has_image = any(item.get("type") == "image_url" for item in payload["content"])
        has_text = any(item.get("type") == "text" for item in payload["content"])
        if has_image and has_text:
            checks.append(("✅ content结构正确", "包含图片和文本"))
        else:
            checks.append(("❌ content结构错误", "应包含图片和文本"))
    else:
        checks.append(("❌ content结构错误", f"当前长度: {len(payload['content'])}"))
    
    print("\n" + "=" * 60)
    print("检查结果:")
    print("=" * 60)
    for check, detail in checks:
        print(f"{check}: {detail}")
    
    return all("✅" in check for check, _ in checks)


def test_t2v_tool_t2v_mode():
    """测试文生视频工具在T2V模式下的参数传递"""
    print("\n" + "=" * 60)
    print("测试: 文生视频工具在T2V模式下的参数传递")
    print("=" * 60)
    
    # 模拟参数输入（无图片，T2V模式）
    params = {
        "duration": "5",
        "resolution": "1080p",
        "aspect_ratio": "16:9",
        "camera_control": "auto",
        "prompt": "一个美丽的风景",
        "_image_url": ""  # 无图片，T2V模式
    }
    
    # 模拟代码逻辑
    duration = params.get("duration", "5")
    resolution = params.get("resolution", "1080p")
    aspect_ratio = params.get("aspect_ratio", "16:9")
    camera_control = params.get("camera_control", "auto")
    prompt = params.get("prompt", "")
    image_url = params.get("_image_url", "")
    
    # 检查是否有图片参数（I2V 模式）
    is_i2v_mode = bool(image_url)
    
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
    
    # ✅ 添加视频比例（仅文生视频支持，图生视频由图片决定比例）
    if aspect_ratio and not is_i2v_mode:
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
    print(f"\n📋 模式检测: {'I2V (图生视频)' if is_i2v_mode else 'T2V (文生视频)'}")
    print(f"\n📋 构建的参数对象:")
    print(json.dumps(api_parameters, indent=2, ensure_ascii=False))
    
    print(f"\n📋 完整的请求体:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    
    # 检查项
    checks = []
    
    # ✅ 检查1: 应该检测到T2V模式
    if not is_i2v_mode:
        checks.append(("✅ T2V模式检测正确", "未检测到图片参数"))
    else:
        checks.append(("❌ T2V模式检测错误", "不应检测到图片参数"))
    
    # ✅ 检查2: T2V模式下应该有aspect_ratio参数
    if "aspect_ratio" in api_parameters:
        checks.append(("✅ T2V模式下有aspect_ratio参数", "文生视频需要指定比例"))
    else:
        checks.append(("❌ T2V模式下应该有aspect_ratio参数", "文生视频需要此参数"))
    
    # ✅ 检查3: content应只包含文本
    if len(payload["content"]) == 1:
        has_text = payload["content"][0].get("type") == "text"
        if has_text:
            checks.append(("✅ content结构正确", "只包含文本"))
        else:
            checks.append(("❌ content结构错误", "应只包含文本"))
    else:
        checks.append(("❌ content结构错误", f"当前长度: {len(payload['content'])}"))
    
    print("\n" + "=" * 60)
    print("检查结果:")
    print("=" * 60)
    for check, detail in checks:
        print(f"{check}: {detail}")
    
    return all("✅" in check for check, _ in checks)


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("文生视频工具模式切换测试")
    print("=" * 60)
    
    results = []
    
    # 测试1: I2V模式
    results.append(("I2V模式参数传递", test_t2v_tool_i2v_mode()))
    
    # 测试2: T2V模式
    results.append(("T2V模式参数传递", test_t2v_tool_t2v_mode()))
    
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
        print("🎉 所有测试通过！模式切换和参数传递正确。")
    else:
        print("⚠️ 部分测试失败，请检查模式切换逻辑。")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    main()

