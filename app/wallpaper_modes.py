"""Per-workspace wallpaper preferences and a non-interactive native backdrop."""
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QWidget

MODES = [('paint', 'Paint'), ('gif', 'GIF-Editor'), ('notebook', 'Notizbuch'),
         ('retexto', 'ReTexto / Editor'), ('video', 'Video-Editor'),
         ('browser', 'ReBrowko'), ('draw', 'DrawTogether'),
         ('redrawko', 'ReDrawko'), ('redatako','ReDataKo'), ('help', 'Hilfe')]

def selected_modes(settings):
    value = settings.value('wallpaper/modes', None)
    if value is None:
        return {'paint', 'gif'}  # Preserve the previous canvas-only behavior.
    if isinstance(value, str):
        value = [value] if value else []
    return set(value) & {key for key, _ in MODES}

class Backdrop(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.path = None
        self.pixmap = QPixmap()
        self.scaled = QPixmap()
        self.cached_size = None
        self.opacity = 1.0
        parent.installEventFilter(self)
        self.setGeometry(parent.rect())
        self.lower()

    def configure(self, path, opacity):
        path = str(path) if path else None
        if path != self.path:
            self.path = path
            self.pixmap = QPixmap(path) if path else QPixmap()
            self.cached_size = None
        self.opacity = max(0, min(100, opacity)) / 100
        self.setVisible(not self.pixmap.isNull() and self.opacity > 0)
        self.lower()
        self.update()

    def eventFilter(self, owner, event):
        if event.type() == QEvent.Type.Resize:
            self.setGeometry(owner.rect())
        return False

    def paintEvent(self, event):
        if self.pixmap.isNull():
            return
        if self.cached_size != self.size():
            self.scaled = self.pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                             Qt.TransformationMode.SmoothTransformation)
            self.cached_size = self.size()
        painter = QPainter(self)
        painter.setOpacity(self.opacity)
        painter.drawPixmap((self.width()-self.scaled.width())//2,
                           (self.height()-self.scaled.height())//2, self.scaled)

def apply_background(widget, path, opacity):
    if widget is None:
        return
    backdrop = getattr(widget, '_wallpaper_backdrop', None)
    if backdrop is None and path:
        backdrop = widget._wallpaper_backdrop = Backdrop(widget)
    if backdrop is not None:
        backdrop.configure(path, opacity)
    # Leave editor papers, video frames and websites opaque and unchanged.
    # Only structural containers expose the wallpaper behind the controls.
    for child in widget.findChildren(QWidget):
        if type(child) is QWidget and child.layout() is not None and child is not backdrop:
            previous = getattr(child, '_wallpaper_original_style', None)
            if path and previous is None:
                child._wallpaper_original_style = child.styleSheet()
                child.setProperty('wallpaperContainer', True)
                child.setStyleSheet(child.styleSheet() + '\nQWidget[wallpaperContainer="true"] { background: transparent; }')
            elif not path and previous is not None:
                child.setStyleSheet(previous)
                child.setProperty('wallpaperContainer', False)
                del child._wallpaper_original_style
