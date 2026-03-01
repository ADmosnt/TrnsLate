"""TrnsLate — Real-time screen text translation overlay.

A transparent overlay window that captures, detects, and translates
text in real-time, inspired by Android's Google Lens overlay.
"""

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

    def __init__(self, capture, detector, translator):
        super().__init__()
        self._capture = capture
        self._detector = detector
        self._translator = translator
        self._region = None
        self._running = False
        self._lock = threading.Lock()

    def set_region(self, rect):
        with self._lock:
            self._region = rect

    def process(self):
        """Run one capture -> OCR -> translate cycle."""
        with self._lock:
            region = self._region

        if region is None or region.width() <= 0 or region.height() <= 0:
            log.debug("process: no valid region (region=%s)", region)
            self.status_update.emit("Move overlay over text to translate")
            return

        log.info("process: region=(%d, %d, %d, %d)",
                 region.x(), region.y(), region.width(), region.height())

        try:
            # Capture
            self.status_update.emit("Capturing...")
            image = self._capture.capture_rect(region)
            if image is None:
                log.warning("process: capture returned None for region (%d, %d, %d, %d)",
                            region.x(), region.y(), region.width(), region.height())
                self.status_update.emit("Capture failed")
                return

            # OCR
            self.status_update.emit("Detecting text...")
            blocks = self._detector.detect(image)
            if not blocks:
                self.status_update.emit("No text detected")
                self.results_ready.emit([])
                return

            text_count = len(blocks)
            self.status_update.emit(f"Translating {text_count} block(s)...")

            # Translate
            translated = self._translator.translate_blocks(blocks)
            self.status_update.emit(
                f"Translated {len(translated)} block(s) | "
                f"Right-click for options | Ctrl+T pause"
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

        # Worker for background processing
        self._worker = TranslationWorker(
            self._capture, self._detector, self._translator
        )

        # Connect signals
        self._worker.results_ready.connect(self._overlay.set_translated_blocks)
        self._worker.status_update.connect(self._overlay.set_status)
        self._overlay.region_changed.connect(self._worker.set_region)
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

    def _run_cycle(self):
        """Run a translation cycle in a background thread."""
        if self._processing:
            return  # Skip if previous cycle still running

        region = self._overlay.get_capture_region()
        self._worker.set_region(region)

        self._processing = True
        self._thread = threading.Thread(
            target=self._process_and_finish, daemon=True
        )
        self._thread.start()

    def _process_and_finish(self):
        try:
            self._worker.process()
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
            self._run_cycle()

    def run(self):
        self._overlay.show()
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
