"""Screen capture module using mss."""

import mss
import numpy as np
from PIL import Image


class ScreenCapture:
    """Captures a region of the screen."""

    def __init__(self):
        self._sct = mss.mss()

    def capture_region(self, x, y, width, height):
        """Capture a screen region and return as PIL Image.

        Args:
            x: Left coordinate
            y: Top coordinate
            width: Region width
            height: Region height

        Returns:
            PIL.Image.Image or None if capture fails
        """
        if width <= 0 or height <= 0:
            return None

        monitor = {
            "left": x,
            "top": y,
            "width": width,
            "height": height
        }

        try:
            screenshot = self._sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            return img
        except Exception:
            return None

    def capture_rect(self, qrect):
        """Capture from a QRect."""
        return self.capture_region(
            qrect.x(), qrect.y(),
            qrect.width(), qrect.height()
        )

    def close(self):
        self._sct.close()
