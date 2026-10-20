"""Read browser image drag payloads without executing embedded HTML."""
import base64
import io
import time
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote_to_bytes
from urllib.request import Request, build_opener, HTTPRedirectHandler
from document import load_image

MAX_DOWNLOAD = 40 * 1024 * 1024


def image_url(value):
    value=value.strip()
    parts=urlsplit(value)
    return value if (parts.scheme in ('http','https') and parts.hostname and not parts.username and not parts.password) or value.startswith('data:image/') else None


class Images(HTMLParser):
    def __init__(self):
        super().__init__();self.sources=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower()=='img':
            source=dict(attrs).get('src','')
            if source:self.sources.append(source)


def browser_source(mime):
    if mime.hasImage():return ('native',None)
    if mime.hasHtml():
        parser=Images();parser.feed(mime.html())
        if len(parser.sources)==1:
            url=image_url(parser.sources[0])
            if url:return ('url',url)
    urls=mime.urls()
    if len(urls)==1:
        url=image_url(urls[0].toString())
        if url:return ('url',url)
    if not urls and mime.hasText():
        url=image_url(mime.text())
        if url:return ('url',url)
    return None


class WebRedirects(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if urlsplit(newurl).scheme not in ('http','https'):
            raise ValueError('Die Bildadresse leitet auf einen nicht unterstützten Dateityp um.')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def download_image(url,cancel):
    if not image_url(url):raise ValueError('Keine unterstützte Bildadresse.')
    if url.startswith('data:image/'):
        header,data=url.split(',',1)
        if len(data)>MAX_DOWNLOAD*4//3+8:raise ValueError('Das Bild ist größer als 40 MB.')
        data=base64.b64decode(data,validate=True) if ';base64' in header else unquote_to_bytes(data)
    else:
        request=Request(url,headers={'User-Agent':'Repaintko/6.1.1','Accept':'image/*'})
        started=time.monotonic()
        with build_opener(WebRedirects()).open(request,timeout=10) as response:
            length=response.headers.get('Content-Length')
            if length and int(length)>MAX_DOWNLOAD:raise ValueError('Das Bild ist größer als 40 MB.')
            stream=io.BytesIO()
            while True:
                if cancel.is_set():raise ValueError('Download abgebrochen.')
                if time.monotonic()-started>30:raise ValueError('Das Laden des Bildes dauert zu lange.')
                block=response.read(65536)
                if not block:break
                if stream.tell()+len(block)>MAX_DOWNLOAD:raise ValueError('Das Bild ist größer als 40 MB.')
                stream.write(block)
            data=stream.getvalue()
    if len(data)>MAX_DOWNLOAD:raise ValueError('Das Bild ist größer als 40 MB.')
    if cancel.is_set():raise ValueError('Download abgebrochen.')
    try:return load_image(io.BytesIO(data))
    except Exception as exc:
        raise ValueError('Die Adresse liefert kein lesbares Bild. Ziehe das Bild selbst statt der Webseite. Bei geschützten Bildern hilft „Bild kopieren“ im Browser und Strg+V.') from exc
