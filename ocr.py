"""OCR module using EasyOCR with manga-optimized preprocessing."""

import cv2
import easyocr
import numpy as np


class TextDetector:
    """Detects text in images using EasyOCR."""

    def __init__(self, languages=None, use_gpu=False):
        if languages is None:
            languages = ["en"]
        self._reader = easyocr.Reader(languages, gpu=use_gpu)

    @staticmethod
    def _preprocess(img_array):
        """Clean image for OCR: grayscale, denoise screentones, binarize."""
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        # Median blur removes manga screentone dots without blurring letter edges
        blurred = cv2.medianBlur(gray, 3)

        # Otsu binarization: auto-threshold to pure black/white
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        return binary

    def detect(self, image):
        """Detect text in a PIL Image.

        Returns list of dicts with 'bbox', 'text', 'confidence' keys.
        Uses paragraph grouping to merge speech bubble lines.
        """
        if image is None:
            return []

        img_array = np.array(image)
        clean = self._preprocess(img_array)

        # paragraph=True groups nearby lines into coherent blocks (speech bubbles)
        # x_ths/y_ths control horizontal/vertical grouping tolerance
        results = self._reader.readtext(
            clean, paragraph=True, x_ths=1.0, y_ths=0.5
        )

        blocks = []
        for result in results:
            if len(result) == 3:
                bbox_points, text, confidence = result
                if confidence < 0.3:
                    continue
            else:
                bbox_points, text = result
                confidence = 1.0

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
