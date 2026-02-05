"""图片差异检测 - 用于判断屏幕是否发生变化."""

import base64
import numpy as np
from typing import Optional
from io import BytesIO


class ImageDiffChecker:
    """图片差异检测器,用于判断两张图片是否发生明显变化."""
    
    def __init__(self, threshold: float = 0.15):
        """
        初始化差异检测器.
        
        Args:
            threshold: 差异阈值 (0.0-1.0),超过该值认为发生明显变化
        """
        self.threshold = threshold
    
    def calculate_diff(self, image1_base64: str, image2_base64: str) -> float:
        """
        计算两张图片的差异度.
        
        Args:
            image1_base64: 第一张图片的 base64 数据
            image2_base64: 第二张图片的 base64 数据
            
        Returns:
            差异度 (0.0-1.0)
        """
        try:
            # 解码图片
            img1_data = base64.b64decode(image1_base64)
            img2_data = base64.b64decode(image2_base64)
            
            # 使用 PIL 加载图片
            from PIL import Image
            img1 = Image.open(BytesIO(img1_data))
            img2 = Image.open(BytesIO(img2_data))
            
            # 转换为相同大小
            if img1.size != img2.size:
                img2 = img2.resize(img1.size)
            
            # 转换为 numpy 数组
            arr1 = np.array(img1)
            arr2 = np.array(img2)
            
            # 计算像素差异
            diff = np.abs(arr1.astype(float) - arr2.astype(float))
            diff_ratio = np.mean(diff) / 255.0
            
            return diff_ratio
            
        except Exception as e:
            print(f"⚠️  计算图片差异失败: {e}")
            return 0.0
    
    def has_changed(self, image1_base64: str, image2_base64: str) -> bool:
        """
        判断两张图片是否发生明显变化.
        
        Args:
            image1_base64: 第一张图片的 base64 数据
            image2_base64: 第二张图片的 base64 数据
            
        Returns:
            是否发生明显变化
        """
        diff = self.calculate_diff(image1_base64, image2_base64)
        return diff > self.threshold
    
    def is_stable(
        self,
        recent_images: list,
        stable_frames: int = 3,
        stable_threshold: float = 0.05
    ) -> bool:
        """
        判断画面是否稳定(连续多帧变化小于阈值).
        
        Args:
            recent_images: 最近的图片列表 (base64 格式)
            stable_frames: 需要稳定的帧数
            stable_threshold: 稳定阈值
            
        Returns:
            画面是否稳定
        """
        if len(recent_images) < stable_frames:
            return False
        
        # 检查最近 N 帧是否都很相似
        for i in range(len(recent_images) - stable_frames + 1, len(recent_images)):
            diff = self.calculate_diff(recent_images[i-1], recent_images[i])
            if diff > stable_threshold:
                return False
        
        return True
