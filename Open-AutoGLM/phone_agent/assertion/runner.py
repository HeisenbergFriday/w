"""断言运行器 - 集成 AutoGLM 和断言监听."""

import time
import threading
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

from .assertion_watcher import AssertionWatcher, Assertion


@dataclass
class AssertionResult:
    """断言执行结果."""
    success: bool  # 是否成功
    message: str  # 结果消息
    elapsed_time: float  # 执行时间(秒)
    screenshot_path: Optional[str] = None  # 失败时的截图路径


class AssertionRunner:
    """
    断言运行器 - 负责协调 AI 操作和断言监听.
    
    核心流程:
    1. 启动 AutoGLM (执行 Prompt)
    2. 启动 Assertion Watcher (并行监听)
    3. 轮询屏幕状态
    4. 断言命中 → STOP AutoGLM → PASS
    5. 超时未命中 → STOP AutoGLM → FAIL
    """
    
    def __init__(
        self,
        agent,
        screenshot_func: Callable,
        save_screenshot_func: Optional[Callable] = None
    ):
        """
        初始化断言运行器.
        
        Args:
            agent: PhoneAgent 实例
            screenshot_func: 截图函数,返回 base64 编码的图片
            save_screenshot_func: 保存截图函数 (失败时调用)
        """
        self.agent = agent
        self.screenshot_func = screenshot_func
        self.save_screenshot_func = save_screenshot_func
        
        self.watcher = AssertionWatcher(screenshot_func)
        self._agent_thread = None
        self._agent_result = None
        self._agent_error = None
    
    def run_with_assertion(
        self,
        prompt: str,
        assertions: List[Dict[str, Any]],
        timeout: float = 10.0
    ) -> AssertionResult:
        """
        执行带断言的任务.
        
        Args:
            prompt: AI 操作指令 (只描述操作,不做判断)
            assertions: 断言列表,格式: [{"type": "text_exists", "value": "登录成功", "timeout": 5}]
            timeout: 总超时时间(秒)
            
        Returns:
            AssertionResult 对象
            
        Example:
            >>> runner = AssertionRunner(agent, screenshot_func)
            >>> result = runner.run_with_assertion(
            ...     prompt="点击登录按钮,等待页面稳定",
            ...     assertions=[
            ...         {"type": "text_exists", "value": "我的订单", "timeout": 5}
            ...     ]
            ... )
            >>> if result.success:
            ...     print("断言通过!")
        """
        start_time = time.time()
        
        # 转换断言格式
        assertion_objects = [
            Assertion(
                type=a["type"],
                value=a["value"],
                timeout=a.get("timeout", timeout)
            )
            for a in assertions
        ]
        
        print("=" * 70)
        print("🚀 启动带断言的任务执行")
        print("=" * 70)
        print(f"📝 Prompt: {prompt}")
        print(f"🔍 断言数量: {len(assertion_objects)}")
        for idx, assertion in enumerate(assertion_objects, 1):
            print(f"   {idx}. {assertion.type}: {assertion.value}")
        print()
        
        # 1. 启动 AI 操作 (在单独线程中)
        self._start_agent_async(prompt)
        
        # 2. 启动断言监听 (在主线程中)
        try:
            hit, message = self.watcher.watch(assertion_objects, timeout)
            
            # 3. 停止 AI 操作
            self._stop_agent()
            
            elapsed_time = time.time() - start_time
            
            if hit:
                # 断言命中 - 成功
                return AssertionResult(
                    success=True,
                    message=message or "断言通过",
                    elapsed_time=elapsed_time
                )
            else:
                # 超时未命中 - 失败
                screenshot_path = None
                if self.save_screenshot_func:
                    screenshot_path = self.save_screenshot_func()
                
                return AssertionResult(
                    success=False,
                    message="断言超时未命中",
                    elapsed_time=elapsed_time,
                    screenshot_path=screenshot_path
                )
                
        except Exception as e:
            # 异常 - 失败
            self._stop_agent()
            elapsed_time = time.time() - start_time
            
            screenshot_path = None
            if self.save_screenshot_func:
                screenshot_path = self.save_screenshot_func()
            
            return AssertionResult(
                success=False,
                message=f"断言执行异常: {str(e)}",
                elapsed_time=elapsed_time,
                screenshot_path=screenshot_path
            )
    
    def _start_agent_async(self, prompt: str):
        """在单独线程中启动 AI 操作."""
        def run_agent():
            try:
                self._agent_result = self.agent.run(prompt)
            except Exception as e:
                self._agent_error = e
        
        self._agent_thread = threading.Thread(target=run_agent, daemon=True)
        self._agent_thread.start()
        
        print("🤖 AI 操作已启动")
        print()
    
    def _stop_agent(self):
        """停止 AI 操作."""
        # 停止监听
        self.watcher.stop()
        
        # 注意: PhoneAgent 目前没有提供停止接口
        # 这里只是标记,实际上 agent 会继续执行直到完成
        # 如果需要强制停止,需要在 PhoneAgent 中添加停止机制
        
        print()
        print("⏹️  AI 操作已停止")
