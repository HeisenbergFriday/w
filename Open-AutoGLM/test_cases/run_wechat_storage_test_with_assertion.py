#!/usr/bin/env python3
"""
微柜v3小程序寄存流程测试用例 - 带断言版本

使用说明:
1. 确保已配置 config.yaml 文件
2. 确保手机已通过 ADB 连接
3. 确保手机相册中有二维码图片
4. 执行命令: python test_cases/run_wechat_storage_test_with_assertion.py

注意事项:
- 本测试会产生实际费用,请谨慎执行
- 建议使用测试账号进行测试
- 测试前请确认支付密码等敏感信息
- 使用断言机制自动验证每个步骤的执行结果
"""

import sys
import os
from pathlib import Path
import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
import json
from typing import Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from phone_agent import PhoneAgent
from phone_agent.agent import AgentConfig
from phone_agent.model import ModelConfig
from phone_agent.device_factory import get_device_factory
from phone_agent.assertion import AssertionRunner

# 导入配置加载模块
try:
    from load_config import load_config
    config = load_config()
    print("✅ 成功加载配置文件 config.yaml")
except Exception as e:
    print(f"⚠️  配置加载失败: {e}")
    print("将使用默认配置")
    config = {}


def send_dingtalk_notification(message_type: str, error_message: str = "", traceback_info: str = ""):
    """发送钉钉机器人通知."""
    # 钉钉机器人配置
    access_token = "7e9bbd283af35c7631c17282f7000f816c03e10b28c73081ff3f0a1d6aeb4cf8"
    secret = "SEC2c8f6e8a664ce948eadb123f41957ea285d5b7cb532cef2a9675765f35f1bf5e"
    
    try:
        print(f"[DEBUG] 开始发送钉钉通知, 类型: {message_type}")
        
        # 生成签名
        timestamp = str(round(time.time() * 1000))
        secret_enc = secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        
        print(f"[DEBUG] 签名生成成功, timestamp: {timestamp}")
        
        # 构造请求URL
        url = f"https://oapi.dingtalk.com/robot/send?access_token={access_token}&timestamp={timestamp}&sign={sign}"

        # 根据消息类型构造不同的消息内容
        if message_type == 'manual_operation':
            title = "微柜v3测试 - 人工操作提醒"
            content = f"## ⏸️ 微柜v3测试需要人工操作\n\n"
            content += f"**时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            content += f"**提示**: {error_message}\n\n"
            content += f"**测试用例**: 微柜v3小程序寄存流程测试\n\n"
            content += "**请手动完成操作，完成后在控制台确认继续执行！**"
        elif message_type == 'success':
            title = "微柜v3测试成功通知"
            content = f"## ✅ 微柜v3测试执行成功\n\n"
            content += f"**时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            content += f"**测试用例**: 微柜v3小程序寄存流程测试\n\n"
            content += "所有测试步骤已成功完成！"
        elif message_type == 'interrupt':
            title = "微柜v3测试中断通知"
            content = f"## ⚠️ 微柜v3测试被中断\n\n"
            content += f"**时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            content += f"**原因**: {error_message}\n\n"
            content += f"**测试用例**: 微柜v3小程序寄存流程测试"
        else:  # error
            title = "微柜v3测试失败通知"
            content = f"## ❌ 微柜v3测试执行失败\n\n"
            content += f"**时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            content += f"**错误信息**: {error_message}\n\n"
            
            if traceback_info:
                content += f"**详细堆栈**:\n```\n{traceback_info}\n```\n\n"
            
            content += f"**测试用例**: 微柜v3小程序寄存流程测试\n\n"
            content += "请及时检查测试环境和日志！"
        
        # 构造请求体
        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content
            }
        }
        
        print(f"[DEBUG] 请求体构造完成, 标题: {title}")
        
        # 发送POST请求
        headers = {'Content-Type': 'application/json'}
        print(f"[DEBUG] 发送POST请求到钉钉...")
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=10)
        
        print(f"[DEBUG] 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"[DEBUG] 响应内容: {result}")
            if result.get('errcode') == 0:
                print("✅ 钉钉通知发送成功")
            else:
                print(f"⚠️  钉钉通知发送失败: {result.get('errmsg')}")
        else:
            print(f"⚠️  钉钉通知发送失败: HTTP {response.status_code}")
            print(f"[DEBUG] 响应内容: {response.text}")
            
    except Exception as e:
        print(f"⚠️  钉钉通知发送异常: {e}")
        import traceback
        traceback.print_exc()


def create_screenshot_func(device_id=None):
    """创建截图函数."""
    def screenshot():
        device_factory = get_device_factory()
        screenshot_obj = device_factory.get_screenshot(device_id)
        return screenshot_obj.base64_data
    return screenshot


def create_save_screenshot_func(agent_config):
    """创建保存截图函数."""
    def save_screenshot():
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            screenshot_dir = Path(agent_config.screenshot_dir) / "assertion_failures"
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            
            filepath = screenshot_dir / f"failure_{timestamp}.png"
            
            device_factory = get_device_factory()
            screenshot_obj = device_factory.get_screenshot(agent_config.device_id)
            
            import base64
            image_data = base64.b64decode(screenshot_obj.base64_data)
            with open(filepath, "wb") as f:
                f.write(image_data)
            
            print(f"📸 失败截图已保存: {filepath}")
            return str(filepath)
        except Exception as e:
            print(f"⚠️  保存截图失败: {e}")
            return None
    
    return save_screenshot


def main():
    """执行微柜v3寄存流程测试 - 带断言版本."""
    
    # 测试步骤列表 - 带断言配置
    test_steps = [
        {
            "step": 1,
            "description": "打开微信",
            "prompt": "打开微信应用,等待页面完全加载"
        },
        {
            "step": 2,
            "description": "进入发现页面",
            "prompt": "点击底部导航栏的发现标签"
        },
        {
            "step": 3,
            "description": "进入小程序",
            "prompt": "点击小程序选项"
        },
        {
            "step": 4,
            "description": "打开微信开发者助手",
            "prompt": "找到微信开发者助手并进入这个小程序"
        },
        {
            "step": 5,
            "description": "进入我的业务",
            "prompt": "从我的业务中点击小程序选项"
        },
        {
            "step": 6,
            "description": "查找微柜v3",
            "prompt": "在小程序列表中找到微柜v3"
        },
        {
            "step": 7,
            "description": "进入体验版",
            "prompt": "从版本查看中进入体验版"
        },
        {
            "step": 8,
            "description": "点击存包",
            "prompt": "点击存包按钮"
        },
        {
            "step": 9,
            "description": "选择二维码",
            "prompt": "进入拍摄页面后，点击右下角相册，选择一张二维码图片"
        },
        {
            "step": 10,
            "description": "选择柜子",
            "prompt": "点击确认按钮,然后选择小柜",
            "assertions": [
                {"type": "text_exists", "value": "小柜", "timeout": 8},
                {"type": "text_exists", "value": "中柜", "timeout": 8}
            ]
        },
        {
            "step": 11,
            "description": "同意用户协议",
            "prompt": "点击同意用户协议",
            "assertions": [
                {"type": "text_exists", "value": "同意并继续", "timeout": 5}
            ]
        },
        {
            "step": 12,
            "description": "输入取物密码",
            "prompt": "点击输入取物密码,输入1111",
            "assertions": [
                {"type": "text_exists", "value": "确认下单", "timeout": 5}
            ]
        },
        {
            "step": 13,
            "description": "确认下单",
            "prompt": "点击确认下单按钮"
        },
        {
            "step": 14,
            "description": "放弃添加保险",
            "prompt": "点击放弃添加按钮",
            "assertions": [
                {"type": "text_exists","value": "放弃添加", "timeout": 5}
            ]
        },
        {
            "step": 15,
            "description": "进入支付页面",
            "prompt": "点击确认下单按钮,等待进入支付页面"
        },
        {
            "step": 16,
            "description": "人工支付操作",
            "task": "manual_payment",
            "is_manual": True,
            "manual_instruction": "请手动完成支付操作：\n1. 点击支付按钮\n2. 输入支付密码\n3. 等待支付完成\n4. 确认支付成功后按回车键继续"
        },
        {
            "step": 17,
            "description": "等待柜门开启",
            "prompt": "等待柜门开启"
        },
        {
            "step": 18,
            "description": "完成寄存",
            "prompt": "点击寄存完成按钮",
            "assertions": [
                {"type": "text_exists", "value": "寄存完成", "timeout": 5}
            ],
            "is_critical": True
        }
    ]
    
    print("=" * 70)
    print("微柜v3小程序寄存流程测试 - 带断言版本")
    print("=" * 70)
    print()
    print("📋 测试用例详情:")
    print("  - 测试名称: 微柜v3小程序寄存流程测试")
    print("  - 测试应用: 微信小程序 - 微柜v3")
    print(f"  - 测试步骤: {len(test_steps)}步")
    print("  - 涉及功能: 寄存、人工支付、断言验证")
    print()
    print("⚠️  重要提示:")
    print("  - 本测试需要人工完成支付操作")
    print("  - 请确保相册中有二维码图片")
    print("  - 请确认取物密码: 1111")
    print("  - 支付步骤将暂停等待人工确认")
    print("  - 每个步骤都有断言验证,自动判断执行结果")
    print()
    
    # 询问用户确认
    confirm = input("是否继续执行测试? (y/n): ").strip().lower()
    if confirm != 'y':
        print("测试已取消")
        return
    
    print()
    print("=" * 70)
    print("开始执行测试...")
    print("=" * 70)
    print()
    
    try:
        # 从配置中获取模型配置
        model_config_dict = config.get('model', {})
        model_config = ModelConfig(
            base_url=model_config_dict.get('base_url', 'http://localhost:8000/v1'),
            model_name=model_config_dict.get('model_name', 'autoglm-phone-9b'),
            api_key=model_config_dict.get('api_key', 'EMPTY'),
            lang=config.get('agent', {}).get('lang', 'cn')
        )
        
        # 从配置中获取 agent 配置
        agent_config_dict = config.get('agent', {})
        agent_config = AgentConfig(
            max_steps=agent_config_dict.get('max_steps', 100),
            device_id=agent_config_dict.get('device_id'),
            verbose=agent_config_dict.get('verbose', True),
            lang=agent_config_dict.get('lang', 'cn'),
            save_screenshots=agent_config_dict.get('save_screenshots', True),
            screenshot_dir=agent_config_dict.get('screenshot_dir', './screenshots')
        )
        
        print(f"🤖 模型配置:")
        print(f"  - Base URL: {model_config.base_url}")
        print(f"  - Model: {model_config.model_name}")
        print(f"  - Language: {model_config.lang}")
        print()
        print(f"📱 Agent 配置:")
        print(f"  - Max Steps: {agent_config.max_steps}")
        print(f"  - Device ID: {agent_config.device_id or '自动检测'}")
        print(f"  - Verbose: {agent_config.verbose}")
        print(f"  - Save Screenshots: {agent_config.save_screenshots}")
        print(f"  - Screenshot Dir: {agent_config.screenshot_dir}")
        print()
        
        # 创建 agent 实例
        agent = PhoneAgent(
            model_config=model_config,
            agent_config=agent_config
        )
        
        # 创建截图函数
        screenshot_func = create_screenshot_func(agent_config.device_id)
        save_screenshot_func = create_save_screenshot_func(agent_config)
        
        # 创建断言运行器
        runner = AssertionRunner(
            agent=agent,
            screenshot_func=screenshot_func,
            save_screenshot_func=save_screenshot_func
        )
        
        print("🚀 开始执行测试任务...")
        print()
        
        # 执行分步测试
        for idx, test_step in enumerate(test_steps, 1):
            step_num = test_step['step']
            description = test_step['description']
            is_critical = test_step.get('is_critical', False)
            is_manual = test_step.get('is_manual', False)
            
            print(f"{'='*70}")
            print(f"步骤 {step_num}/{len(test_steps)}: {description}")
            print(f"{'='*70}")
            
            # 如果是人工操作步骤
            if is_manual:
                manual_instruction = test_step.get('manual_instruction', '')
                print(f"⏸️  需要人工操作")
                print()
                print(manual_instruction)
                print()
                
                # 发送钉钉通知
                print("📢 正在发送钉钉通知...")
                try:
                    send_dingtalk_notification(
                        'manual_operation',
                        f"步骤 {step_num}: {description}\n{manual_instruction}"
                    )
                except Exception as e:
                    print(f"⚠️  钉钉通知发送失败: {e}")
                    import traceback
                    traceback.print_exc()
                
                # 等待用户确认
                input("按回车键继续...")
                print("✅ 人工操作已确认完成")
                print()
                
                # 步骤间延迟
                time.sleep(2)
                continue
            
            # 检查是否有断言配置
            has_assertions = 'assertions' in test_step and test_step['assertions']
            
            try:
                if has_assertions:
                    # 执行带断言的任务
                    prompt = test_step['prompt']
                    assertions = test_step['assertions']
                    
                    print(f"📝 任务: {prompt}")
                    print(f"🔍 断言数量: {len(assertions)}")
                    
                    # 使用断言运行器执行
                    result = runner.run_with_assertion(
                        prompt=prompt,
                        assertions=assertions,
                        timeout=15
                    )
                    
                    if result.success:
                        print(f"✅ 步骤 {step_num} 断言通过: {result.message}")
                        print(f"⏱️  耗时: {result.elapsed_time:.2f}秒")
                    else:
                        print(f"❌ 步骤 {step_num} 断言失败: {result.message}")
                        print(f"⏱️  耗时: {result.elapsed_time:.2f}秒")
                        if result.screenshot_path:
                            print(f"📸 失败截图: {result.screenshot_path}")
                        
                        # 如果是关键步骤,发送通知并退出
                        if is_critical:
                            import traceback
                            tb_str = traceback.format_exc()
                            send_dingtalk_notification(
                                'error',
                                f"关键步骤 {step_num} 断言失败: {description}\n{result.message}",
                                tb_str
                            )
                            raise AssertionError(f"关键步骤 {step_num} 断言失败")
                else:
                    # 无断言的步骤,直接执行
                    task = test_step.get('prompt') or test_step.get('task', '')
                    print(f"📝 任务: {task}")
                    print(f"ℹ️  无断言检查,直接执行")
                    
                    # 直接执行
                    agent.run(task)
                    print("✅ 任务执行完成")
                
                print()
                
                # 步骤间延迟
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ 步骤 {step_num} 执行失败: {e}")
                
                # 如果是关键步骤,发送通知并退出
                if is_critical:
                    import traceback
                    tb_str = traceback.format_exc()
                    send_dingtalk_notification(
                        'error',
                        f"关键步骤 {step_num} 执行失败: {description}",
                        tb_str
                    )
                    raise
                else:
                    print("⚠️  非关键步骤,继续执行...")
                    print()
        
        print()
        print("=" * 70)
        print("测试执行完成")
        print("=" * 70)
        print("✅ 所有测试步骤执行成功")
        print()
        
        if agent_config.save_screenshots:
            print(f"📸 截图已保存到: {agent_config.screenshot_dir}")
        
        # 发送成功通知
        send_dingtalk_notification('success', "所有测试步骤执行成功")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试执行失败: {e}")
        import traceback
        tb_str = traceback.format_exc()
        traceback.print_exc()
        # 发送钉钉通知
        send_dingtalk_notification('error', str(e), tb_str)
        sys.exit(1)


if __name__ == "__main__":
    main()
