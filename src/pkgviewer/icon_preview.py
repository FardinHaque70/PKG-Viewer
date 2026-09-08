"""Aspect-preserving preview whose image cannot enlarge the window layout."""

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QFrame, QSizePolicy


class IconPreview(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._image = QImage()
        self._message = "Drop a PKG file here"
        self.setObjectName("icon")
        self.setAccessibleName("Package icon preview")
        self.setMinimumSize(160, 160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def sizeHint(self):
        return QSize(280, 280)

    def set_image(self, image):
        self._image = image
        self._message = ""
        self.update()

    def set_message(self, message):
        self._image = QImage()
        self._message = message
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        area = QRectF(self.contentsRect()).adjusted(6, 6, -6, -6)
        if area.isEmpty():
            return
        if self._image.isNull():
            painter.setPen(self.palette().windowText().color())
            painter.drawText(area, Qt.AlignCenter | Qt.TextWordWrap, self._message)
            return
        size = self._image.size().scaled(area.size().toSize(), Qt.KeepAspectRatio)
        target = QRectF(0, 0, size.width(), size.height())
        target.moveCenter(area.center())
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawImage(target, self._image)
