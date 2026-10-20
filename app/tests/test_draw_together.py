import unittest,time,threading,tempfile,socket
from pathlib import Path
from draw_state import SharedDrawing
from draw_network import DrawServer,DrawClient,discover_servers,close_socket,packet,receive

def wait_for(test,timeout=10):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  if test():return
  time.sleep(.025)
 raise AssertionError('Timed out waiting for synchronized network state')

def stroke(layer,color,x,y=20):return dict(kind='stroke',layer=layer,tool='Pinsel',color=color,width=5,opacity=100,points=[[x,y],[x+10,y]])

class DrawStateTests(unittest.TestCase):
 def test_layers_and_serialized_roundtrip(self):
  s=SharedDrawing(size=(100,80));bottom=s.ids[0];s.apply(s.normalize({'kind':'add','name':'Oben'}));top=s.ids[1];s.apply(s.normalize(stroke(bottom,'#ff0000',10)));s.apply(s.normalize(stroke(top,'#0000ff',40)));s.apply(s.normalize(dict(kind='opacity',layer=top,value=42)));s.apply(s.normalize(dict(kind='move',layer=top,offset=-1)));r=SharedDrawing.restore(s.export());self.assertEqual(s.ids,r.ids);self.assertEqual(s.doc.composite().tobytes(),r.doc.composite().tobytes());self.assertEqual(r.doc.layers[r.ids.index(bottom)]['image'].getpixel((15,20)),(255,0,0,255))
 def test_invalid_operations_do_not_mutate(self):
  s=SharedDrawing(size=(30,30));before=s.export()
  for op in [dict(kind='delete',layer=s.ids[0]),stroke('missing','#ff0000',1),stroke(s.ids[0],'broken',1),dict(stroke(s.ids[0],'#000000',1),width=999),dict(kind='rename',layer=s.ids[0],name=None)]:
   with self.assertRaises((ValueError,TypeError)):s.normalize(op)
   self.assertEqual(s.export(),before)
 def test_eraser_never_touches_other_layer(self):
  s=SharedDrawing(size=(80,80));first=s.ids[0];s.apply(s.normalize(stroke(first,'#ff0000',10)));s.apply(s.normalize(dict(kind='add',name='Zwei')));second=s.ids[1];s.apply(s.normalize(stroke(second,'#0000ff',10)));s.apply(s.normalize(dict(stroke(second,'#000000',10),tool='Radierer')));self.assertEqual(s.doc.layers[0]['image'].getpixel((15,20)),(255,0,0,255));self.assertEqual(s.doc.layers[1]['image'].getpixel((15,20))[3],0)

class DrawNetworkTests(unittest.TestCase):
 def test_normal_editor_transactions_and_undo_over_network(self):
  from draw_edits import clone,prepare,compress,inverse,signature
  a=self.client();b=self.client();wait_for(lambda:a.connected and b.connected)
  left=a.document_copy();right=b.document_copy()
  left.image.putpixel((10,10),(255,0,0,255));right.image.putpixel((80,80),(0,0,255,255))
  ao=compress(prepare(a.document_copy(),left)[0]);bo=compress(prepare(b.document_copy(),right)[0])
  a.submit(ao);b.submit(bo);self.sync(a,b)
  a.submit(dict(kind='batch',ops=[inverse(ao)]));self.sync(a,b)
  self.assertEqual(a.state.doc.image.getpixel((10,10))[3],0);self.assertEqual(a.state.doc.image.getpixel((80,80)),(0,0,255,255))
  before=a.document_copy();after=clone(before);after.add_layer();after.image.putpixel((30,30),(0,255,0,255))
  a.submit(compress(prepare(before,after)[0]));self.sync(a,b)
  late=self.client();wait_for(lambda:late.connected);self.sync(late)
  self.assertEqual(signature(late.state.doc),signature(self.server.state.doc))
 def setUp(self):
  self.server=DrawServer('LAN Test','secret-password',size=(180,100),discovery_port=0);self.clients=[];self.info=dict(self.server.info(),host='127.0.0.1')
 def tearDown(self):
  for c in self.clients:c.stop()
  self.server.stop();wait_for(self.server.stopped.is_set)
 def client(self,password='secret-password',username='User'):
  c=DrawClient(self.info,username,password);self.clients.append(c);return c
 def sync(self,*clients):
  wait_for(lambda:all(c.state is not None and c.state.revision==self.server.state.revision and not c.pending for c in clients))
  for c in clients:
   with c.lock,self.server.lock:self.assertEqual(c.state.doc.composite().tobytes(),self.server.state.doc.composite().tobytes())
 def test_discovery_auth_and_encryption(self):
  result=discover_servers(['127.0.0.1'],.25,self.server.udp.getsockname()[1]);self.assertEqual(result[0]['name'],'LAN Test');self.assertTrue(result[0]['locked']);self.assertNotIn('password',str(result));bad=self.client('wrong');wait_for(lambda:bad.terminal);self.assertIsNone(bad.state);good=self.client();wait_for(lambda:good.connected);self.assertIn(good.socket.version(),('TLSv1.2','TLSv1.3'))
 def test_concurrent_layers_late_join_and_metadata(self):
  a=self.client(username='Anna');b=self.client(username='Ben');c=self.client(username='Chris');wait_for(lambda:all(x.connected for x in (a,b,c)));base=self.server.state.ids[0]
  a.submit(dict(kind='add',name='Zwei'));wait_for(lambda:len(self.server.state.ids)==2);b.submit(dict(kind='add',name='Drei'));wait_for(lambda:len(self.server.state.ids)==3);self.sync(a,b,c);ids=self.server.state.ids[:]
  def draw(client,key,color,y):
   for x in range(10,100,10):client.submit(stroke(key,color,x,y))
  threads=[threading.Thread(target=draw,args=(user,key,color,y)) for user,key,color,y in zip((a,b,c),ids,('#ff0000','#00ff00','#0000ff'),(20,40,60))]
  for t in threads:t.start()
  for t in threads:t.join()
  self.sync(a,b,c);self.assertEqual(self.server.state.doc.layers[0]['image'].getpixel((15,20)),(255,0,0,255));self.assertEqual(self.server.state.doc.layers[1]['image'].getpixel((15,40)),(0,255,0,255))
  a.submit(dict(kind='rename',layer=ids[1],name='Gemeinsam'));b.submit(dict(kind='opacity',layer=ids[2],value=55));c.submit(dict(kind='visible',layer=ids[0],value=False));a.submit(dict(kind='move',layer=ids[2],offset=-1));self.sync(a,b,c)
  late=self.client(username='Late');wait_for(lambda:late.connected);self.sync(late);self.assertEqual(late.state.metadata(),self.server.state.metadata());b.submit(dict(kind='delete',layer=ids[1]));self.sync(a,b,c,late)
 def test_same_layer_concurrency_and_reconnect_exactly_once(self):
  a=self.client();b=self.client();wait_for(lambda:a.connected and b.connected);key=self.server.state.ids[0]
  for x in range(10,100,10):a.submit(stroke(key,'#ff0000',x,20));b.submit(stroke(key,'#0000ff',x,60))
  self.sync(a,b);before=self.server.state.revision
  # Simulate the server committing a command whose acknowledgement is lost.
  with self.server.lock:
   user=self.server.users[a.identity];op=self.server.state.normalize(stroke(key,'#00ff00',10,40));self.server.state.apply(op);user['last']+=1
   with a.lock:a.sequence+=1;a.pending[a.sequence]=op
   close_socket(a.socket)
  wait_for(lambda:not a.connected);wait_for(lambda:a.connected,12)
  # b missed this synthetic injection too; force a full resync of that client.
  close_socket(b.socket);wait_for(lambda:not b.connected);wait_for(lambda:b.connected,12);self.sync(a,b);self.assertEqual(self.server.state.revision,before+1);self.assertFalse(a.pending)
 def test_shutdown_notifies_clients(self):
  a=self.client();wait_for(lambda:a.connected);self.server.stop();wait_for(lambda:a.terminal);self.assertIsNotNone(a.state)
 def test_certificate_change_is_rejected(self):
  self.info['fingerprint']='0'*64;c=self.client();wait_for(lambda:c.terminal);self.assertIsNone(c.state)
 def test_open_server(self):
  other=DrawServer('Ohne Passwort',size=(20,20),discovery_port=0)
  try:
   c=DrawClient(dict(other.info(),host='127.0.0.1'),'Gast');self.clients.append(c);wait_for(lambda:c.connected);self.assertFalse(other.locked)
  finally:other.stop();wait_for(other.stopped.is_set)

class DrawWidgetTests(unittest.TestCase):
 def test_local_layer_selection_and_embedded_switch(self):
  import os
  from unittest.mock import patch
  from PySide6.QtWidgets import QApplication
  from browser_mode import Browser
  from browser_store import BrowserStore
  from qt_app import Repainko
  app=QApplication.instance() or QApplication([])
  with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'REPAINKO_SETTINGS_PATH':str(Path(folder)/'p.ini')}),patch.object(Browser,'check'),patch('browser_mode.BrowserStore',side_effect=lambda unused:BrowserStore(folder)):
   from draw_edits import clone
   from qt_app import TOOLS
   w=Repainko();w.show();doc=w.doc;w.open_draw_together();d=w.draw_together;d.search_timer.stop()
   self.assertTrue(w.draw_active);self.assertIs(d.window(),w)
   self.assertEqual([d.editor.tool.itemText(i) for i in range(d.editor.tool.count())],TOOLS)
   self.assertFalse(d.editor.mode_menu.menuAction().isVisible());self.assertFalse(w.mode_menu.menuAction().isVisible())
   s=SharedDrawing(size=(100,80));s.apply(s.normalize(dict(kind='add',name='Oben')))
   d.editor.shared_bridge.receive(clone(s.doc));d.editor.doc.active=0;chosen=d.editor.doc.layers[0]['_shared_id']
   s.apply(s.normalize(dict(kind='rename',layer=s.ids[1],name='Neu')));d.editor.shared_bridge.receive(clone(s.doc))
   self.assertEqual(d.editor.doc.layers[d.editor.doc.active]['_shared_id'],chosen)
   self.assertFalse(d.editor.findChildren(__import__('PySide6.QtWidgets',fromlist=['QToolBar']).QToolBar)[0].isHidden())
   w.open_help();w.return_from_help();self.assertTrue(w.draw_active);w.leave_video_editor();self.assertIs(w.doc,doc)
   d.editor.shared_bridge.shutdown();w.close()
