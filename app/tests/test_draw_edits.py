import unittest
from PIL import Image,ImageDraw
from draw_state import SharedDrawing
from draw_edits import clone,prepare,compress,inverse,signature

def transaction(before,after,boxes=None):return compress(prepare(clone(before),after,boxes)[0])

class EditorTransactions(unittest.TestCase):
    def test_concurrent_disjoint_pixels_and_conflict_no_partial_write(self):
        state=SharedDrawing(size=(100,100));a=clone(state.doc);b=clone(state.doc)
        a.image.putpixel((10,10),(255,0,0,255));b.image.putpixel((15,15),(0,0,255,255))
        ao=transaction(state.doc,a);bo=transaction(state.doc,b)
        state.apply(ao);state.apply(bo)
        self.assertEqual(state.doc.image.getpixel((10,10)),(255,0,0,255));self.assertEqual(state.doc.image.getpixel((15,15)),(0,0,255,255))
        before=signature(state.doc)
        with self.assertRaises(ValueError):state.apply(ao)
        self.assertEqual(signature(state.doc),before)
        state.apply(inverse(ao));self.assertEqual(state.doc.image.getpixel((10,10))[3],0)
        self.assertEqual(state.doc.image.getpixel((15,15)),(0,0,255,255))
    def test_full_editor_effects_shapes_text_layers_and_resize(self):
        state=SharedDrawing(size=(120,90));doc=clone(state.doc)
        doc.shape('Ellipse',(5,5),(50,50),'#ff0000','#00ff00',3,'Kontur + Füllung')
        doc.apply_stack(doc.image.convert('RGB'),(('brightness',-20,(0,0,120,90)),))
        state.apply(transaction(state.doc,doc));self.assertEqual(state.doc.effect_stack,doc.effect_stack)
        self.assertIsNotNone(state.doc.effect_base)
        doc=clone(state.doc);doc.duplicate_layer();doc.resize((80,60))
        edit=transaction(state.doc,doc);state.apply(edit)
        self.assertEqual(state.size,(80,60));self.assertEqual(len(state.ids),2);self.assertEqual(len(set(state.ids)),2)
        state.apply(inverse(edit));self.assertEqual(state.size,(120,90));self.assertEqual(len(state.ids),1)
        restored=SharedDrawing.restore(state.export());self.assertEqual(signature(restored.doc),signature(state.doc))
    def test_brush_patch_is_small_and_alpha_is_not_lost(self):
        state=SharedDrawing(size=(2000,1000));doc=clone(state.doc);key=state.ids[0]
        doc.image.putpixel((100,100),(0,0,0,80))
        edit=transaction(state.doc,doc,{key:(90,90,120,120)})
        self.assertLess(len(str(edit)),1500);state.apply(edit);self.assertEqual(state.doc.image.getpixel((100,100)),(0,0,0,80))
    def test_batch_undo_is_atomic(self):
        state=SharedDrawing(size=(40,40));doc=clone(state.doc);doc.image.putpixel((1,1),(255,0,0,255));a=transaction(state.doc,doc)
        state.apply(a);doc=clone(state.doc);doc.image.putpixel((2,2),(0,255,0,255));b=transaction(state.doc,doc);state.apply(b)
        state.apply(dict(kind='batch',ops=[inverse(b),inverse(a)]));self.assertIsNone(state.doc.image.getbbox())
