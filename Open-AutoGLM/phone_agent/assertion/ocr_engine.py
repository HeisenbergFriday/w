"""OCR 引擎 - 封装屏幕文字识别功能."""

import base64
import subprocess
import json
from typing import List
from pathlib import Path


class OCREngine:
    """OCR 引擎,用于识别屏幕中的文字内容."""
    
    def __init__(self, device_id: str = None):
        """
        初始化 OCR 引擎.
        
        Args:
            device_id: 设备 ID
        """
        self.device_id = device_id
    
    def extract_text(self, image_base64: str) -> List[str]:
        """
        从 base64 编码的图片中提取文字.
        
        Args:
            image_base64: base64 编码的图片数据
            
        Returns:
            提取的文字列表
        """
        # TODO: 这里需要根据实际的 OCR 实现来完成
        # 目前返回空列表作为占位
        # 可以使用 PaddleOCR、Tesseract 或其他 OCR 工具
        
        # 示例实现 (需要安装 paddleocr):
        # from paddleocr import PaddleOCR
        # ocr = PaddleOCR(use_angle_cls=True, lang='ch')
        # image_data = base64.b64decode(image_base64)
        # result = ocr.ocr(image_data, cls=True)
        # texts = [line[1][0] for line in result[0]]
        # return texts
        
        return []
    
    def contains_text(self, image_base64: str, target_text: str) -> bool:
        """
        检查图片中是否包含指定文字.
        
        Args:
            image_base64: base64 编码的图片数据
            target_text: 目标文字
            
        Returns:
            是否包含目标文字
        """
        texts = self.extract_text(image_base64)
        return any(target_text in text for text in texts)
    
    def not_contains_text(self, image_base64: str, target_text: str) -> bool:
        """
        检查图片中是否不包含指定文字.
        
        Args:
            image_base64: base64 编码的图片数据
            target_text: 目标文字
            
        Returns:
            是否不包含目标文字
        """
        return not self.contains_text(image_base64, target_text)
