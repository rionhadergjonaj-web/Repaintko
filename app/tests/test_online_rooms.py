import asyncio
import json
import sys
import threading
import unittest
import uuid
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from server.main import Service
from websockets.asyncio.server import serve
from websockets.sync.client import connect
from draw_state import SharedDrawing


class OnlineIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ready = threading.Event()
        cls.loop = asyncio.new_event_loop()
        cls.service = Service()
        def run():
            asyncio.set_event_loop(cls.loop)
            async def start():
                cls.server = await serve(cls.service.handle, "127.0.0.1", 0, compression=None)
                cls.port = cls.server.sockets[0].getsockname()[1]
                cls.ready.set()
            cls.loop.run_until_complete(start())
            cls.loop.run_forever()
        cls.thread = threading.Thread(target=run, daemon=True)
        cls.thread.start()
        assert cls.ready.wait(5)

    @classmethod
    def tearDownClass(cls):
        async def stop():
            cls.server.close()
            await cls.server.wait_closed()
        asyncio.run_coroutine_threadsafe(stop(), cls.loop).result(10)
        cls.loop.call_soon_threadsafe(cls.loop.stop)
        cls.thread.join(5)
        cls.loop.close()

    def socket(self):
        ws = connect(f"ws://127.0.0.1:{self.port}", legacy=True, proxy=None, compression=None)
        self.addCleanup(ws.close)
        return ws

    def send(self, ws, **msg):
        ws.send(json.dumps(msg))

    def receive(self, ws, kind):
        for _ in range(15):
            msg = json.loads(ws.recv(timeout=5))
            if msg["type"] == kind:
                return msg
        self.fail("Expected message not received")

    def test_password_layers_reconnect_and_permissions(self):
        a = self.socket()
        owner, secret = uuid.uuid4().hex, uuid.uuid4().hex * 2
        initial = SharedDrawing(size=(32,32))
        initial.apply(initial.normalize(dict(kind="add", name="Zweite Ebene")))
        self.send(a, type="create", identity=owner, secret=secret, username="A",
                  password="test-only", name="Integration", maximum=2, state=initial.export())
        first = self.receive(a, "snapshot")
        room = first["room"]["id"]
        denied = self.socket()
        self.send(denied, type="join", identity=uuid.uuid4().hex, secret=uuid.uuid4().hex*2,
                  username="B", password="wrong", room=room)
        self.assertEqual(self.receive(denied,"denied")["message"],"Das Passwort ist falsch.")
        b = self.socket()
        bid, bsecret = uuid.uuid4().hex, uuid.uuid4().hex*2
        self.send(b,type="join",identity=bid,secret=bsecret,username="B",password="test-only",room=room)
        self.receive(b,"snapshot")
        for ws,key,color in ((a,initial.ids[0],"#ff0000"),(b,initial.ids[1],"#0000ff")):
            self.send(ws,type="op",seq=1,op=dict(kind="stroke",layer=key,points=[[5,5],[10,10]],width=3,opacity=100,color=color,tool="Pinsel"))
        opsa=[self.receive(a,"op"),self.receive(a,"op")]
        opsb=[self.receive(b,"op"),self.receive(b,"op")]
        self.assertEqual(opsa,opsb)
        self.assertEqual([m["revision"] for m in opsa],[2,3])
        b.close()
        b2=self.socket()
        self.send(b2,type="join",identity=bid,secret=bsecret,username="B",password="test-only",room=room)
        snap=self.receive(b2,"snapshot")
        self.assertEqual(snap["ack"],1)
        state=SharedDrawing.restore(snap["state"])
        self.assertEqual(state.doc.layers[0]["image"].getpixel((5,5))[:3],(255,0,0))
        self.assertEqual(state.doc.layers[1]["image"].getpixel((5,5))[:3],(0,0,255))
        self.send(b2,type="op",seq=1,op=opsa[1]["op"])
        self.receive(b2,"ack")
        self.send(b2,type="close")
        self.assertIn("Host",self.receive(b2,"denied")["message"])
        self.assertIn(room,self.service.registry.rooms)
        self.send(a,type="close")
        self.receive(a,"ended")

    def test_desktop_transport(self):
        from draw_online import OnlineClient
        endpoint=f'ws://127.0.0.1:{self.port}'
        initial=SharedDrawing(size=(32,32))
        a=OnlineClient(dict(endpoint=endpoint,create=True,state=initial.export(),name='Desktop',maximum=3),'Alice',document_frames=True)
        self.addCleanup(a.stop)
        def wait(predicate):
            until=time.monotonic()+8
            while time.monotonic()<until:
                if predicate():return
                time.sleep(.02)
            self.fail('Desktop transport did not synchronize')
        wait(lambda:a.connected)
        b=OnlineClient(dict(endpoint=endpoint,id=a.server['id'],name='Desktop'),'Bob',document_frames=True)
        self.addCleanup(b.stop)
        wait(lambda:b.connected)
        key=a.state.ids[0]
        a.submit(dict(kind='stroke',layer=key,points=[[4,4]],width=3,opacity=100,color='#00ff00',tool='Pinsel'))
        wait(lambda:b.state.revision==1 and not a.pending)
        self.assertEqual(b.document_copy().layers[0]['image'].getpixel((4,4)),(0,255,0,255))
        a.administer('kick',b.identity)
        wait(lambda:b.terminal)
        a.administer('close')
        wait(lambda:a.terminal)

    def test_tls_verified_connection_and_untrusted_certificate(self):
        import ssl, tempfile, datetime, ipaddress
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        key=ec.generate_private_key(ec.SECP256R1())
        subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'localhost')])
        now=datetime.datetime.now(datetime.timezone.utc)
        cert=(x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
              .serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(minutes=1))
              .not_valid_after(now+datetime.timedelta(days=1))
              .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),False)
              .sign(key,hashes.SHA256()))
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);certfile=root/'cert.pem';keyfile=root/'key.pem'
            certfile.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            keyfile.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
            context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(certfile,keyfile)
            async def start():return await serve(self.service.handle,'127.0.0.1',0,ssl=context,compression=None)
            tlsserver=asyncio.run_coroutine_threadsafe(start(),self.loop).result(5)
            endpoint=f'wss://127.0.0.1:{tlsserver.sockets[0].getsockname()[1]}'
            try:
                with self.assertRaises(ssl.SSLCertVerificationError):
                    with connect(endpoint,proxy=None):pass
                trusted=ssl.create_default_context(cafile=str(certfile))
                with connect(endpoint,ssl=trusted,proxy=None) as ws:
                    self.send(ws,type='list');self.assertIsInstance(self.receive(ws,'rooms')['rooms'],list)
            finally:
                async def stop():tlsserver.close();await tlsserver.wait_closed()
                asyncio.run_coroutine_threadsafe(stop(),self.loop).result(5)


if __name__ == "__main__":
    unittest.main()
