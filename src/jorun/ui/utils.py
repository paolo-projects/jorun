from PySide6.QtGui import QPixmap, QColor, QIcon
from PySide6.QtWidgets import QStyle


def icon_from_standard_pixmap(style: QStyle, p: QStyle.StandardPixmap, color: str):
    p = style.standardPixmap(p)
    p2 = QPixmap(p.size())
    p2.fill(QColor.fromString(color))
    p2.setMask(p.createHeuristicMask())

    return QIcon(p2)
