"""
配置文件加载模块
从 config.yaml 读取配置并提供给主程序使用
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

# 设置 Windows 下的 UTF-8 输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载 YAML 配置文件
    
    Args:
        config_path: 配置文件路径，如果为 None 则使用默认路径
        
    Returns:
        配置字典
    """
    if config_path is None:
        # 默认配置文件路径（项目根目录下的 config.yaml）
        config_path = Path(__file__).parent / "config.yaml"
    else:
        config_path = Path(config_path)
    
    # 检查配置文件是否存在
    if not config_path.exists():
        print(f"⚠️  配置文件不存在: {config_path}")
        print("将使用默认配置或环境变量")
        return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        if config is None:
            return {}
            
        print(f"✅ 已加载配置文件: {config_path}")
        return config
        
    except yaml.YAMLError as e:
        print(f"❌ 配置文件格式错误: {e}")
        return {}
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
        return {}


def get_model_config(config: Dict[str, Any]) -> Dict[str, str]:
    """
    从配置中提取模型配置
    
    Args:
        config: 完整配置字典
        
    Returns:
        模型配置字典
    """
    model_config = config.get('model', {})
    
    return {
        'base_url': model_config.get('base_url', 'http://localhost:8000/v1'),
        'model_name': model_config.get('model_name', 'autoglm-phone-9b'),
        'api_key': model_config.get('api_key', 'EMPTY'),
    }


def get_model_params(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    从配置中提取模型参数
    
    Args:
        config: 完整配置字典
        
    Returns:
        模型参数字典
    """
    return config.get('model_params', {
        'max_tokens': 3000,
        'temperature': 0.1,
        'frequency_penalty': 0.2,
    })


def get_agent_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    从配置中提取 Agent 配置
    
    Args:
        config: 完整配置字典
        
    Returns:
        Agent 配置字典
    """
    agent_config = config.get('agent', {})
    
    return {
        'max_steps': agent_config.get('max_steps', 100),
        'device_id': agent_config.get('device_id'),
        'device_type': agent_config.get('device_type', 'adb'),
        'lang': agent_config.get('lang', 'cn'),
        'verbose': agent_config.get('verbose', True),
        'save_screenshots': agent_config.get('save_screenshots', False),
        'screenshot_dir': agent_config.get('screenshot_dir', './screenshots'),
    }


def get_ios_config(config: Dict[str, Any]) -> Dict[str, str]:
    """
    从配置中提取 iOS 配置
    
    Args:
        config: 完整配置字典
        
    Returns:
        iOS 配置字典
    """
    ios_config = config.get('ios', {})
    
    return {
        'wda_url': ios_config.get('wda_url', 'http://localhost:8100'),
    }


def merge_with_env_and_args(
    config: Dict[str, Any],
    args: Any
) -> Dict[str, Any]:
    """
    合并配置文件、环境变量和命令行参数
    优先级: 命令行参数 > 环境变量 > 配置文件 > 默认值
    
    Args:
        config: 从配置文件加载的配置
        args: 命令行参数对象
        
    Returns:
        合并后的配置
    """
    model_config = get_model_config(config)
    agent_config = get_agent_config(config)
    ios_config = get_ios_config(config)
    
    # 模型配置合并（优先使用命令行参数，其次环境变量，最后配置文件）
    base_url = (
        args.base_url if hasattr(args, 'base_url') and args.base_url != os.getenv("PHONE_AGENT_BASE_URL", "http://localhost:8000/v1")
        else os.getenv("PHONE_AGENT_BASE_URL", model_config['base_url'])
    )
    
    model_name = (
        args.model if hasattr(args, 'model') and args.model != os.getenv("PHONE_AGENT_MODEL", "autoglm-phone-9b")
        else os.getenv("PHONE_AGENT_MODEL", model_config['model_name'])
    )
    
    api_key = (
        args.apikey if hasattr(args, 'apikey') and args.apikey != os.getenv("PHONE_AGENT_API_KEY", "EMPTY")
        else os.getenv("PHONE_AGENT_API_KEY", model_config['api_key'])
    )
    
    # Agent 配置合并
    max_steps = (
        args.max_steps if hasattr(args, 'max_steps') and args.max_steps != int(os.getenv("PHONE_AGENT_MAX_STEPS", "100"))
        else int(os.getenv("PHONE_AGENT_MAX_STEPS", str(agent_config['max_steps'])))
    )
    
    device_id = (
        args.device_id if hasattr(args, 'device_id') and args.device_id
        else os.getenv("PHONE_AGENT_DEVICE_ID", agent_config['device_id'])
    )
    
    device_type = (
        args.device_type if hasattr(args, 'device_type') and args.device_type != os.getenv("PHONE_AGENT_DEVICE_TYPE", "adb")
        else os.getenv("PHONE_AGENT_DEVICE_TYPE", agent_config['device_type'])
    )
    
    lang = (
        args.lang if hasattr(args, 'lang') and args.lang != os.getenv("PHONE_AGENT_LANG", "cn")
        else os.getenv("PHONE_AGENT_LANG", agent_config['lang'])
    )
    
    verbose = not args.quiet if hasattr(args, 'quiet') else agent_config['verbose']
    
    # 截图配置（优先使用命令行参数，否则使用配置文件）
    save_screenshots = (
        args.save_screenshots if hasattr(args, 'save_screenshots') 
        else agent_config.get('save_screenshots', False)
    )
    
    screenshot_dir = (
        args.screenshot_dir if hasattr(args, 'screenshot_dir') and args.screenshot_dir
        else agent_config.get('screenshot_dir', './screenshots')
    )
    
    # iOS 配置
    wda_url = (
        args.wda_url if hasattr(args, 'wda_url') and args.wda_url != os.getenv("PHONE_AGENT_WDA_URL", "http://localhost:8100")
        else os.getenv("PHONE_AGENT_WDA_URL", ios_config['wda_url'])
    )
    
    return {
        'model': {
            'base_url': base_url,
            'model_name': model_name,
            'api_key': api_key,
        },
        'model_params': get_model_params(config),
        'agent': {
            'max_steps': max_steps,
            'device_id': device_id,
            'device_type': device_type,
            'lang': lang,
            'verbose': verbose,
            'save_screenshots': save_screenshots,
            'screenshot_dir': screenshot_dir,
        },
        'ios': {
            'wda_url': wda_url,
        }
    }


def print_config_summary(merged_config: Dict[str, Any]) -> None:
    """
    打印配置摘要
    
    Args:
        merged_config: 合并后的配置
    """
    print("\n" + "=" * 50)
    print("📋 当前配置摘要")
    print("=" * 50)
    
    model = merged_config['model']
    print(f"模型 API 地址: {model['base_url']}")
    print(f"模型名称: {model['model_name']}")
    print(f"API Key: {'已设置' if model['api_key'] and model['api_key'] != 'EMPTY' else '未设置'}")
    
    agent = merged_config['agent']
    print(f"设备类型: {agent['device_type'].upper()}")
    print(f"最大步数: {agent['max_steps']}")
    print(f"语言: {agent['lang'].upper()}")
    print(f"详细输出: {'开启' if agent['verbose'] else '关闭'}")
    print(f"保存截图: {'开启' if agent.get('save_screenshots', False) else '关闭'}")
    if agent.get('save_screenshots', False):
        print(f"截图目录: {agent.get('screenshot_dir', './screenshots')}")
    
    if agent['device_id']:
        print(f"指定设备: {agent['device_id']}")
    
    if agent['device_type'] == 'ios':
        ios = merged_config['ios']
        print(f"WDA URL: {ios['wda_url']}")
    
    print("=" * 50 + "\n")


if __name__ == "__main__":
    # 测试配置加载
    config = load_config()
    print("\n加载的配置:")
    print(yaml.dump(config, allow_unicode=True, default_flow_style=False))
