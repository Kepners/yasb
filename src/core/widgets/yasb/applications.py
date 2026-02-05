import logging
import os
import subprocess

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
    """QLabel with rotation animation support for wiggle effect."""

    def __init__(self, parent: ApplicationsWidget | None = None):
        super().__init__(parent)
        self.parent_widget = parent
        self.data = None
        self.container = None
        self._rotation = 0.0  # Rotation angle in degrees
        self._wiggle_anim = None
        self._text_content = ""  # Cache text for custom painting

    def getRotation(self):
        return self._rotation

    def setRotation(self, angle):
        self._rotation = angle
        self.update()  # Trigger repaint

    # Define rotation as a Qt property for animation
    rotation = pyqtProperty(float, getRotation, setRotation)

    def setText(self, text):
        """Override to cache text content."""
        self._text_content = text
        super().setText(text)

    def paintEvent(self, event):
        """Custom paint with rotation transform around center."""
        if abs(self._rotation) < 0.1:
            # No significant rotation - use default painting
            super().paintEvent(event)
            return

        # Don't call super() - we handle all painting
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Save painter state
        painter.save()

        # Rotate around widget center
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        painter.translate(cx, cy)
        painter.rotate(self._rotation)
        painter.translate(-cx, -cy)

        # Draw text (font icon) centered
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.setFont(self.font())
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._text_content or self.text())

        painter.restore()
        painter.end()

    def _startWiggle(self):
        """Start rotational wiggle animation matching LayoutForge HotCorner."""
        # Stop any existing animation
        if self._wiggle_anim:
            self._wiggle_anim.stop()

        self._wiggle_anim = QPropertyAnimation(self, b"rotation")
        self._wiggle_anim.setDuration(400)  # 400ms like LayoutForge

        # Keyframes: 0 -> -8 -> 6 -> -4 -> 2 -> 0 (matching HotCorner shake)
        self._wiggle_anim.setKeyValueAt(0.0, 0.0)
        self._wiggle_anim.setKeyValueAt(0.15, -8.0)
        self._wiggle_anim.setKeyValueAt(0.35, 6.0)
        self._wiggle_anim.setKeyValueAt(0.55, -4.0)
        self._wiggle_anim.setKeyValueAt(0.75, 2.0)
        self._wiggle_anim.setKeyValueAt(1.0, 0.0)

        self._wiggle_anim.start()

    def enterEvent(self, event):
        """Trigger rotational wiggle animation on hover."""
        super().enterEvent(event)
        self._startWiggle()

    def leaveEvent(self, event):
        """Stop wiggle and reset rotation on mouse leave."""
        super().leaveEvent(event)
        if self._wiggle_anim:
            self._wiggle_anim.stop()
        self._rotation = 0.0
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.data and self.parent_widget:
            self.parent_widget.execute_code(self.data)
