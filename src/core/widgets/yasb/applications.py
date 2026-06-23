import logging
import os
import subprocess
import time

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QCursor, QPixmap, QPainter, QTransform
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from core.utils.tooltip import set_tooltip
from core.utils.utilities import add_shadow
from core.utils.widgets.animation_manager import AnimationManager
from core.utils.win32.system_function import function_map
from core.validation.widgets.yasb.applications import ApplicationsWidgetConfig
from core.widgets.base import BaseWidget


class ApplicationsWidget(BaseWidget):
    validation_schema = ApplicationsWidgetConfig

    def __init__(self, config: ApplicationsWidgetConfig):
        super().__init__(class_name=f"apps-widget {config.class_name}")
        self.config = config

        # Construct container
        self._widget_container_layout = QHBoxLayout()
        self._widget_container_layout.setSpacing(0)
        self._widget_container_layout.setContentsMargins(0, 0, 0, 0)
        # Initialize container
        self._widget_container = QFrame()
        self._widget_container.setLayout(self._widget_container_layout)
        self._widget_container.setProperty("class", "widget-container")
        add_shadow(self._widget_container, self.config.container_shadow.model_dump())

        # Add the container to the main widget layout
        self.widget_layout.addWidget(self._widget_container)
        self._update_label()

    def _update_label(self):
        for app_data in self.config.app_list:
            if app_data.icon and app_data.launch:
                # Create a container widget for each label
                label_container = QWidget()
                label_layout = QHBoxLayout(label_container)
                label_layout.setContentsMargins(0, 0, 0, 0)
                label_layout.setSpacing(0)

                # Create the label
                label = ClickableLabel(self)
                label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                label.setProperty("class", "label")

                app_name = app_data.name
                if app_name and self.config.tooltip:
                    set_tooltip(label, app_name, 0)

                # Set icon
                icon = app_data.icon
                if os.path.isfile(icon):
                    pixmap = QPixmap(icon).scaled(
                        self.config.image_icon_size,
                        self.config.image_icon_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    label.setPixmap(pixmap)
                else:
                    label.setText(icon)

                # Center icon/text in label (fixes vertical alignment for icon font glyphs)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)

                label.data = app_data.launch
                label.container = label_container  # Store reference to container

                # Add shadow to the label
                add_shadow(label, self.config.label_shadow.model_dump())

                # Add label to its container
                label_layout.addWidget(label)

                # Add container to main layout
                self._widget_container_layout.addWidget(label_container)

    def execute_code(self, data: str):
        try:
            if data in function_map:
                function_map[data]()
            else:
                try:
                    cmd_args: str | list[str] = data
                    if not any(param in data for param in ["-new-tab", "-new-window", "-private-window"]):
                        cmd_args = data.split()
                    subprocess.Popen(cmd_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                except Exception as e:
                    logging.error(f"Error starting app: {str(e)}")
        except Exception as e:
            logging.error(f'Exception occurred: {str(e)} "{data}"')


class ClickableLabel(QLabel):
    """QLabel with rotation + blue background animation for wiggle effect."""

    def __init__(self, parent: ApplicationsWidget | None = None):
        super().__init__(parent)
        self.parent_widget = parent
        self.data = None
        self.container = None
        self._rotation = 0.0
        self._wiggle_anim = None
        self._bg_anim = None
        self._bg_progress = 0.0
        self._text_content = ""
        self._last_click_time = 0.0  # Click cooldown

    # --- Rotation property (wiggle) ---
    def getRotation(self):
        return self._rotation

    def setRotation(self, angle):
        self._rotation = angle
        self.update()

    rotation = pyqtProperty(float, getRotation, setRotation)

    # --- Background progress property (blue transition) ---
    def getBgProgress(self):
        return self._bg_progress

    def setBgProgress(self, val):
        self._bg_progress = val
        container = getattr(self.parent_widget, '_widget_container', None)
        if not container:
            return
        # Interpolate: rgba(30,34,40,0.7) -> #3B82F6 (rgb 59,130,246)
        r = int(30 + (59 - 30) * val)
        g = int(34 + (130 - 34) * val)
        b = int(40 + (246 - 40) * val)
        a = 0.7 + 0.3 * val
        color = f"rgba({r},{g},{b},{a:.2f})"
        container.setStyleSheet(
            f"background-color: {color}; border: 1px solid {color}; "
            f"border-radius: 12px; margin: 4px 0;"
        )

    bgProgress = pyqtProperty(float, getBgProgress, setBgProgress)

    def setText(self, text):
        """Override to cache text content."""
        self._text_content = text
        super().setText(text)

    def _is_icon_font(self):
        """Check if this label uses an icon font glyph (non-ASCII)."""
        text = self._text_content or self.text()
        return text and len(text) == 1 and ord(text[0]) > 255

    def paintEvent(self, event):
        """Custom paint with rotation transform around center."""
        if abs(self._rotation) < 0.1:
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.save()

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        painter.translate(cx, cy)
        painter.rotate(self._rotation)
        painter.translate(-cx, -cy)

        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.setFont(self.font())
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._text_content or self.text())

        painter.restore()
        painter.end()

    def _startWiggle(self):
        """Start rotational wiggle + blue bg transition (icon font only)."""
        if self._wiggle_anim:
            self._wiggle_anim.stop()

        self._wiggle_anim = QPropertyAnimation(self, b"rotation")
        self._wiggle_anim.setDuration(400)
        self._wiggle_anim.setKeyValueAt(0.0, 0.0)
        self._wiggle_anim.setKeyValueAt(0.15, -8.0)
        self._wiggle_anim.setKeyValueAt(0.35, 6.0)
        self._wiggle_anim.setKeyValueAt(0.55, -4.0)
        self._wiggle_anim.setKeyValueAt(0.75, 2.0)
        self._wiggle_anim.setKeyValueAt(1.0, 0.0)
        self._wiggle_anim.start()

        # Blue background transition for icon font glyphs (e.g. Windows logo)
        if self._is_icon_font():
            if self._bg_anim:
                self._bg_anim.stop()
            self._bg_anim = QPropertyAnimation(self, b"bgProgress")
            self._bg_anim.setDuration(400)
            self._bg_anim.setStartValue(0.0)
            self._bg_anim.setEndValue(1.0)
            self._bg_anim.start()

    def enterEvent(self, event):
        """Trigger wiggle + blue transition on hover."""
        super().enterEvent(event)
        self._startWiggle()

    def leaveEvent(self, event):
        """Stop animations and reset on mouse leave."""
        super().leaveEvent(event)
        if self._wiggle_anim:
            self._wiggle_anim.stop()
        if self._bg_anim:
            self._bg_anim.stop()
        self._rotation = 0.0
        self._bg_progress = 0.0
        self.update()
        # Reset container background to CSS default
        container = getattr(self.parent_widget, '_widget_container', None)
        if container:
            container.setStyleSheet("")

    def mousePressEvent(self, event):
        """Handle click with 500ms cooldown to prevent accidental triggers."""
        if event.button() == Qt.MouseButton.LeftButton and self.data and self.parent_widget:
            now = time.time()
            if now - self._last_click_time >= 0.5:
                self._last_click_time = now
                self.parent_widget.execute_code(self.data)
