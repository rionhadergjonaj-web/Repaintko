"""Forward Windows browser launches to the running application, per user."""
import getpass,hashlib,json
from urllib.parse import urlsplit
from PySide6.QtNetwork import QLocalServer,QLocalSocket

NAME='Repaintko-Browser-'+hashlib.sha256(getpass.getuser().encode()).hexdigest()[:16]

def forward(url):
    socket=QLocalSocket();socket.connectToServer(NAME)
    if not socket.waitForConnected(250):return False
    socket.write((json.dumps({'url':url})+'\n').encode());socket.waitForBytesWritten(1000);socket.disconnectFromServer();return True

def listen(window):
    server=QLocalServer(window);server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
    if not server.listen(NAME):return None
    def connected():
        socket=server.nextPendingConnection();buffer=bytearray()
        def receive():
            buffer.extend(bytes(socket.readAll()))
            if len(buffer)>8192:socket.disconnectFromServer();return
            if b'\n' not in buffer:return
            try:
                value=json.loads(buffer.split(b'\n')[0]);url=value.get('url','')
                if url and (urlsplit(url).scheme not in ('http','https') or not urlsplit(url).hostname):return
                window.open_browser()
                if url:window.browser.open_external(url)
                window.showNormal();window.raise_();window.activateWindow()
            except (ValueError,TypeError,AttributeError):pass
            socket.disconnectFromServer()
        socket.readyRead.connect(receive);socket.disconnected.connect(socket.deleteLater)
        if socket.bytesAvailable():receive()
    server.newConnection.connect(connected);return server
