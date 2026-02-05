#!/usr/bin/env python3
"""
美团团购券购买与券码复制自动化任务脚本

使用说明:
1. 确保已配置 config.yaml 文件
2. 确保手机已通过 ADB 连接
3. 确保微信已登录，并且小程序和支付环境已准备好
4. 执行命令: python test_cases/run_meituan_task.py

注意事项:
- 本测试会产生实际费用,请谨慎执行
- 建议使用测试账号进行测试
- 测试前请确认支付密码等敏感信息
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

# 导入配置加载模块
try:
    from load_config import load_config
    config = load_config()
    print("✅ 成功加载配置文件 config.yaml")
except Exception as e:
    print(f"⚠️  配置加载失败: {e}")
    print("将使用默认配置")
    config = {}

def send_dingtalk_notification(message_type: str, error_message: str = "", traceback_info: str = "", screenshot_path: Optional[str] = None):
    """
    发送钉钉机器人通知
    
    Args:
        message_type: 消息类型 ('error', 'manual_operation', 'success', 'interrupt')
        error_message: 错误消息或其他消息内容
        traceback_info: 堆栈跟踪信息
        screenshot_path: 可选，要上传的截图路径
    """
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
            title = "美团任务 - 人工操作提醒"
            content = f"## ⏸️ 美团团购券任务需要人工操作\n\n"
            content += f"**时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            content += f"**提示**: {error_message}\n\n"
            content += f"**任务描述**: 购买美团团购券并复制券码\n\n"
            content += "**请手动完成支付操作，完成后在控制台确认继续执行！**"
        elif message_type == 'success':
            title = "美团任务成功通知"
            content = f"## ✅ 美团团购券任务执行成功\n\n"
            content += f"**时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            content += f"**任务描述**: 购买美团团购券并复制券码\n\n"
            content += "整个任务流程已成功完成！"
        elif message_type == 'interrupt':
            title = "美团任务中断通知"
            content = f"## ⚠️ 美团团购券任务被中断\n\n"
            content += f"**时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            content += f"**原因**: {error_message}\n\n"
            content += f"**任务描述**: 购买美团团购券并复制券码"
        else:  # error
            title = "美团任务失败通知"
            content = f"## ❌ 美团团购券任务执行失败\n\n"
            content += f"**时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            content += f"**错误信息**: {error_message}\n\n"
            
            if traceback_info:
                content += f"**详细堆栈**:\n```\n{traceback_info}\n```\n\n"
            
            content += f"**任务描述**: 购买美团团购券并复制券码\n\n"
            content += "请及时检查测试环境和日志！"
        
        # 如果有截图，则添加到消息内容中
        if screenshot_path and os.path.exists(screenshot_path):
            # 尝试上传图片到钉钉
            upload_url = f"https://oapi.dingtalk.com/media/upload?access_token={access_token}&type=image"
            try:
                with open(screenshot_path, 'rb') as f:
                    files = {'media': f}
                    upload_response = requests.post(upload_url, files=files, timeout=30)
                    if upload_response.status_code == 200:
                        upload_result = upload_response.json()
                        if upload_result.get('errcode') == 0:
                            media_id = upload_result['media_id']
                            content += f"\n![失败截图](https://oapi.dingtalk.com/media/download?media_id={media_id})"
                        else:
                            print(f"⚠️  上传图片失败: {upload_result.get('errmsg')}")
                    else:
                        print(f"⚠️  上传图片请求失败: HTTP {upload_response.status_code}")
            except Exception as file_err:
                print(f"⚠️  读取或上传图片文件失败: {file_err}")

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


def main():
    """执行美团团购券购买与券码复制任务"""
    
    # 定义单一任务描述
    # 注意：这里需要将“某某团购券”替换为您实际想要购买的券的名称
    task_description = "打开美团小程序，找到'全聚德北京烤鸭双人套餐'团购券，点击购买，完成支付，支付成功后复制券码。"
    
    print("=" * 70)
    print("美团团购券购买与券码复制自动化任务")
    print("=" * 70)
    print()
    print("📋 任务详情:")
    print(f"  - 任务描述: {task_description}")
    print("  - 涉及应用: 微信 -> 美团小程序")
    print("  - 涉及功能: 商品查找、下单、支付、券码复制")
    print()
    print("⚠️  重要提示:")
    print("  - 本任务需要人工完成支付操作")
    print("  - 请确保微信已登录，且支付环境（如密码）已准备好")
    print("  - 请将任务描述中的商品名称修改为您需要的真实商品名")
    print("  - 支付步骤将暂停等待人工确认")
    print()
    
    # 询问用户确认
    confirm = input("是否继续执行任务? (y/n): ").strip().lower()
    if confirm != 'y':
        print("任务已取消")
        return
    
    print()
    print("=" * 70)
    print("开始执行任务...")
    print("=" * 70)
    print()
    
    # --- 新增：创建统一的截图保存目录 ---
    # 使用当前时间戳作为文件夹名，避免重复
    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
    unified_screenshot_dir = project_root / "meituan_task_screenshots" / f"run_{timestamp_str}"
    unified_screenshot_dir.mkdir(parents=True, exist_ok=True)
    print(f"📸 截图将保存到: {unified_screenshot_dir}")
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
            save_screenshots=True,  # 启用截图保存
            screenshot_dir=str(unified_screenshot_dir) # 使用新的统一目录
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
        
        print("🚀 开始执行任务...")
        print(f"📝 任务指令: {task_description}")
        print()

        # --- 核心变化：执行单一任务 ---
        # 让 AI Agent 自主完成整个复杂流程
        agent.run(task_description)

        # 任务执行完毕，可能需要人工确认支付
        print("\n--- 任务执行阶段完成 ---")
        print("如果任务中包含支付环节，请手动完成支付。")
        manual_confirm = input("请确认已完成所有操作（如支付）并复制了券码，完成后按回车键继续以发送通知...")

        print("\n✅ 任务执行完成")
        print()
        
        print(f"📸 所有截图已保存到: {unified_screenshot_dir}")
        
        # 发送成功通知
        send_dingtalk_notification('success', "美团团购券购买与券码复制任务执行成功")
        
    except KeyboardInterrupt:
        error_msg = "任务被用户中断"
        print(f"\n\n⚠️  {error_msg}")
        # 可以选择发送中断通知
        send_dingtalk_notification('interrupt', error_msg)
        sys.exit(1)
    except Exception as e:
        # --- 修改：捕获特定错误并转换为中文提示 ---
        original_error_str = str(e)
        if "No output from dumpsys window windows" in original_error_str:
            error_msg = "设备连接失败或ADB服务异常。请检查手机是否通过USB正确连接，并且开启了USB调试模式。"
        else:
            error_msg = f"任务执行失败: {original_error_str}"

        print(f"\n\n❌ {error_msg}")
        import traceback
        tb_str = traceback.format_exc()
        traceback.print_exc()
        
        # 查找最新的截图文件作为错误截图
        latest_screenshot = None
        if unified_screenshot_dir.exists():
            screenshot_files = sorted(unified_screenshot_dir.glob("*.png"), key=os.path.getmtime, reverse=True)
            if screenshot_files:
                latest_screenshot = str(screenshot_files[0])
                print(f"📁 将使用最新截图 {latest_screenshot} 作为错误报告附件")

        # 发送钉钉通知，附带最新的截图和中文错误信息
        send_dingtalk_notification('error', error_msg, tb_str, latest_screenshot)
        sys.exit(1)


if __name__ == "__main__":
    main()