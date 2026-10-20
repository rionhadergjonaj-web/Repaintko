"""Register a browser candidate; Windows keeps the user's default choice."""
import sys,os
from pathlib import Path

def registration_values(executable):
    exe=str(Path(executable).resolve());app=r'Software\Clients\StartMenuInternet\Repaintko';caps=app+r'\Capabilities';prog=r'Software\Classes\Repaintko.URL'
    return [(app,'','Repaintko'),(app+r'\DefaultIcon','',exe+',0'),(app+r'\shell\open\command','','"'+exe+'" --browser'),
            (caps,'ApplicationName','Repaintko'),(caps,'ApplicationDescription','ReBrowko – der Browser in Repaintko'),
            (caps+r'\URLAssociations','http','Repaintko.URL'),(caps+r'\URLAssociations','https','Repaintko.URL'),
            (r'Software\RegisteredApplications','Repaintko',caps),(prog,'','Repaintko Webadresse'),(prog,'URL Protocol',''),
            (prog+r'\DefaultIcon','',exe+',0'),(prog+r'\shell\open\command','','"'+exe+'" --browser "%1"')]

def register(open_settings=True):
    if not getattr(sys,'frozen',False):raise ValueError('Bitte die installierte Repaintko.exe verwenden, um Repaintko als Browser anzumelden.')
    import winreg,ctypes
    for path,name,value in registration_values(sys.executable):
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,path) as key:winreg.SetValueEx(key,name,0,winreg.REG_SZ,value)
    ctypes.windll.shell32.SHChangeNotify(0x08000000,0,None,None)
    if open_settings:os.startfile('ms-settings:defaultapps')
