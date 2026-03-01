"""Transparent overlay window using PyQt5."""

from PyQt5.QtWidgets import (
    QWidget, QApplication, QMenu, QAction, QLabel, QVBoxLayout,
    QHBoxLayout, QSystemTrayIcon
)
from PyQt5.QtCore import Qt, QTimer, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QCursor


class GripEdge:
    """Edge/corner resize grip zones."""
    NONE = 0
    LEFT = 1
    RIGHT = 2
    TOP = 4
    BOTTOM = 8
    TOP_LEFT = TOP | LEFT
    TOP_RIGHT = TOP | RIGHT
    BOTTOM_LEFT = BOTTOM | LEFT
    BOTTOM_RIGHT = BOTTOM | RIGHT


class OverlayWindow(QWidget):
    """Transparent, draggable, resizable overlay window."""

    region_changed = pyqtSignal(QRect)
    translate_toggled = pyqtSignal(bool)
    refresh_requested = pyqtSignal()

    GRIP_SIZE = 8
    MIN_WIDTH = 200
    MIN_HEIGHT = 100
    TITLE_BAR_HEIGHT = 28

    def __init__(self, width=500, height=350, opacity=0.25):
        super().__init__()
        self._drag_pos = None
        self._resize_edge = GripEdge.NONE
        self._resizing = False
        self._translating = True
        self._overlay_opacity = opacity
        self._translated_blocks = []  # List of (x, y, w, h, translated_text)
        self._status_text = "Starting..."

        self._init_window(width, height)
        self._init_ui()

    def _init_window(self, width, height):
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.resize(width, height)
        self.setMouseTracking(True)

    def _init_ui(self):
        self._status_label = QLabel(self._status_text)
        self._status_label.setStyleSheet(
            "color: white; background: rgba(0,0,0,160); "
            "padding: 2px 8px; border-radius: 4px; font-size: 11px;"
        )
        self._status_label.setFixedHeight(20)
        self._status_label.setMouseTracking(True)

    def set_status(self, text):
        self._status_text = text
        self._status_label.setText(text)
        self.update()

    def set_translated_blocks(self, blocks):
        """Set translated text blocks to render.

        Args:
            blocks: list of (x, y, w, h, translated_text) tuples
                    coordinates relative to the capture region
        """
        self._translated_blocks = blocks
        self.update()

    def get_capture_region(self):
        """Get the screen region to capture (excluding title bar)."""
        pos = self.mapToGlobal(QPoint(0, self.TITLE_BAR_HEIGHT))
        return QRect(
            pos.x() + self.GRIP_SIZE,
            pos.y(),
            self.width() - 2 * self.GRIP_SIZE,
            self.height() - self.TITLE_BAR_HEIGHT - self.GRIP_SIZE
        )

    # --- Painting ---

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Title bar background
        painter.setBrush(QColor(30, 30, 30, 200))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, w, self.TITLE_BAR_HEIGHT + 6, 6, 6)
        painter.drawRect(0, 10, w, self.TITLE_BAR_HEIGHT - 4)

        # Title text
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        title = "TrnsLate"
        if not self._translating:
            title += "  [PAUSED]"
        painter.drawText(10, 3, w - 20, self.TITLE_BAR_HEIGHT - 4,
                         Qt.AlignVCenter, title)

        # Capture area - semi-transparent overlay
        content_y = self.TITLE_BAR_HEIGHT
        content_h = h - content_y
        painter.setBrush(QColor(0, 0, 0, int(255 * self._overlay_opacity)))
        painter.setPen(QPen(QColor(100, 200, 255, 180), 2))
        painter.drawRect(0, content_y, w, content_h)

        # Render translated text blocks
        if self._translated_blocks and self._translating:
            painter.setFont(QFont("Segoe UI", 10))
            fm = painter.fontMetrics()
            for block in self._translated_blocks:
                bx, by, bw, bh, text = block
                # Original bbox centre in widget coordinates
                cx = bx + self.GRIP_SIZE + bw // 2
                cy = by + content_y + bh // 2

                # Measure text size (allow it to grow vertically)
                render_w = max(bw, 80)
                text_rect = fm.boundingRect(
                    QRect(0, 0, render_w, 9999),
                    Qt.AlignCenter | Qt.TextWordWrap, text
                )
                # Centre the measured rect over the original bbox
                text_rect.moveCenter(QPoint(cx, cy))

                # Background behind translated text
                padding = 4
                bg_rect = text_rect.adjusted(-padding, -padding, padding, padding)
                painter.setBrush(QColor(0, 0, 0, 210))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(bg_rect, 4, 4)

                # Translated text
                painter.setPen(QColor(100, 255, 100))
                painter.drawText(
                    text_rect,
                    Qt.AlignCenter | Qt.TextWordWrap,
                    text
                )

        # Status bar at bottom
        status_rect = QRect(4, h - 22, w - 8, 18)
        painter.setBrush(QColor(0, 0, 0, 160))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(status_rect, 3, 3)
        painter.setPen(QColor(200, 200, 200))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(status_rect.adjusted(6, 0, -6, 0),
                         Qt.AlignVCenter, self._status_text)

        # Border
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(100, 200, 255, 120), 1))
        painter.drawRoundedRect(0, 0, w - 1, h - 1, 6, 6)

        painter.end()

    # --- Mouse handling for drag & resize ---

    def _edge_at(self, pos):
        """Determine which edge/corner the position is near."""
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        g = self.GRIP_SIZE
        edge = GripEdge.NONE

        if x < g:
            edge |= GripEdge.LEFT
        elif x > w - g:
            edge |= GripEdge.RIGHT
        if y < g:
            edge |= GripEdge.TOP
        elif y > h - g:
            edge |= GripEdge.BOTTOM
        return edge

    def _update_cursor(self, edge):
        cursors = {
            GripEdge.LEFT: Qt.SizeHorCursor,
            GripEdge.RIGHT: Qt.SizeHorCursor,
            GripEdge.TOP: Qt.SizeVerCursor,
            GripEdge.BOTTOM: Qt.SizeVerCursor,
            GripEdge.TOP_LEFT: Qt.SizeFDiagCursor,
            GripEdge.BOTTOM_RIGHT: Qt.SizeFDiagCursor,
            GripEdge.TOP_RIGHT: Qt.SizeBDiagCursor,
            GripEdge.BOTTOM_LEFT: Qt.SizeBDiagCursor,
        }
        cursor = cursors.get(edge, Qt.ArrowCursor)
        self.setCursor(cursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            edge = self._edge_at(event.pos())
            if edge != GripEdge.NONE:
                self._resize_edge = edge
                self._resizing = True
                self._drag_pos = event.globalPos()
            elif event.pos().y() <= self.TITLE_BAR_HEIGHT:
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                self._resizing = False
            else:
                # Allow dragging from content area too
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                self._resizing = False
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.NoButton:
            self._update_cursor(self._edge_at(event.pos()))
            return

        if not (event.buttons() & Qt.LeftButton):
            return

        if self._resizing and self._drag_pos:
            delta = event.globalPos() - self._drag_pos
            self._drag_pos = event.globalPos()
            geo = self.geometry()

            if self._resize_edge & GripEdge.LEFT:
                geo.setLeft(geo.left() + delta.x())
            if self._resize_edge & GripEdge.RIGHT:
                geo.setRight(geo.right() + delta.x())
            if self._resize_edge & GripEdge.TOP:
                geo.setTop(geo.top() + delta.y())
            if self._resize_edge & GripEdge.BOTTOM:
                geo.setBottom(geo.bottom() + delta.y())

            if geo.width() >= self.MIN_WIDTH and geo.height() >= self.MIN_HEIGHT:
                self.setGeometry(geo)
                self.region_changed.emit(self.get_capture_region())

        elif self._drag_pos:
            self.move(event.globalPos() - self._drag_pos)
            self.region_changed.emit(self.get_capture_region())

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        self._resizing = False
        self._resize_edge = GripEdge.NONE
        self.region_changed.emit(self.get_capture_region())

    # --- Context menu ---

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #555;
                padding: 4px;
            }
            QMenu::item:selected {
                background-color: #4a9eff;
            }
        """)

        toggle_text = "Pause Translation" if self._translating else "Resume Translation"
        toggle_action = menu.addAction(toggle_text)
        toggle_action.triggered.connect(self._toggle_translate)

        refresh_action = menu.addAction("Refresh Now")
        refresh_action.triggered.connect(self.refresh_requested.emit)

        menu.addSeparator()

        quit_action = menu.addAction("Quit (Ctrl+Q)")
        quit_action.triggered.connect(QApplication.quit)

        menu.exec_(pos)

    def _toggle_translate(self):
        self._translating = not self._translating
        self.translate_toggled.emit(self._translating)
        self.update()

    # --- Keyboard shortcuts ---

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_Q:
                QApplication.quit()
            elif event.key() == Qt.Key_T:
                self._toggle_translate()
            elif event.key() == Qt.Key_R:
                self.refresh_requested.emit()
