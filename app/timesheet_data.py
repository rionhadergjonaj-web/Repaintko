"""Read-only Bbc timesheet adapter and explicit, minute-based departure estimates."""
import re
from datetime import datetime, timedelta
from urllib.parse import urlsplit

URL = 'https://extranet.bbcag.ch/timesheet/record'
LEGACY = 'https://legacy.extranet.bbcag.ch/timesheet/record'

def is_record_url(url):
    u = urlsplit(url)
    return u.scheme == 'https' and u.hostname in ('extranet.bbcag.ch', 'legacy.extranet.bbcag.ch') and u.port in (None, 443) and u.path.rstrip('/') == '/timesheet/record' and not u.username

# Only rendered timesheet fields; no credentials, cookies or hidden application state.
READ_TIMESHEET = r'''(()=>{
if(!['https://extranet.bbcag.ch','https://legacy.extranet.bbcag.ch'].includes(location.origin)||location.pathname.replace(/\/$/,'')!='/timesheet/record')return '';
const date=document.getElementById('timegraph_work_hours_form_date');
const summary=document.getElementById('time_summary');
if(!date||!summary)return '';
const balances={};
for(const box of summary.querySelectorAll('.timesheet-balance')){
 const label=box.querySelector('[id=account_title]');const amount=box.querySelector('[id=account_time] > div');
 if(label&&amount)balances[label.textContent.trim()]=amount.textContent.trim();
}
const starts=[...document.querySelectorAll('input[id^="working_hours_collection_records_"][id$="_start"]')];
let dirty=false;
const rows=starts.map(start=>{const stop=document.getElementById(start.id.replace(/_start$/,'_stop'));
 if(start.value!==start.defaultValue||(stop&&stop.value!==stop.defaultValue))dirty=true;
 return [start.value,stop?stop.value:''];});
for(const e of document.querySelectorAll('input[id^="working_hours_collection_"],input[id^="absence_collection_"],textarea[id^="working_hours_collection_"],textarea[id^="absence_collection_"]')){
 if(e.type!=='hidden'&&e.value!==e.defaultValue)dirty=true;
}
const absence=[...document.querySelectorAll('select[id^="absence_collection_records_"][id$="_recordType"]')].some(e=>e.value&&!['0',''].includes(e.value));
return JSON.stringify({url:location.href,date:date.textContent.trim(),balances,rows,dirty,absence});})()'''

MONTHS = ['januar','februar','märz','april','mai','juni','juli','august','september','oktober','november','dezember']

def minutes(text, signed=False):
    match = re.fullmatch(r'([+\-−]?)(\d{1,4}):([0-5]\d)', str(text).strip())
    if not match or (not signed and (match[1] or int(match[2]) > 23)):
        raise ValueError('Ungültige Zeitangabe.')
    return (-1 if match[1] in ('-', '−') else 1) * (int(match[2])*60+int(match[3]))

def parse_day(text):
    match = re.search(r'(\d{1,2})\.\s*([A-Za-zäÄ]+)\s+(\d{4})', text)
    if not match or match[2].lower() not in MONTHS:raise ValueError('Datum nicht erkannt.')
    return datetime(int(match[3]), MONTHS.index(match[2].lower())+1, int(match[1])).date()

def calculate(data, now, basis='unknown', balance_text='', snapshot_at=None):
    """basis: prior = balance before today, live = balance including work at now.

    Future work includes any missing part of the requested 30-minute minimum break.
    Longer recorded breaks count in full. Closed sessions
    do not invent a return time. Unknown balance semantics never yield a fake time.
    """
    if not is_record_url(data.get('url','')):raise ValueError('Keine Bbc-Zeiterfassung.')
    if parse_day(data.get('date','')) != now.date():raise ValueError('Bitte den heutigen Tag auswählen.')
    if data.get('dirty'):raise ValueError('Geänderte Formularfelder: zuerst im Extranet prüfen und neu laden.')
    if data.get('absence'):raise ValueError('Tag mit Fehlzeit: automatische Berechnung ausgesetzt.')
    now_min = now.hour*60+now.minute
    total=0;last_end=0;opened=False;count=0;pause=0;open_minutes=0
    for start,stop in data.get('rows',[]):
        if not start and not stop:continue
        if not start:raise ValueError('Buchung ohne Beginn.')
        a=minutes(start);b=minutes(stop) if stop else now_min
        if opened or a<last_end or b<a or b>now_min:raise ValueError('Überlappende oder zukünftige Buchungen.')
        if count:pause+=a-last_end
        total+=b-a;last_end=b;opened=not bool(stop);count+=1
        if opened:open_minutes=b-a
    if not count:raise ValueError('Heute noch keine Arbeitszeit erfasst.')
    if not opened:pause+=now_min-last_end
    pause_missing=max(0,30-pause)
    remaining=492-total
    zero=None
    if basis=='prior':zero=492-minutes(balance_text,True)-total
    elif basis=='badge':zero=-minutes(balance_text,True)-open_minutes
    elif basis=='live':
        elapsed=max(0,int((now-snapshot_at).total_seconds()//60)) if opened and snapshot_at else 0
        zero=-minutes(balance_text,True)-elapsed
    elif basis!='unknown':raise ValueError('Unbekannte Saldo-Grundlage.')
    def target(left):
        if left is None:return 'Grundlage wählen'
        if left<=0 and not pause_missing:return 'bereits erreicht'
        if not opened:
            work=max(0,left)
            return f'noch {work//60}:{work%60:02d} Arbeit'+(f' + {pause_missing} min Pause' if pause_missing else '')
        end=now.replace(second=0,microsecond=0)+timedelta(minutes=max(0,left)+pause_missing)
        days=(end.date()-now.date()).days
        return end.strftime('%H:%M')+(f' (+{days} '+('Tag)' if days==1 else 'Tage)') if days else '')
    return dict(daily=target(remaining),zero=target(zero),worked=total,open=opened,pause=pause,pause_missing=pause_missing,open_minutes=open_minutes)
