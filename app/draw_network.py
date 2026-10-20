"""TLS LAN transport, UDP discovery and authoritative ordered DrawTogether sessions."""
import select
import base64,hashlib,hmac,ipaddress,json,os,queue,secrets,socket,ssl,struct,sys,tempfile,threading,time,uuid
from pathlib import Path
from datetime import datetime,timedelta,timezone
from draw_state import SharedDrawing,name
PORT=45873
PROTOCOL='repaintko-draw-2'
MAX_MESSAGE=384*1024*1024

def lan(address):
    try:
        ip=ipaddress.ip_address(address)
        return ip.is_loopback or any(ip in ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','169.254.0.0/16'))
    except ValueError:return False

def packet(data):
    raw=json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
    if len(raw)>MAX_MESSAGE:raise ValueError('Nachricht zu groß.')
    return struct.pack('!I',len(raw))+raw

def send(sock,data):
    lock=getattr(sock,'_draw_io_lock',None)
    if lock:
        with lock:sock.sendall(data)
    else:sock.sendall(data)

def receive(sock,limit=MAX_MESSAGE):
    deadline=time.monotonic()+15
    def exact(n):
        chunks=[]
        while n:
            try:
                lock=getattr(sock,'_draw_io_lock',None)
                if lock:
                    # OpenSSL objects have one caller at a time; readiness waits
                    # happen outside the lock so drawing sends never wait for idle reads.
                    with lock:pending=sock.pending()
                    if not pending and not select.select([sock],[],[],.1)[0]:
                        if time.monotonic()>deadline:raise ConnectionError('Verbindung antwortet nicht.')
                        continue
                    with lock:chunk=sock.recv(min(n,65536))
                else:chunk=sock.recv(min(n,65536))
            except socket.timeout:
                if time.monotonic()>deadline:raise ConnectionError('Verbindung antwortet nicht.')
                continue
            if not chunk:raise ConnectionError('Verbindung geschlossen.')
            chunks.append(chunk);n-=len(chunk)
        return b''.join(chunks)
    length=struct.unpack('!I',exact(4))[0]
    if not 0<length<=limit:raise ValueError('Ungültige Nachrichtengröße.')
    obj=json.loads(exact(length))
    if not isinstance(obj,dict):raise ValueError('Ungültige Nachricht.')
    return obj

def close_socket(sock):
    if sock:
        # Interrupt the underlying socket without clearing SSLSocket._sslobj while
        # another thread is inside OpenSSL. TLS objects close when their owning
        # reader/writer references are released.
        try:socket.socket.shutdown(sock,socket.SHUT_RDWR)
        except OSError:pass
        if not isinstance(sock,ssl.SSLSocket):
            try:sock.close()
            except OSError:pass

def server_context():
    vendor=str(Path(__file__).resolve().parent/'draw_vendor')
    if vendor not in sys.path:sys.path.insert(0,vendor)
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes,serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    key=ec.generate_private_key(ec.SECP256R1());subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'DrawTogether')]);now=datetime.now(timezone.utc)
    cert=x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=30)).sign(key,hashes.SHA256())
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2
    with tempfile.TemporaryDirectory(prefix='repaintko-tls-') as folder:
        path=Path(folder);(path/'cert.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM));(path/'key.pem').write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()));context.load_cert_chain(path/'cert.pem',path/'key.pem')
    return context,cert.fingerprint(hashes.SHA256()).hex()

def password_key(password,salt):return hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),bytes.fromhex(salt),200000)
def proof(key,nonce,identity):return hmac.new(key,(nonce+identity).encode('ascii'),hashlib.sha256).hexdigest()

class DrawServer:
    def __init__(self,title,password='',document=None,size=(1920,1080),discovery_port=PORT,max_participants=32):
        self.max_participants=max(2,min(32,int(max_participants)));self.banned=set();self.title=name(title);self.sid=uuid.uuid4().hex;self.state=SharedDrawing(document,size);self.lock=threading.RLock();self.stopped=threading.Event();self.closing=threading.Event();self.peers={};self.users={};self.limit=threading.BoundedSemaphore(32);self.context,self.fingerprint=server_context();self.salt=secrets.token_hex(16);self.key=password_key(password,self.salt);self.locked=bool(password);self.discovery_port=discovery_port
        self.tcp=socket.socket();self.udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        try:
            self.tcp.bind(('0.0.0.0',0));self.tcp.listen(16);self.tcp.settimeout(.5);self.port=self.tcp.getsockname()[1]
            self.udp.bind(('',discovery_port));self.udp.settimeout(.5)
        except Exception:close_socket(self.tcp);close_socket(self.udp);raise
        threading.Thread(target=self.accept,daemon=True).start();threading.Thread(target=self.discover,daemon=True).start()
    def info(self):return dict(protocol=PROTOCOL,id=self.sid,name=self.title,port=self.port,locked=self.locked,fingerprint=self.fingerprint,players=len(self.peers),maximum=self.max_participants)
    def discover(self):
        while not self.stopped.is_set():
            try:
                raw,address=self.udp.recvfrom(2048)
                if not lan(address[0]):continue
                query=json.loads(raw)
                if query.get('protocol')==PROTOCOL and query.get('find') and isinstance(query.get('nonce'),str):self.udp.sendto(json.dumps(dict(self.info(),nonce=query['nonce'][:64])).encode(),address)
            except socket.timeout:continue
            except (OSError,ValueError,AttributeError):continue
    def accept(self):
        while not self.stopped.is_set():
            try:sock,address=self.tcp.accept()
            except (socket.timeout,OSError):continue
            if not lan(address[0]) or not self.limit.acquire(False):close_socket(sock);continue
            threading.Thread(target=self.serve,args=(sock,),daemon=True).start()
    def enqueue(self,peer,message):
        try:peer['out'].put_nowait(packet(message))
        except queue.Full:close_socket(peer['socket'])
    def broadcast(self,message):
        encoded=packet(message)
        for peer in list(self.peers.values()):
            try:peer['out'].put_nowait(encoded)
            except queue.Full:close_socket(peer['socket'])
    def roster(self):return [{'id':key,'name':self.users[key]['name']} for key in self.peers]
    def writer(self,peer):
        try:
            while not self.stopped.is_set() and not peer['closed'].is_set():
                try:data=peer['out'].get(timeout=2)
                except queue.Empty:data=packet({'type':'ping'})
                send(peer['socket'],data)
        except OSError:pass
        finally:close_socket(peer['socket'])
    def serve(self,raw):
        sock=raw;peer=None;identity=None;writer_thread=None
        try:
            raw.settimeout(5);sock=self.context.wrap_socket(raw,server_side=True);sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1);sock.settimeout(1);sock._draw_io_lock=threading.RLock()
            nonce=secrets.token_hex(32);send(sock,packet(dict(type='challenge',protocol=PROTOCOL,id=self.sid,salt=self.salt,nonce=nonce,locked=self.locked)))
            auth=receive(sock,8192);identity=auth.get('identity','');secret=auth.get('secret','')
            if auth.get('type')!='auth' or len(identity)!=32 or len(secret)!=64:raise ValueError('Ungültige Anmeldung.')
            if not hmac.compare_digest(str(auth.get('proof','')),proof(self.key,nonce,identity)):
                send(sock,packet({'type':'denied','message':'Das Passwort ist falsch.'}));return
            with self.lock:
                if identity in self.banned:raise ValueError('Teilnehmer wurde entfernt.')
                if identity not in self.peers and len(self.peers)>=self.max_participants:raise ValueError('Der Raum ist voll.')
                user=self.users.get(identity)
                if user and not hmac.compare_digest(user['secret'],secret):raise ValueError('Wiederverbindung abgelehnt.')
                if not user:
                    if len(self.users)>=256:raise ValueError('Sitzungslimit erreicht. Bitte neue Sitzung starten.')
                    user={'name':name(auth.get('name','Gast')),'secret':secret,'last':0};self.users[identity]=user
                old=self.peers.get(identity)
                if old:old['closed'].set();close_socket(old['socket'])
                peer={'socket':sock,'out':queue.Queue(128),'closed':threading.Event()};self.peers[identity]=peer
                self.enqueue(peer,{'type':'snapshot','state':self.state.export(),'ack':user['last'],'identity':identity});self.broadcast({'type':'users','users':self.roster()})
            writer_thread=threading.Thread(target=self.writer,args=(peer,),daemon=True);writer_thread.start();started=time.monotonic();count=0
            while not self.stopped.is_set() and not peer['closed'].is_set():
                message=receive(sock)
                if message.get('type')=='ping':continue
                if message.get('type')=='cursor':
                    from draw_state import integer
                    x=integer(message.get('x'),0,self.state.size[0]-1);y=integer(message.get('y'),0,self.state.size[1]-1)
                    now=time.monotonic()
                    if now-peer.get('cursor_time',0)>=.05:
                        peer['cursor_time']=now
                        with self.lock:self.broadcast(dict(type='cursor',identity=identity,name=self.users[identity]['name'],x=x,y=y))
                    continue
                if message.get('type')!='op':raise ValueError('Unbekannte Nachricht.')
                count+=1
                if time.monotonic()-started>1:started=time.monotonic();count=1
                if count>240:raise ValueError('Zu viele Aktionen.')
                seq=message.get('seq')
                if type(seq) is not int or seq<1:raise ValueError('Ungültige Aktionsnummer.')
                with self.lock:
                    if self.peers.get(identity) is not peer:break
                    if self.closing.is_set():continue
                    if seq<=user['last']:self.enqueue(peer,{'type':'ack','seq':seq});continue
                    if seq!=user['last']+1:raise ValueError('Aktionsreihenfolge unterbrochen.')
                    try:
                        op=self.state.normalize(message.get('op'));self.state.apply(op);self.broadcast({'type':'op','revision':self.state.revision,'identity':identity,'seq':seq,'op':op})
                    except (ValueError,KeyError,TypeError,IndexError) as exc:self.enqueue(peer,{'type':'rejected','seq':seq,'message':str(exc)})
                    user['last']=seq
        except (OSError,ValueError,KeyError,TypeError,ConnectionError):pass
        finally:
            if peer:peer['closed'].set()
            close_socket(sock)
            with self.lock:
                if peer and self.peers.get(identity) is peer:self.peers.pop(identity,None);self.broadcast({'type':'users','users':self.roster()})
            if writer_thread:writer_thread.join(3)
            if not writer_thread or not writer_thread.is_alive():sock.close()
            self.limit.release()
    def kick(self,identity):
        with self.lock:
            self.banned.add(identity)
            peer=self.peers.get(identity)
            if peer:
                self.enqueue(peer,dict(type='ended'))
                def close():
                    time.sleep(.15);peer['closed'].set();close_socket(peer['socket'])
                threading.Thread(target=close,daemon=True).start()
    def stop(self):
        if self.closing.is_set():return
        with self.lock:
            self.closing.set();self.broadcast({'type':'ended'});peers=list(self.peers.values())
        # Allow the final ordered message to leave each writer without blocking the UI.
        def finish():
            time.sleep(.15);self.stopped.set();close_socket(self.tcp);close_socket(self.udp)
            for peer in peers:peer['closed'].set();close_socket(peer['socket'])
        threading.Thread(target=finish,daemon=True).start()


def discover_servers(targets=None,duration=1.2,port=PORT):
    nonce=secrets.token_hex(12);found={};sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);sock.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1);sock.bind(('',0));sock.settimeout(.15)
    query=json.dumps(dict(protocol=PROTOCOL,find=True,nonce=nonce)).encode()
    try:
        for address in set((targets or ['255.255.255.255'])+['127.0.0.1']):
            try:sock.sendto(query,(address,port))
            except OSError:pass
        until=time.monotonic()+duration
        while time.monotonic()<until:
            try:
                raw,address=sock.recvfrom(4096);item=json.loads(raw)
                if item.get('protocol')!=PROTOCOL or item.get('nonce')!=nonce or not lan(address[0]):continue
                if type(item.get('port')) is not int or not 1<=item['port']<=65535 or len(item.get('fingerprint',''))!=64:continue
                item['host']=address[0];item['name']=name(item.get('name'));found[item['id']]=item
            except (socket.timeout,OSError,ValueError,KeyError,TypeError,AttributeError):continue
    finally:sock.close()
    return list(found.values())

class DrawClient:
    def __init__(self,server,username,password='',on_status=lambda *x:None,on_frame=lambda *x:None,on_users=lambda *x:None,on_error=lambda *x:None,document_frames=False,on_operation=lambda *x:None,on_cursor=lambda *x:None):
        self.on_cursor=on_cursor;self.cursor_pending=None
        self.document_frames=document_frames
        self.on_operation=on_operation
        self.last_rejection=None
        self.server=dict(server);self.username=name(username);self.password=password;self.identity=uuid.uuid4().hex;self.secret=secrets.token_hex(32);self.on_status=on_status;self.on_frame=on_frame;self.on_users=on_users;self.on_error=on_error;self.lock=threading.RLock();self.stop_event=threading.Event();self.pending={};self.sequence=0;self.state=None;self.socket=None;self.connected=False;self.changed=False;self.terminal=False
        threading.Thread(target=self.run,daemon=True).start();threading.Thread(target=self.render,daemon=True).start()
    def submit(self,op):
        with self.lock:
            if not self.connected:raise ConnectionError('Zeichnen ist während der Wiederverbindung pausiert.')
            if len(self.pending)>=2048:raise ConnectionError('Die Verbindung ist ausgelastet. Bitte kurz warten.')
            self.sequence+=1;self.pending[self.sequence]=op
    def render(self):
        while not self.stop_event.wait(.033):
            with self.lock:
                if not self.changed or self.state is None:continue
                image=None if self.document_frames else self.state.doc.composite();meta=self.state.metadata();revision=self.state.revision;self.changed=False
            self.on_frame(image,meta,revision)
    def writer(self,sock,dead):
        sent=0;last_ping=0
        try:
            while not self.stop_event.is_set() and not dead.wait(.016):
                with self.lock:out=[(seq,op) for seq,op in self.pending.items() if seq>sent]
                for seq,op in out:send(sock,packet({'type':'op','seq':seq,'op':op}));sent=seq
                with self.lock:cursor=self.cursor_pending;self.cursor_pending=None
                if cursor:send(sock,packet(dict(type='cursor',x=cursor[0],y=cursor[1])))
                if time.monotonic()-last_ping>2:send(sock,packet({'type':'ping'}));last_ping=time.monotonic()
        except OSError:close_socket(sock)
    def run(self):
        while not self.stop_event.is_set() and not self.terminal:
            sock=None;dead=threading.Event();writer_thread=None
            try:
                self.on_status('Verbinde …',False)
                context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT);context.check_hostname=False;context.verify_mode=ssl.CERT_NONE;context.minimum_version=ssl.TLSVersion.TLSv1_2
                raw=socket.create_connection((self.server['host'],self.server['port']),timeout=4);sock=context.wrap_socket(raw,server_hostname='DrawTogether');sock.settimeout(1);sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1);sock._draw_io_lock=threading.RLock();self.socket=sock
                # Session certificate is pinned from LAN discovery, and never silently replaced on reconnect.
                actual=hashlib.sha256(sock.getpeercert(binary_form=True)).hexdigest()
                if not hmac.compare_digest(actual,self.server['fingerprint']):self.terminal=True;raise ValueError('Das Serverzertifikat hat sich geändert. Bitte neu über die Serversuche beitreten.')
                challenge=receive(sock,8192)
                if challenge.get('id')!=self.server['id'] or challenge.get('protocol')!=PROTOCOL:raise ValueError('Falscher Server.')
                key=password_key(self.password,challenge['salt']);send(sock,packet(dict(type='auth',identity=self.identity,secret=self.secret,name=self.username,proof=proof(key,challenge['nonce'],self.identity))))
                first=receive(sock)
                if first.get('type')=='denied':self.terminal=True;raise ValueError(first['message'])
                if first.get('type')!='snapshot':raise ValueError('Keine vollständige Zeichnung empfangen.')
                state=SharedDrawing.restore(first['state'])
                with self.lock:
                    self.state=state;self.changed=True;self.pending={n:op for n,op in self.pending.items() if n>first['ack']};self.connected=True
                self.on_status('Verbunden · '+self.server['name'],True);writer_thread=threading.Thread(target=self.writer,args=(sock,dead),daemon=True);writer_thread.start()
                while not self.stop_event.is_set():
                    msg=receive(sock);kind=msg.get('type')
                    if kind=='ended':self.terminal=True;self.on_status('Der Host hat die Sitzung beendet. Die letzte Zeichnung kann gespeichert werden.',False);break
                    if kind=='users':self.on_users(msg['users']);continue
                    if kind=='cursor':
                        if msg['identity']!=self.identity:self.on_cursor(msg)
                        continue
                    if kind in ('ack','rejected'):
                        with self.lock:
                            if kind=='rejected':self.last_rejection=msg['message']
                            self.pending.pop(msg['seq'],None);self.changed=True
                        if kind=='rejected':self.on_error(msg['message'])
                    elif kind=='op':
                        with self.lock:
                            if msg['revision']!=self.state.revision+1:raise ValueError('Zeichnung wird neu synchronisiert.')
                            self.state.apply(msg['op']);self.changed=True
                            if msg['identity']==self.identity:self.pending.pop(msg['seq'],None)
                        if msg['identity']!=self.identity:self.on_operation(msg['op'])
            except (OSError,ValueError,KeyError,TypeError,ConnectionError) as exc:
                if not self.stop_event.is_set():self.on_status(str(exc) if self.terminal else 'Verbindung unterbrochen · automatischer Neuversuch …',False)
            finally:
                dead.set();close_socket(sock)
                if writer_thread:writer_thread.join(3)
                if sock and (not writer_thread or not writer_thread.is_alive()):sock.close()
                if self.socket is sock:self.socket=None
                with self.lock:self.connected=False
            if not self.terminal:self.stop_event.wait(2)
    def cursor(self,x,y):
        with self.lock:self.cursor_pending=(x,y)
    def document_copy(self):
        with self.lock:
            if self.state is None:raise ValueError('Noch keine Zeichnung empfangen.')
            from document import Document
            from draw_edits import clone
            return clone(self.state.doc)
    def stop(self):self.stop_event.set();self.connected=False;close_socket(self.socket)
