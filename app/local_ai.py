"""Offline LaMa inpainting and transparent removal. No network access."""
import hashlib
import os
from pathlib import Path
from threading import Lock
from PIL import Image, ImageChops, ImageOps

MODEL_SHA256='7df918ac3921d3daf0aae1d219776cf0dc4e4935f035af81841b40adcf74fdf2'
MODEL_PATH=Path(__file__).parent/'models/lama.onnx'
_session=None
_lock=Lock()


def session():
    global _session
    with _lock:
        if _session is None:
            if not MODEL_PATH.is_file():raise ValueError('Das lokale KI-Modell fehlt. Bitte Repaintko mit dem vollständigen Installer reparieren.')
            with MODEL_PATH.open('rb') as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest()!=MODEL_SHA256:
                    raise ValueError('Die KI-Modelldatei ist beschädigt. Bitte Repaintko reparieren.')
            import onnxruntime as ort
            ort.disable_telemetry_events()
            options=ort.SessionOptions();options.log_severity_level=3
            options.intra_op_num_threads=max(1,min(4,(os.cpu_count() or 2)//2));options.inter_op_num_threads=1
            _session=ort.InferenceSession(str(MODEL_PATH),sess_options=options,providers=['CPUExecutionProvider'])
        return _session


def checked_mask(image,mask):
    if image.size!=mask.size:raise ValueError('Bild und Markierung müssen gleich groß sein.')
    mask=mask.convert('L')
    if not mask.getbbox():raise ValueError('Markiere zuerst die Person oder das Objekt.')
    return mask


def transparent_remove(image,mask):
    mask=checked_mask(image,mask)
    result=image.convert('RGBA')
    result.putalpha(ImageChops.multiply(result.getchannel('A'),ImageOps.invert(mask)))
    return result


def context_box(size,bounds):
    x,y,r,b=bounds;w,h=size
    side=max(128,round(max(r-x,b-y)*2))
    cw,ch=min(w,side),min(h,side)
    left=max(0,min(w-cw,(x+r-cw)//2));top=max(0,min(h-ch,(y+b-ch)//2))
    return left,top,left+cw,top+ch


def inpaint(image,mask,cancel=None,control=None):
    import numpy as np
    import onnxruntime as ort
    mask=checked_mask(image,mask)
    if cancel is not None and cancel.is_set():raise ValueError('Abgebrochen.')
    engine=session()
    if cancel is not None and cancel.is_set():raise ValueError('Abgebrochen.')
    box=context_box(image.size,mask.getbbox())
    region=image.crop(box).convert('RGB');local_mask=mask.crop(box)
    # Letterbox to the model's fixed input without stretching the object.
    scale=min(512/region.width,512/region.height)
    size=(max(1,round(region.width*scale)),max(1,round(region.height*scale)))
    pixels=np.asarray(region.resize(size,Image.Resampling.LANCZOS),dtype=np.float32)/255.0
    pixels=np.pad(pixels,((0,512-size[1]),(0,512-size[0]),(0,0)),mode='edge')
    selected=np.asarray(local_mask.resize(size,Image.Resampling.BOX))>0
    selected=np.pad(selected,((0,512-size[1]),(0,512-size[0])),mode='constant')
    run=ort.RunOptions()
    if control is not None:control['run']=run
    if cancel is not None and cancel.is_set():raise ValueError('Abgebrochen.')
    prediction=engine.run(None,{'image':pixels.transpose(2,0,1)[None].copy(),
                                'mask':selected.astype(np.float32)[None,None]},run)[0]
    if cancel is not None and cancel.is_set():raise ValueError('Abgebrochen.')
    rgb=np.clip(prediction[0].transpose(1,2,0),0,255).astype(np.uint8)[:size[1],:size[0]]
    patch=Image.fromarray(rgb).resize(region.size,Image.Resampling.LANCZOS)
    result=image.copy()
    if result.mode=='RGBA':
        patch=patch.convert('RGBA');patch.putalpha(image.crop(box).getchannel('A'))
    result.paste(patch,box[:2],local_mask)
    return result
