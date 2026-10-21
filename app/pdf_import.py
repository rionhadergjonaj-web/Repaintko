"""Import a selected PDF page as editable pixels using Qt PDF."""
from PIL import Image
from PySide6.QtCore import QSize,Qt
from PySide6.QtGui import QImage,QPixmap
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import QDialog,QVBoxLayout,QFormLayout,QLabel,QSpinBox,QComboBox,QDialogButtonBox,QMessageBox
from document import checked_size
from shiboken6 import delete


class PdfPasswordRequired(ValueError):pass


def load_pdf(path,password=''):
    document=QPdfDocument()
    if password:document.setPassword(password)
    error=document.load(str(path))
    if error==QPdfDocument.Error.IncorrectPassword:
        document.close();raise PdfPasswordRequired('Dieses PDF benötigt ein gültiges Passwort.')
    if error!=QPdfDocument.Error.None_ or document.pageCount()<1:
        document.close();raise ValueError('Das PDF konnte nicht gelesen werden. Es ist möglicherweise beschädigt oder verwendet einen nicht unterstützten Schutz.')
    return document


def page_size(document,page,dpi):
    if not 0<=page<document.pageCount():raise ValueError('Ungültige PDF-Seite.')
    points=document.pagePointSize(page)
    if dpi not in (72,150,300,600):raise ValueError('Ungültige PDF-Auflösung.')
    return checked_size(max(1,round(points.width()*dpi/72)),max(1,round(points.height()*dpi/72)))


def render_page(document,page,dpi):
    width,height=page_size(document,page,dpi)
    rendered=document.render(page,QSize(width,height))
    if rendered.isNull():raise ValueError('Die PDF-Seite konnte nicht gerendert werden.')
    rendered=rendered.convertToFormat(QImage.Format.Format_RGBA8888)
    image=Image.frombytes('RGBA',(width,height),bytes(rendered.constBits()),'raw','RGBA',rendered.bytesPerLine())
    return Image.alpha_composite(Image.new('RGBA',image.size,'white'),image).convert('RGB')


class PdfImportDialog(QDialog):
    def __init__(self,path,parent=None,password=''):
        document=load_pdf(path,password)
        super().__init__(parent);self.document=document;document.setParent(self)
        self.result_image=None
        available=self.screen().availableGeometry()
        self.setWindowTitle('PDF-Seite öffnen');self.resize(490,min(490,available.height()-60))
        layout=QVBoxLayout(self)
        self.preview=QLabel();self.preview.setFixedSize(450,min(290,max(120,available.height()-310)));self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview,0,Qt.AlignmentFlag.AlignCenter)
        form=QFormLayout();layout.addLayout(form)
        self.page=QSpinBox();self.page.setRange(1,document.pageCount());self.page.setSuffix(f' / {document.pageCount()}');self.page.setKeyboardTracking(False)
        self.dpi=QComboBox()
        for dpi in (72,150,300,600):self.dpi.addItem(f'{dpi} dpi',dpi)
        self.dpi.setCurrentIndex(1)
        form.addRow('Seite',self.page);form.addRow('Auflösung',self.dpi)
        self.info=QLabel();self.info.setWordWrap(True);layout.addWidget(self.info)
        note=QLabel('Die gewählte Seite wird als Bild geöffnet. Text und Vektoren werden zu Pixeln. Das Original-PDF bleibt unverändert.')
        note.setWordWrap(True);layout.addWidget(note)
        self.buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Open|QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Open).setText('Seite öffnen')
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Abbrechen')
        layout.addWidget(self.buttons);self.buttons.accepted.connect(self.import_page);self.buttons.rejected.connect(self.reject)
        self.page.valueChanged.connect(self.update_preview);self.dpi.currentIndexChanged.connect(self.update_preview)
        self.update_preview()

    def update_preview(self):
        try:
            width,height=page_size(self.document,self.page.value()-1,self.dpi.currentData())
            self.info.setText(f'{width} × {height} Pixel')
            ratio=min(self.preview.width()/width,self.preview.height()/height)
            image=self.document.render(self.page.value()-1,QSize(max(1,round(width*ratio)),max(1,round(height*ratio))))
            if image.isNull():raise ValueError('Keine Vorschau verfügbar.')
            self.preview.setPixmap(QPixmap.fromImage(image))
            self.buttons.button(QDialogButtonBox.StandardButton.Open).setEnabled(True)
        except Exception as error:
            self.preview.clear();self.info.setText(str(error));self.buttons.button(QDialogButtonBox.StandardButton.Open).setEnabled(False)

    def import_page(self):
        try:
            self.result_image=render_page(self.document,self.page.value()-1,self.dpi.currentData())
            self.release()
            self.accept()
        except Exception as error:QMessageBox.warning(self,'PDF öffnen',str(error))

    def done(self,result):
        self.release();super().done(result)

    def release(self):
        if self.document is not None:
            self.document.close();delete(self.document);self.document=None
