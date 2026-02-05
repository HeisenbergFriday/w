"""断言监听器 - 边执行边监听断言条件."""

import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .ocr_engine import OCREngine
from .image_diff import ImageDiffChecker


@dataclass
class Assertion:
    """断言配置."""
    type: str  # text_exists, text_not_exists, image_changed
    value: str  # 断言值
    timeout: float = 10.0  # 超时时间(秒)


class AssertionWatcher:
    """
    断言监听器 - 同步监听屏幕状态,检查断言是否命中.
    
    设计原则:
    1. AI 只负责操作,不负责判断
    2. 断言与 AI 同步执行(边操作边监听)
    3. 判断结果只来自规则(非 LLM)
    4. 命中断言立即停止 AI 操作
    """
    
    def __init__(
        self,
        screenshot_func,
        ocr_engine: Optional[OCREngine] = None,
        image_diff_checker: Optional[ImageDiffChecker] = None,
        poll_interval: float = 0.5,
        stable_frames: int = 3,
        stable_threshold: float = 0.05
    ):
        """
        初始化断言监听器.
        
        Args:
            screenshot_func: 截图函数,返回 base64 编码的图片
            ocr_engine: OCR 引擎
            image_diff_checker: 图片差异检测器
            poll_interval: 轮询间隔(秒)
            stable_frames: 画面稳定帧数
            stable_threshold: 画面稳定阈值
        """
        self.screenshot_func = screenshot_func
        self.ocr_engine = ocr_engine or OCREngine()
        self.image_diff_checker = image_diff_checker or ImageDiffChecker()
        self.poll_interval = poll_interval
        self.stable_frames = stable_frames
        self.stable_threshold = stable_threshold
        
        self._running = False
        self._last_screenshot = None
        self._recent_screenshots = []  # 用于画面稳定判定
    
    def check_assertion(self, assertion: Assertion, current_screenshot: str) -> bool:
        """
        检查单个断言是否命中.
        
        Args:
            assertion: 断言对象
            current_screenshot: 当前截图 (base64)
            
        Returns:
            是否命中断言
        """
        # 只在画面稳定时执行检查
        if not self._is_screen_stable():
            return False
        
        if assertion.type == "text_exists":
            return self.ocr_engine.contains_text(current_screenshot, assertion.value)
        
        elif assertion.type == "text_not_exists":
            return self.ocr_engine.not_contains_text(current_screenshot, assertion.value)
        
        elif assertion.type == "image_changed":
            if self._last_screenshot is None:
                return False
            return self.image_diff_checker.has_changed(
                self._last_screenshot,
                current_screenshot
            )
        
        return False
    
    def watch(self, assertions: List[Assertion], timeout: float = 10.0) -> tuple[bool, Optional[str]]:
        """
        监听断言,直到命中或超时.
        
        Args:
            assertions: 断言列表
            timeout: 总超时时间(秒)
            
        Returns:
            (是否命中, 命中的断言描述)
        """
        self._running = True
        start_time = time.time()
        
        print(f"🔍 开始监听断言 (超时: {timeout}秒)")
        print(f"   断言数量: {len(assertions)}")
        
        while self._running and (time.time() - start_time) < timeout:
            # 获取当前截图
            current_screenshot = self.screenshot_func()
            
            # 记录到最近截图列表(用于稳定性判定)
            self._recent_screenshots.append(current_screenshot)
            if len(self._recent_screenshots) > self.stable_frames:
                self._recent_screenshots.pop(0)
            
            # 检查每个断言
            for assertion in assertions:
                if self.check_assertion(assertion, current_screenshot):
                    self._running = False
                    msg = f"断言命中: {assertion.type} = {assertion.value}"
                    print(f"✅ {msg}")
                    return True, msg
            
            # 保存当前截图用于下次比较
            self._last_screenshot = current_screenshot
            
            # 等待下次轮询
            time.sleep(self.poll_interval)
        
        # 超时未命中
        self._running = False
        print(f"❌ 断言超时未命中 ({timeout}秒)")
        return False, None
    
    def stop(self):
        """停止监听."""
        self._running = False
    
    def _is_screen_stable(self) -> bool:
        """
        判断屏幕是否稳定.
        
        只有在画面稳定时才执行 OCR/图片断言,避免操作过程中误判.
        """
        if len(self._recent_screenshots) < self.stable_frames:
            return False
        
        return self.image_diff_checker.is_stable(
            self._recent_screenshots,
            self.stable_frames,
            self.stable_threshold
        )
