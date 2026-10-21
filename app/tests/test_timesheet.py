import unittest
from datetime import datetime,timedelta
from timesheet_data import calculate,minutes,is_record_url,URL

def fixture():
    return dict(url=URL,date='Donnerstag, 15. Oktober 2026',rows=[['08:00','12:00'],['12:30','']],dirty=False,absence=False,balances={'Gleitzeit Saldo':'-02:00','Gleitzeit aktuell':'-01:00'})

class CalculatorTests(unittest.TestCase):
    def test_badge_out_balance_does_not_drift_on_reload(self):
        d=fixture();d['rows']=[['07:30','11:30'],['12:00','']]
        for hour in (12,13,14,15):
            self.assertEqual(calculate(d,datetime(2026,10,15,hour),'badge','-04:00')['zero'],'16:00')
        self.assertEqual(calculate(d,datetime(2026,10,15,16),'badge','-04:00')['zero'],'bereits erreicht')
        d['rows']=[['12:00','']]
        self.assertEqual(calculate(d,datetime(2026,10,15,14),'badge','-04:00')['zero'],'16:30')
        d['rows']=[['07:30','11:30'],['12:00','14:00'],['15:00','']]
        self.assertEqual(calculate(d,datetime(2026,10,15,16),'badge','-02:00')['zero'],'17:00')
    def test_daily_and_prior_balance(self):
        result=calculate(fixture(),datetime(2026,10,15,14), 'prior','-02:00')
        self.assertEqual(result['daily'],'16:42');self.assertEqual(result['zero'],'18:42')
        self.assertEqual(calculate(fixture(),datetime(2026,10,15,15))['daily'],'16:42')
    def test_live_balance_is_not_counted_twice(self):
        self.assertEqual(calculate(fixture(),datetime(2026,10,15,14),'live','-02:00')['zero'],'16:00')
        self.assertEqual(calculate(fixture(),datetime(2026,10,15,14))['zero'],'Grundlage wählen')
    def test_pause_and_targets_already_reached(self):
        d=fixture();d['rows'][1][1]='14:00'
        self.assertEqual(calculate(d,datetime(2026,10,15,15))['daily'],'noch 2:42 Arbeit')
        self.assertEqual(calculate(fixture(),datetime(2026,10,15,17))['daily'],'bereits erreicht')
        self.assertEqual(calculate(d,datetime(2026,10,15,15),'prior','+10:00')['zero'],'bereits erreicht')
    def test_invalid_records_dates_and_absences(self):
        for extra in [dict(date='Mittwoch, 14. Oktober 2026'),dict(dirty=True),dict(absence=True),dict(rows=[['12:00','11:00']]),dict(rows=[['08:00','12:00'],['11:30','']]),dict(rows=[['08:00',''],['12:30','']]),dict(rows=[['','11:00']]),dict(rows=[])]:
            d=fixture();d.update(extra)
            with self.subTest(extra=extra),self.assertRaises(ValueError):calculate(d,datetime(2026,10,15,14))
    def test_exact_origin_and_input_validation(self):
        for url in ['http://extranet.bbcag.ch/timesheet/record','https://extranet.bbcag.ch.evil.test/timesheet/record','https://extranet.bbcag.ch:444/timesheet/record','https://user@extranet.bbcag.ch/timesheet/record']:
            self.assertFalse(is_record_url(url))
        for text in ['25:00','12:60','-02:00']:
            with self.assertRaises(ValueError):minutes(text)
        self.assertEqual(minutes('−02:15',True),-135)
    def test_next_day(self):
        self.assertEqual(calculate(fixture(),datetime(2026,10,15,14),'prior','-10:00')['zero'],'02:42 (+1 Tag)')
    def test_minimum_pause_and_longer_pause(self):
        d=fixture();d['rows']=[['08:00','']]
        r=calculate(d,datetime(2026,10,15,14),'prior','-02:00')
        self.assertEqual(r['daily'],'16:42');self.assertEqual(r['zero'],'18:42');self.assertEqual(r['pause_missing'],30)
        d['rows']=[['08:00','12:00'],['12:10','']]
        r=calculate(d,datetime(2026,10,15,14));self.assertEqual(r['daily'],'16:42');self.assertEqual(r['pause_missing'],20)
        d['rows'][1][0]='13:00'
        r=calculate(d,datetime(2026,10,15,14));self.assertEqual(r['daily'],'17:12');self.assertEqual(r['pause_missing'],0)
        d['rows']=[['08:00','12:00']]
        r=calculate(d,datetime(2026,10,15,12,15));self.assertEqual(r['pause_missing'],15);self.assertEqual(r['daily'],'noch 4:12 Arbeit + 15 min Pause')

class WidgetTests(unittest.TestCase):
    def test_stale_generation_modes_and_privacy(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QSettings
        from timesheet_ui import TimesheetWidget
        import tempfile,json
        from pathlib import Path
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            settings=QSettings(str(Path(folder)/'test.ini'),QSettings.Format.IniFormat)
            w=TimesheetWidget(settings,None);w.set_enabled(True)
            w.loaded_at=datetime.now().replace(hour=14,minute=0)
            d=fixture();d['date']=f'{w.loaded_at.day}. '+['Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember'][w.loaded_at.month-1]+f' {w.loaded_at.year}'
            w.received(json.dumps(d),99);self.assertIsNone(w.data)
            w.loaded_at=datetime.now();w.received(json.dumps(d),w.generation)
            self.assertIsNotNone(w.data)
            w.loaded_at=datetime.now()-timedelta(minutes=4);w.render();self.assertIn('veraltet',w.label.text())
            w.set_enabled(False);w.received(json.dumps(d),w.generation);self.assertIsNone(w.data)
            self.assertNotIn('-02:00',str(settings.allKeys()));w.shutdown();w.deleteLater()
