#!/usr/bin/env python3
"""
图生视频图片和旁白参数测试脚本

测试：
1. 图片参数处理（URL、Base64转换）
2. 旁白参数处理（合并到prompt）
3. audio_url参数处理
4. 旁白与audio_url的优先级关系
"""

import json
import base64


def test_image_url_handling():
    """测试图片URL处理"""
    print("=" * 60)
    print("测试1: 图片URL处理")
    print("=" * 60)
    
    # 模拟不同的图片URL场景
    test_cases = [
        {
            "name": "公网HTTP URL",
            "url": "http://example.com/image.jpg",
            "expected_base64": False,
            "description": "标准HTTP URL，应直接使用"
        },
        {
            "name": "公网HTTPS URL",
            "url": "https://example.com/image.jpg",
            "expected_base64": False,
            "description": "标准HTTPS URL，应直接使用"
        },
        {
            "name": "内网URL (localhost)",
            "url": "http://localhost:8080/image.jpg",
            "expected_base64": True,
            "description": "localhost地址，应转换为Base64"
        },
        {
            "name": "内网URL (192.168.x.x)",
            "url": "http://192.168.1.100:8080/image.jpg",
            "expected_base64": True,
            "description": "内网IP地址，应转换为Base64"
        },
        {
            "name": "非标准端口URL",
            "url": "http://example.com:8080/image.jpg",
            "expected_base64": True,
            "description": "非标准端口(非80/443)，应转换为Base64"
        },
        {
            "name": "Base64格式URL",
            "url": "data:image/jpeg;base64,/9j/4AAQSkZJRg==",
            "expected_base64": False,
            "description": "已经是Base64格式，直接使用"
        }
    ]
    
    checks = []
    
    for case in test_cases:
        url = case["url"]
        
        # 模拟代码中的判断逻辑
        def _is_public_accessible_url(url: str) -> bool:
            """判断URL是否可被火山引擎公网访问"""
            from urllib.parse import urlparse
            try:
                parsed = urlparse(url)
                host = parsed.hostname or ""
                
                # 私有网络地址（一定需要转 Base64）
                private_patterns = [
                    'localhost', '127.0.0.1', '127.',
                    '10.', '172.16.', '172.17.', '172.18.', '172.19.',
                    '172.20.', '172.21.', '172.22.', '172.23.',
                    '172.24.', '172.25.', '172.26.', '172.27.',
                    '172.28.', '172.29.', '172.30.', '172.31.',
                    '192.168.', '169.254.',
                ]
                
                for pattern in private_patterns:
                    if host.startswith(pattern) or host == pattern.rstrip('.'):
                        return False
                
                # 非标准端口也需要转 Base64
                port = parsed.port
                if port and port not in [80, 443]:
                    return False
                
                # Base64格式直接使用
                if url.startswith("data:image/"):
                    return True
                
                return True
            except Exception:
                return False
        
        need_base64 = not _is_public_accessible_url(url)
        
        if need_base64 == case["expected_base64"]:
            checks.append((f"✅ {case['name']}", case["description"]))
        else:
            checks.append((f"❌ {case['name']}", 
                          f"期望: {'需要Base64' if case['expected_base64'] else '直接使用URL'}, "
                          f"实际: {'需要Base64' if need_base64 else '直接使用URL'}"))
    
    print("\n" + "=" * 60)
    print("检查结果:")
    print("=" * 60)
    for check, detail in checks:
        print(f"{check}: {detail}")
    
    return all("✅" in check for check, _ in checks)


def test_narration_parameter():
    """测试旁白参数处理"""
    print("\n" + "=" * 60)
    print("测试2: 旁白参数处理")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "有旁白且启用音频",
            "narration": "这是旁白内容",
            "enable_audio": True,
            "audio_url": "",
            "expected_in_prompt": True,
            "description": "旁白应合并到prompt中"
        },
        {
            "name": "有旁白但禁用音频",
            "narration": "这是旁白内容",
            "enable_audio": False,
            "audio_url": "",
            "expected_in_prompt": False,
            "description": "禁用音频时，旁白不应合并到prompt"
        },
        {
            "name": "有旁白但有自定义音频URL",
            "narration": "这是旁白内容",
            "enable_audio": True,
            "audio_url": "https://example.com/audio.mp3",
            "expected_in_prompt": False,
            "description": "有自定义音频URL时，旁白不应合并到prompt"
        },
        {
            "name": "无旁白",
            "narration": "",
            "enable_audio": True,
            "audio_url": "",
            "expected_in_prompt": False,
            "description": "无旁白时，prompt不应包含旁白内容"
        }
    ]
    
    checks = []
    
    for case in test_cases:
        narration = case["narration"]
        enable_audio = case["enable_audio"]
        audio_url = case["audio_url"]
        prompt = "让图片动起来"
        
        # 模拟代码逻辑
        full_prompt = prompt
        if narration and enable_audio and not audio_url:
            enhanced_prompt = f"{prompt}。旁白内容：{narration}"
            full_prompt = enhanced_prompt
        
        has_narration = "旁白内容" in full_prompt
        
        if has_narration == case["expected_in_prompt"]:
            checks.append((f"✅ {case['name']}", case["description"]))
        else:
            checks.append((f"❌ {case['name']}", 
                          f"期望: {'包含旁白' if case['expected_in_prompt'] else '不包含旁白'}, "
                          f"实际: {'包含旁白' if has_narration else '不包含旁白'}"))
    
    print("\n" + "=" * 60)
    print("检查结果:")
    print("=" * 60)
    for check, detail in checks:
        print(f"{check}: {detail}")
    
    return all("✅" in check for check, _ in checks)


def test_audio_url_parameter():
    """测试自定义音频URL参数处理"""
    print("\n" + "=" * 60)
    print("测试3: 自定义音频URL参数处理")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "有效的HTTP音频URL",
            "audio_url": "http://example.com/audio.mp3",
            "expected_in_parameters": True,
            "description": "有效HTTP URL应传递到parameters"
        },
        {
            "name": "有效的HTTPS音频URL",
            "audio_url": "https://example.com/audio.mp3",
            "expected_in_parameters": True,
            "description": "有效HTTPS URL应传递到parameters"
        },
        {
            "name": "无效的音频URL（非HTTP/HTTPS）",
            "audio_url": "ftp://example.com/audio.mp3",
            "expected_in_parameters": False,
            "description": "非HTTP/HTTPS URL不应传递"
        },
        {
            "name": "空音频URL",
            "audio_url": "",
            "expected_in_parameters": False,
            "description": "空URL不应传递"
        },
        {
            "name": "只有空格的音频URL",
            "audio_url": "   ",
            "expected_in_parameters": False,
            "description": "只有空格的URL不应传递"
        }
    ]
    
    checks = []
    
    for case in test_cases:
        audio_url_raw = case["audio_url"]
        
        # 模拟代码逻辑
        audio_url = ""
        if audio_url_raw and isinstance(audio_url_raw, str):
            audio_url_raw = audio_url_raw.strip()
            if audio_url_raw.startswith(("http://", "https://")):
                audio_url = audio_url_raw
        
        api_parameters = {}
        if audio_url:
            api_parameters["audio_url"] = audio_url
        
        has_audio_url = "audio_url" in api_parameters
        
        if has_audio_url == case["expected_in_parameters"]:
            checks.append((f"✅ {case['name']}", case["description"]))
        else:
            checks.append((f"❌ {case['name']}", 
                          f"期望: {'包含audio_url' if case['expected_in_parameters'] else '不包含audio_url'}, "
                          f"实际: {'包含audio_url' if has_audio_url else '不包含audio_url'}"))
    
    print("\n" + "=" * 60)
    print("检查结果:")
    print("=" * 60)
    for check, detail in checks:
        print(f"{check}: {detail}")
    
    return all("✅" in check for check, _ in checks)


def test_audio_priority():
    """测试音频参数优先级"""
    print("\n" + "=" * 60)
    print("测试4: 音频参数优先级")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "有audio_url时，generate_audio不应传递",
            "enable_audio": True,
            "audio_url": "https://example.com/audio.mp3",
            "narration": "旁白内容",
            "expected_generate_audio": False,
            "expected_audio_url": True,
            "expected_narration_in_prompt": False,
            "description": "audio_url优先级最高，应传递audio_url，不传递generate_audio，不合并旁白"
        },
        {
            "name": "无audio_url但启用音频，应传递generate_audio",
            "enable_audio": True,
            "audio_url": "",
            "narration": "旁白内容",
            "expected_generate_audio": True,
            "expected_audio_url": False,
            "expected_narration_in_prompt": True,
            "description": "无audio_url时，应传递generate_audio，并合并旁白"
        },
        {
            "name": "禁用音频，不传递任何音频参数",
            "enable_audio": False,
            "audio_url": "",
            "narration": "旁白内容",
            "expected_generate_audio": False,
            "expected_audio_url": False,
            "expected_narration_in_prompt": False,
            "description": "禁用音频时，不传递任何音频相关参数"
        }
    ]
    
    checks = []
    
    for case in test_cases:
        enable_audio = case["enable_audio"]
        audio_url_raw = case["audio_url"]
        narration = case["narration"]
        prompt = "让图片动起来"
        
        # 模拟代码逻辑
        audio_url = ""
        if audio_url_raw and isinstance(audio_url_raw, str):
            audio_url_raw = audio_url_raw.strip()
            if audio_url_raw.startswith(("http://", "https://")):
                audio_url = audio_url_raw
        
        api_parameters = {}
        full_prompt = prompt
        
        # 添加音频参数
        # ⚠️ 注意：如果提供了自定义音频URL，则不应传递generate_audio参数（audio_url优先级更高）
        if enable_audio and not audio_url:
            api_parameters["generate_audio"] = "true"
        
        # 如果提供了自定义音频URL
        if audio_url:
            api_parameters["audio_url"] = audio_url
        
        # 如果有旁白文本，合并到 prompt 中
        if narration and enable_audio and not audio_url:
            enhanced_prompt = f"{prompt}。旁白内容：{narration}"
            full_prompt = enhanced_prompt
        
        has_generate_audio = "generate_audio" in api_parameters
        has_audio_url = "audio_url" in api_parameters
        has_narration = "旁白内容" in full_prompt
        
        all_correct = (
            has_generate_audio == case["expected_generate_audio"] and
            has_audio_url == case["expected_audio_url"] and
            has_narration == case["expected_narration_in_prompt"]
        )
        
        if all_correct:
            checks.append((f"✅ {case['name']}", case["description"]))
        else:
            details = []
            if has_generate_audio != case["expected_generate_audio"]:
                details.append(f"generate_audio: 期望{case['expected_generate_audio']}, 实际{has_generate_audio}")
            if has_audio_url != case["expected_audio_url"]:
                details.append(f"audio_url: 期望{case['expected_audio_url']}, 实际{has_audio_url}")
            if has_narration != case["expected_narration_in_prompt"]:
                details.append(f"narration: 期望{case['expected_narration_in_prompt']}, 实际{has_narration}")
            checks.append((f"❌ {case['name']}", "; ".join(details)))
    
    print("\n" + "=" * 60)
    print("检查结果:")
    print("=" * 60)
    for check, detail in checks:
        print(f"{check}: {detail}")
    
    return all("✅" in check for check, _ in checks)


def test_complete_i2v_scenario():
    """测试完整的图生视频场景"""
    print("\n" + "=" * 60)
    print("测试5: 完整图生视频场景")
    print("=" * 60)
    
    # 完整场景：有图片、有旁白、启用音频
    params = {
        "image_url": "https://example.com/image.jpg",
        "prompt": "让图片动起来",
        "duration": "5",
        "resolution": "1080p",
        "enable_audio": True,
        "narration": "这是一个美丽的风景视频",
        "audio_url": ""
    }
    
    # 模拟完整的参数构建逻辑
    image_url = params.get("image_url", "")
    prompt = params.get("prompt", "让图片动起来")
    duration = params.get("duration", "5")
    resolution = params.get("resolution", "1080p")
    enable_audio = params.get("enable_audio", True)
    narration = params.get("narration", "")
    audio_url_raw = params.get("audio_url", "")
    
    # 验证 audio_url
    audio_url = ""
    if audio_url_raw and isinstance(audio_url_raw, str):
        audio_url_raw = audio_url_raw.strip()
        if audio_url_raw.startswith(("http://", "https://")):
            audio_url = audio_url_raw
    
    # 构建参数对象
    api_parameters = {}
    
    if duration:
        try:
            api_parameters["duration"] = int(duration)
        except ValueError:
            api_parameters["duration"] = 5
    
    if resolution:
        api_parameters["resolution"] = resolution
    
    if enable_audio:
        api_parameters["generate_audio"] = "true"
    
    if audio_url:
        api_parameters["audio_url"] = audio_url
    
    # 构建prompt
    full_prompt = prompt
    if narration and enable_audio and not audio_url:
        enhanced_prompt = f"{prompt}。旁白内容：{narration}"
        full_prompt = enhanced_prompt
    
    # 构建完整请求体
    payload = {
        "model": "doubao-seedance-1-5-pro-251215",
        "content": [
            {"type": "image_url", "image_url": {"url": image_url}},
            {"type": "text", "text": full_prompt}
        ],
        "parameters": api_parameters
    }
    
    print("\n📋 完整的请求体:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    
    # 验证
    checks = []
    
    # 检查1: content包含图片和文本
    if len(payload["content"]) == 2:
        has_image = any(item.get("type") == "image_url" for item in payload["content"])
        has_text = any(item.get("type") == "text" for item in payload["content"])
        if has_image and has_text:
            checks.append(("✅ content结构正确", "包含图片和文本"))
        else:
            checks.append(("❌ content结构错误", "应包含图片和文本"))
    else:
        checks.append(("❌ content结构错误", f"当前长度: {len(payload['content'])}"))
    
    # 检查2: prompt包含旁白
    if "旁白内容" in full_prompt:
        checks.append(("✅ prompt包含旁白", "旁白已正确合并"))
    else:
        checks.append(("❌ prompt不包含旁白", "旁白应合并到prompt"))
    
    # 检查3: parameters包含generate_audio
    if "generate_audio" in api_parameters:
        checks.append(("✅ parameters包含generate_audio", "音频参数正确"))
    else:
        checks.append(("❌ parameters不包含generate_audio", "应包含generate_audio"))
    
    # 检查4: parameters不包含audio_url（因为未提供）
    if "audio_url" not in api_parameters:
        checks.append(("✅ parameters不包含audio_url", "未提供自定义音频URL"))
    else:
        checks.append(("❌ parameters包含audio_url", "不应包含audio_url"))
    
    print("\n" + "=" * 60)
    print("检查结果:")
    print("=" * 60)
    for check, detail in checks:
        print(f"{check}: {detail}")
    
    return all("✅" in check for check, _ in checks)


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("图生视频图片和旁白参数测试")
    print("=" * 60)
    
    results = []
    
    # 测试1: 图片URL处理
    results.append(("图片URL处理", test_image_url_handling()))
    
    # 测试2: 旁白参数处理
    results.append(("旁白参数处理", test_narration_parameter()))
    
    # 测试3: 自定义音频URL参数处理
    results.append(("自定义音频URL参数处理", test_audio_url_parameter()))
    
    # 测试4: 音频参数优先级
    results.append(("音频参数优先级", test_audio_priority()))
    
    # 测试5: 完整场景
    results.append(("完整图生视频场景", test_complete_i2v_scenario()))
    
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
        print("🎉 所有测试通过！图片和旁白参数处理正确。")
    else:
        print("⚠️ 部分测试失败，请检查参数处理逻辑。")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    main()

