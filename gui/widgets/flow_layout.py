"""Wrapping actions keep scientific page headers usable at large text sizes."""
from PySide6.QtCore import Qt, QRect, QSize, QPoint
from PySide6.QtWidgets import QLayout, QWidget, QHBoxLayout


class FlowLayout(QLayout):
    def __init__(self, parent=None, spacing=8):
        super().__init__(parent)
        self.items = []
        self.setContentsMargins(0,0,0,0)
        self.setSpacing(spacing)

    def addItem(self, item):
        self.items.append(item)

    def add_group(self, *widgets):
        """Keep a field's label and control together when actions wrap."""
        group = QWidget()
        row = QHBoxLayout(group)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(self.spacing())
        for widget in widgets:
            row.addWidget(widget)
        self.addWidget(group)
        return group

    def count(self):
        return len(self.items)

    def itemAt(self, index):
        return self.items[index] if 0 <= index < len(self.items) else None

    def takeAt(self, index):
        return self.items.pop(index) if 0 <= index < len(self.items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._arrange(QRect(0,0,width,0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._arrange(rect, False)

    def sizeHint(self):
        sizes = [item.sizeHint() for item in self.items if not item.isEmpty()]
        left,top,right,bottom = self.getContentsMargins()
        return QSize(sum(size.width() for size in sizes)+max(0,len(sizes)-1)*self.spacing()+left+right,
                     max((size.height() for size in sizes), default=0)+top+bottom)

    def minimumSize(self):
        result = QSize()
        for item in self.items:
            if not item.isEmpty():
                result = result.expandedTo(item.minimumSize())
        left,top,right,bottom = self.getContentsMargins()
        return result + QSize(left+right,top+bottom)

    def _arrange(self, rect, dry_run):
        left,top,right,bottom = self.getContentsMargins()
        area = rect.adjusted(left,top,-right,-bottom)
        x,y,height = area.x(),area.y(),0
        gap = max(0,self.spacing())
        for item in self.items:
            if item.isEmpty():
                continue
            size = item.sizeHint()
            if x > area.x() and x+size.width() > area.right()+1:
                x,y,height = area.x(),y+height+gap,0
            if not dry_run:
                item.setGeometry(QRect(QPoint(x,y),size))
            x += size.width()+gap
            height = max(height,size.height())
        return y+height-rect.y()+bottom
