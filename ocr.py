"""OCR module using EasyOCR."""

import easyocr
import numpy as np


class TextDetector:
    """Detects text in images using EasyOCR."""

    def __init__(self, languages=None, use_gpu=False):
        """Initialize the OCR reader.

        Args:
            languages: List of language codes (e.g., ['en', 'es']).
                       Defaults to ['en'].
            use_gpu: Whether to use GPU acceleration (requires CUDA-compatible torch).
        """
        if languages is None:
            languages = ["en"]
        self._reader = easyocr.Reader(languages, gpu=use_gpu)

    def detect(self, image):
        """Detect text in a PIL Image.

        Args:
            image: PIL.Image.Image

        Returns:
            List of detected text blocks:
            [
                {
                    "bbox": (x, y, w, h),  # bounding box relative to image
                    "text": str,            # detected text
                    "confidence": float     # 0.0 to 1.0
                },
                ...
            ]
        """
        if image is None:
            return []

        img_array = np.array(image)
        results = self._reader.readtext(img_array)

        blocks = []
        for (bbox_points, text, confidence) in results:
            if confidence < 0.3:
                continue

            # bbox_points is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            xs = [p[0] for p in bbox_points]
            ys = [p[1] for p in bbox_points]
            x = int(min(xs))
            y = int(min(ys))
            w = int(max(xs) - x)
            h = int(max(ys) - y)

            blocks.append({
                "bbox": (x, y, w, h),
                "text": text.strip(),
                "confidence": confidence
            })

        return blocks
