import base64,copy,json,tempfile,unittest,zlib
from pathlib import Path
from urllib.parse import quote
from redraw_model import DiagramDocument,template,validate
from redraw_io import drawio_import,drawio_export,sql_export,sql_import,xml_parse
from redraw_addon import ReDrawkoStore

class DiagramTests(unittest.TestCase):
    def test_history_and_cascading_delete(self):
        doc=DiagramDocument();doc.data=template('erm');before=doc.serial();key=doc.page['nodes'][0]['id']
        doc.change(lambda:doc.delete({key}))
        self.assertFalse(any(e['source']==key or e['target']==key for e in doc.page['edges']))
        after=doc.serial();doc.history();self.assertEqual(doc.serial(),before);doc.history(True);self.assertEqual(doc.serial(),after)

    def test_duplicate_and_failed_edit_are_isolated(self):
        doc=DiagramDocument();doc.data=template('erm');before=doc.serial();keys=[n['id'] for n in doc.page['nodes']]
        doc.change(lambda:doc.duplicate(keys));self.assertEqual(len(doc.page['nodes']),8);validate(doc.data)
        with self.assertRaises(ValueError):doc.change(lambda:doc.page['nodes'][0].update(w=float('nan')))
        self.assertEqual(len(doc.page['nodes']),8)
        doc.history();self.assertEqual(doc.serial(),before)

    def test_native_roundtrip_and_bad_file_preserve_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'test.redrawko';doc=DiagramDocument();doc.data=template('erm');doc.save(path);new=DiagramDocument();new.load(path);self.assertEqual(new.serial(),doc.serial())
            raw=copy.deepcopy(doc.data);raw['pages'][0]['edges'][0]['end']='invalid';path.write_text(json.dumps(raw),encoding='utf-8')
            with self.assertRaises(ValueError):new.load(path)
            self.assertEqual(new.serial(),doc.serial())

    def test_compressed_drawio_and_xml_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'test.drawio';drawio_export(template('erm'),path)
            import xml.etree.ElementTree as ET
            tree=ET.fromstring(path.read_bytes());diagram=tree.find('diagram');raw=ET.tostring(diagram.find('mxGraphModel'),encoding='unicode')
            compressor=zlib.compressobj(wbits=-15);compressed=compressor.compress(quote(raw).encode())+compressor.flush();diagram.remove(diagram[0]);diagram.text=base64.b64encode(compressed).decode();path.write_bytes(ET.tostring(tree))
            data,warnings=drawio_import(path);self.assertEqual(len(data['pages'][0]['nodes']),4)
            with self.assertRaises(ValueError):xml_parse(b'<!DOCTYPE x [<!ENTITY a "x">]><x>&a;</x>')

    def test_sql_and_addon_lifecycle(self):
        doc=template('erm');self.assertEqual(len(sql_import(sql_export(doc['pages'][0]))['nodes']),4)
        with tempfile.TemporaryDirectory() as tmp:
            store=ReDrawkoStore(tmp);self.assertFalse(store.installed());store.install();self.assertTrue(store.installed());self.assertEqual(len(store.templates()),6)
            project=store.root/'my-project.redrawko';project.write_text('keep',encoding='utf-8');store.uninstall();self.assertFalse(store.installed());self.assertEqual(project.read_text(),'keep')
