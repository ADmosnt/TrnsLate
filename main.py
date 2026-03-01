"""TrnsLate — Real-time screen text translation overlay.

A transparent overlay window that captures, detects, and translates
text in real-time, inspired by Android's Google Lens overlay.
"""

import hashlib
import logging
import os
import sys
import argparse
import threading

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, QRect, QObject, pyqtSignal

from overlay import OverlayWindow
from capture import ScreenCapture
from ocr import TextDetector
from translator import TextTranslator

log = logging.getLogger(__name__)


class TranslationWorker(QObject):
    """Runs OCR + translation in a background thread, emits results."""

    results_ready = pyqtSignal(list)  # list of (x, y, w, h, text)
    status_update = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, detector, translator):
        super().__init__()
        self._detector = detector
        self._translator = translator
        self._force_next = False
        self._last_img_hash = None
        self._lock = threading.Lock()

    def invalidate_cache(self):
        """Clear cached image hash so next cycle always runs."""
        with self._lock:
            self._last_img_hash = None

    def force_next(self):
        """Force the next cycle to run regardless of image changes."""
        with self._lock:
            self._force_next = True

    def process_image(self, image):
        """Run OCR + translate on a pre-captured image."""
        with self._lock:
            force = self._force_next
            self._force_next = False

        try:
            # Compare with previous capture — skip if unchanged
            thumb = image.resize((64, 64))
            img_hash = hashlib.md5(thumb.tobytes()).digest()
            if not force and img_hash == self._last_img_hash:
                log.debug("process: image unchanged, skipping")
                return
            self._last_img_hash = img_hash

            log.info("process: translating%s", " [forced]" if force else "")

            # OCR
            self.status_update.emit("Detecting text...")
            blocks = self._detector.detect(image)
            if not blocks:
                self.status_update.emit("No text detected — Ctrl+R to retry")
                self.results_ready.emit([])
                return

            text_count = len(blocks)
            self.status_update.emit(f"Translating {text_count} block(s)...")

            # Translate
            translated = self._translator.translate_blocks(blocks)
            self.status_update.emit(
                f"Translated {len(translated)} block(s) | "
                f"Ctrl+R refresh | Ctrl+T pause"
            )
            self.results_ready.emit(translated)

        except Exception as e:
            self.error_occurred.emit(str(e))
            self.status_update.emit(f"Error: {e}")


class TrnsLateApp:
    """Main application controller."""

    def __init__(self, args):
        self._app = QApplication(sys.argv)
        self._app.setApplicationName("TrnsLate")

        # Initialize components
        self._capture = ScreenCapture()
        self._detector = TextDetector(languages=[args.source], use_gpu=args.gpu)
        self._translator = TextTranslator(
            source=args.source, target=args.target
        )

        # Create overlay window
        self._overlay = OverlayWindow(
            width=args.width,
            height=args.height,
            opacity=args.opacity
        )

        # Worker for background processing (no longer owns capture)
        self._worker = TranslationWorker(self._detector, self._translator)

        # Connect signals
        self._worker.results_ready.connect(self._overlay.set_translated_blocks)
        self._worker.status_update.connect(self._overlay.set_status)
        self._overlay.region_changed.connect(
            lambda _rect: self._worker.invalidate_cache()
        )
        self._overlay.translate_toggled.connect(self._on_toggle)
        self._overlay.refresh_requested.connect(self._on_refresh)

        # Translation timer
        self._active = True
        self._timer = QTimer()
        self._timer.timeout.connect(self._run_cycle)
        self._interval = args.interval

        # Processing thread
        self._thread = None
        self._processing = False
        self._excluded_from_capture = False

    # --- Screen-capture exclusion ---

    def _try_exclude_from_capture(self):
        """Make overlay invisible to screenshot APIs (Windows 10 2004+)."""
        try:
            import ctypes
            hwnd = int(self._overlay.winId())
            WDA_EXCLUDEFROMCAPTURE = 0x00000011
            if ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE):
                self._excluded_from_capture = True
                log.info("Overlay excluded from screen capture via SetWindowDisplayAffinity")
            else:
                log.warning("SetWindowDisplayAffinity failed — will hide overlay during capture")
        except Exception as e:
            log.debug("SetWindowDisplayAffinity unavailable: %s — will hide overlay during capture", e)

    # --- Translation cycle ---

    def _run_cycle(self):
        """Run a translation cycle."""
        if self._processing:
            return

        region = self._overlay.get_capture_region()
        if region is None or region.width() <= 0 or region.height() <= 0:
            return

        self._processing = True

        if self._excluded_from_capture:
            # Overlay is invisible to mss — capture directly in background
            self._thread = threading.Thread(
                target=self._bg_capture_and_process, args=(region,), daemon=True
            )
            self._thread.start()
        else:
            # Must hide overlay so we don't screenshot our own text
            self._overlay.setWindowOpacity(0)
            QTimer.singleShot(60, lambda: self._capture_while_hidden(region))

    def _capture_while_hidden(self, region):
        """Capture screen while overlay is transparent, then restore."""
        image = self._capture.capture_rect(region)
        self._overlay.setWindowOpacity(1.0)

        if image is None:
            self._processing = False
            return

        self._thread = threading.Thread(
            target=self._bg_process_image, args=(image,), daemon=True
        )
        self._thread.start()

    def _bg_capture_and_process(self, region):
        """Background thread: capture + OCR + translate."""
        try:
            image = self._capture.capture_rect(region)
            if image is not None:
                self._worker.process_image(image)
        finally:
            self._processing = False

    def _bg_process_image(self, image):
        """Background thread: OCR + translate a pre-captured image."""
        try:
            self._worker.process_image(image)
        finally:
            self._processing = False

    def _on_toggle(self, active):
        self._active = active
        if active:
            self._timer.start(self._interval)
            self._overlay.set_status("Translation resumed")
        else:
            self._timer.stop()
            self._overlay.set_translated_blocks([])
            self._overlay.set_status("Translation paused (Ctrl+T to resume)")

    def _on_refresh(self):
        if self._active:
            self._worker.force_next()
            self._run_cycle()

    def run(self):
        self._overlay.show()
        self._try_exclude_from_capture()
        self._overlay.set_status(
            "Ready — move overlay over text | Ctrl+T toggle | Ctrl+Q quit"
        )

        # Start after a brief delay to let window settle
        QTimer.singleShot(1000, lambda: self._timer.start(self._interval))

        return self._app.exec_()


def _load_env():
    """Load .env file from the script's directory."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Don't override existing env vars or CLI args
                if key not in os.environ:
                    os.environ[key] = value


def _env(key, default):
    """Get a value from env, returning default if not set."""
    return os.environ.get(key, default)


def _env_bool(key, default=False):
    """Get a boolean value from env."""
    val = os.environ.get(key)
    if val is None:
        return default
    return val.lower() in ("true", "1", "yes")


def parse_args():
    _load_env()

    parser = argparse.ArgumentParser(
        description="TrnsLate — Real-time screen text translation overlay"
    )
    parser.add_argument(
        "--source", default=_env("SOURCE", "en"),
        help="Source language code (default: en)"
    )
    parser.add_argument(
        "--target", default=_env("TARGET", "es"),
        help="Target language code (default: es)"
    )
    parser.add_argument(
        "--opacity", type=float, default=float(_env("OPACITY", "0.25")),
        help="Overlay opacity 0.0-1.0 (default: 0.25)"
    )
    parser.add_argument(
        "--width", type=int, default=int(_env("WIDTH", "500")),
        help="Initial window width (default: 500)"
    )
    parser.add_argument(
        "--height", type=int, default=int(_env("HEIGHT", "350")),
        help="Initial window height (default: 350)"
    )
    parser.add_argument(
        "--interval", type=int, default=int(_env("INTERVAL", "3000")),
        help="Translation interval in ms (default: 3000)"
    )
    parser.add_argument(
        "--gpu", action="store_true",
        default=_env_bool("GPU"),
        help="Enable GPU acceleration for OCR (requires CUDA-compatible torch)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    level = logging.DEBUG if os.environ.get("DEBUG", "").lower() in ("1", "true") else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    log.info("TrnsLate starting — source=%s target=%s gpu=%s interval=%dms",
             args.source, args.target, args.gpu, args.interval)

    app = TrnsLateApp(args)
    sys.exit(app.run())
