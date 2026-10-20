"""Build a native MSI with embedded cabinet using the Windows Installer API."""
import ctypes as c
from ctypes import wintypes as w
from pathlib import Path
import uuid,subprocess,json,hashlib,re
from msi_ui import add_ui

root=Path(__file__).resolve().parents[1]
payload=root/'dist/Repaintko'
output=root/'outputs/Repaintko-Setup-13.1.0.msi'
api=c.WinDLL('msi')
H=w.UINT
def bind(name,args,ret=w.UINT):
    fn=getattr(api,name);fn.argtypes=args;fn.restype=ret;return fn
open_db=bind('MsiOpenDatabaseW',[w.LPCWSTR,c.c_void_p,c.POINTER(H)])
open_view=bind('MsiDatabaseOpenViewW',[H,w.LPCWSTR,c.POINTER(H)])
execute=bind('MsiViewExecute',[H,H]);close=bind('MsiCloseHandle',[H])
record=bind('MsiCreateRecord',[w.UINT],H)
setstr=bind('MsiRecordSetStringW',[H,w.UINT,w.LPCWSTR])
setint=bind('MsiRecordSetInteger',[H,w.UINT,c.c_int])
setstream=bind('MsiRecordSetStreamW',[H,w.UINT,w.LPCWSTR])
commit=bind('MsiDatabaseCommit',[H])
summary=bind('MsiGetSummaryInformationW',[H,w.LPCWSTR,w.UINT,c.POINTER(H)])
sumset=bind('MsiSummaryInfoSetPropertyW',[H,w.UINT,w.UINT,c.c_int,c.c_void_p,w.LPCWSTR])
sumpersist=bind('MsiSummaryInfoPersist',[H])
def check(code):
    if code:raise RuntimeError(f'Windows Installer API error {code}')
db=H();check(open_db(str(output),c.c_void_p(3),c.byref(db)))
def sql(query,values=()):
    view=H();check(open_view(db,query,c.byref(view)))
    rec=record(len(values)) if values else H(0)
    try:
        for i,value in enumerate(values,1):
            if value is None:continue
            if isinstance(value,Path):check(setstream(rec,i,str(value)))
            elif isinstance(value,int):check(setint(rec,i,value))
            else:check(setstr(rec,i,str(value)))
        check(execute(view,rec))
    finally:
        if rec:close(rec)
        close(view)
columns_by_table={'_Streams':['Name','Data']}
def table(name,columns,key):
    sql(f'CREATE TABLE `{name}` ({columns} PRIMARY KEY {key})')
    columns_by_table[name]=re.findall(r'`([^`]+)`',columns)
def add(name,*values):
    columns=','.join('`'+col+'`' for col in columns_by_table[name])
    sql(f'INSERT INTO `{name}` ({columns}) VALUES ({",".join("?" for _ in values)})',values)
def guid(value):return '{'+str(uuid.uuid5(uuid.NAMESPACE_URL,'repainko.app/'+value)).upper()+'}'

table('Property','`Property` CHAR(72) NOT NULL, `Value` CHAR(0) NOT NULL','`Property`')
properties={'ProductCode':guid('product/13.1.0'),'UpgradeCode':guid('upgrade'),
 'ProductName':'Repaintko','ProductVersion':'13.1.0','ProductLanguage':'1031',
 'Manufacturer':'Repaintko','ALLUSERS':'1','INSTALLLEVEL':'1',
 'ARPNOMODIFY':'1','ARPPRODUCTICON':'RepainkoIcon','ARPHELPLINK':'',
 'SecureCustomProperties':'OLDPRODUCTS;NEWERPRODUCTS;INSTALLDIR;ACCEPTTERMS','MSIRESTARTMANAGERCONTROL':'DisableShutdown'}
for key,value in properties.items():
    if value:add('Property',key,value)
table('Directory','`Directory` CHAR(72) NOT NULL, `Directory_Parent` CHAR(72), `DefaultDir` CHAR(255) NOT NULL','`Directory`')
for row in [('TARGETDIR',None,'SourceDir'),('ProgramFiles64Folder','TARGETDIR','.'),
            ('INSTALLDIR','ProgramFiles64Folder','Repaintko'),('DesktopFolder','TARGETDIR','.'),
            ('ProgramMenuFolder','TARGETDIR','.'),('AppMenu','ProgramMenuFolder','Repaintko')]:add('Directory',*row)
dirs={Path('.'):'INSTALLDIR'}
for path in sorted((p for p in payload.rglob('*') if p.is_dir()),key=lambda p:(len(p.parts),str(p))):
    rel=path.relative_to(payload);key='D'+hashlib.sha1(str(rel).encode()).hexdigest()[:20]
    dirs[rel]=key;add('Directory',key,dirs[rel.parent],path.name)
table('Component','`Component` CHAR(72) NOT NULL, `ComponentId` CHAR(38), `Directory_` CHAR(72) NOT NULL, `Attributes` SHORT NOT NULL, `Condition` CHAR(255), `KeyPath` CHAR(72)','`Component`')
table('Feature','`Feature` CHAR(38) NOT NULL, `Feature_Parent` CHAR(38), `Title` CHAR(64), `Description` CHAR(255), `Display` SHORT, `Level` SHORT NOT NULL, `Directory_` CHAR(72), `Attributes` SHORT NOT NULL','`Feature`')
add('Feature','Main',None,'Repaintko','Bildbearbeitung mit 27 Zensurpinseln',1,1,'INSTALLDIR',0)
table('FeatureComponents','`Feature_` CHAR(38) NOT NULL, `Component_` CHAR(72) NOT NULL','`Feature_`, `Component_`')
table('File','`File` CHAR(72) NOT NULL, `Component_` CHAR(72) NOT NULL, `FileName` CHAR(255) NOT NULL, `FileSize` LONG NOT NULL, `Version` CHAR(72), `Language` CHAR(20), `Attributes` SHORT, `Sequence` LONG NOT NULL','`File`')
files=sorted(p for p in payload.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
keys={}
ddf=['.OPTION EXPLICIT','.Set Cabinet=on','.Set Compress=on','.Set CompressionType=MSZIP',
     '.Set MaxDiskSize=0','.Set CabinetNameTemplate=Repainko1310.cab',f'.Set DiskDirectoryTemplate="{root / "work"}"']
getver=bind('MsiGetFileVersionW',[w.LPCWSTR,w.LPWSTR,c.POINTER(w.DWORD),w.LPWSTR,c.POINTER(w.DWORD)])
manifest={};folder_bytes=0
for i,path in enumerate(files,1):
    rel=path.relative_to(payload);key=f'F{i:04}';component=f'C{i:04}';keys[rel.as_posix()]=(key,component)
    add('Component',component,guid('component/'+rel.as_posix()),dirs[rel.parent],256,None,key)
    add('FeatureComponents','Main',component)
    version=c.create_unicode_buffer(256);length=w.DWORD(256)
    status=getver(str(path),version,c.byref(length),None,None)
    add('File',key,component,path.name,path.stat().st_size,version.value if status==0 else None,None,512,i)
    if folder_bytes and folder_bytes+path.stat().st_size>512*1024**2:ddf.append('.New Folder');folder_bytes=0
    ddf.append(f'"{path}" {key}');folder_bytes+=path.stat().st_size
    manifest[rel.as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
ddfpath=root/'work/repainko1310.ddf';ddfpath.write_text('\n'.join(ddf),encoding='cp1252')
with (root/'work/makecab1310.log').open('w') as log:subprocess.run(['makecab.exe','/V1','/F',str(ddfpath)],cwd=root/'work',check=True,stdout=log,stderr=subprocess.STDOUT)
table('Media','`DiskId` SHORT NOT NULL, `LastSequence` LONG NOT NULL, `DiskPrompt` CHAR(64), `Cabinet` CHAR(255), `VolumeLabel` CHAR(32), `Source` CHAR(72)','`DiskId`')
add('Media',1,len(files),None,'#Repainko1310.cab',None,None)
add('_Streams','Repainko1310.cab',root/'work/Repainko1310.cab')
table('Icon','`Name` CHAR(72) NOT NULL, `Data` OBJECT NOT NULL','`Name`');add('Icon','RepainkoIcon',payload/'_internal/assets/repaintko-free.ico')
table('Shortcut','`Shortcut` CHAR(72) NOT NULL, `Directory_` CHAR(72) NOT NULL, `Name` CHAR(128) NOT NULL, `Component_` CHAR(72) NOT NULL, `Target` CHAR(255) NOT NULL, `Arguments` CHAR(255), `Description` CHAR(255), `Hotkey` SHORT, `Icon_` CHAR(72), `IconIndex` SHORT, `ShowCmd` SHORT, `WkDir` CHAR(72)','`Shortcut`')
pykey,pycomp=keys['Repaintko.exe']
table('Registry','`Registry` CHAR(72) NOT NULL, `Root` SHORT NOT NULL, `Key` CHAR(255) NOT NULL, `Name` CHAR(255), `Value` CHAR(0), `Component_` CHAR(72) NOT NULL','`Registry`')
add('Registry','InstallLocation',2,r'Software\Repainko','InstallDir','[INSTALLDIR]',pycomp)

# Advertise browser capabilities without changing the user's selected defaults.
base=r'Software\Clients\StartMenuInternet\Repaintko'
cap=base+r'\Capabilities'
prog=r'Software\Classes\Repaintko.URL'
browser_values=[(base,'','Repaintko'),(base+r'\shell\open\command','','"[#'+pykey+']" --browser'),
 (cap,'ApplicationName','Repaintko'),(cap,'ApplicationDescription','ReBrowko in Repaintko'),
 (cap+r'\URLAssociations','http','Repaintko.URL'),(cap+r'\URLAssociations','https','Repaintko.URL'),
 (r'Software\RegisteredApplications','Repaintko',cap),(prog,'','Repaintko Webadresse'),(prog,'URL Protocol',''),
 (prog+r'\shell\open\command','','"[#'+pykey+']" --browser "%1"')]
for i,(key,name,value) in enumerate(browser_values):add('Registry','Browser'+str(i),2,key,name,value,pycomp)

table('RegLocator','`Signature_` CHAR(72) NOT NULL, `Root` SHORT NOT NULL, `Key` CHAR(255) NOT NULL, `Name` CHAR(255), `Type` SHORT','`Signature_`')
table('Signature','`Signature` CHAR(72) NOT NULL, `FileName` CHAR(255) NOT NULL, `MinVersion` CHAR(20), `MaxVersion` CHAR(20), `MinSize` LONG, `MaxSize` LONG, `MinDate` LONG, `MaxDate` LONG, `Languages` CHAR(255)','`Signature`')
add('RegLocator','PreviousFolder',2,r'Software\Repainko','InstallDir',18)
table('AppSearch','`Property` CHAR(72) NOT NULL, `Signature_` CHAR(72) NOT NULL','`Property`, `Signature_`')
add('AppSearch','INSTALLDIR','PreviousFolder')
table('CustomAction','`Action` CHAR(72) NOT NULL, `Type` SHORT NOT NULL, `Source` CHAR(72), `Target` CHAR(255)','`Action`')
add('CustomAction','RequireTerms',19,None,'Bitte die Nutzungsbedingungen akzeptieren, bevor du Repaintko installierst.')
add('CustomAction','RecordLocation',51,'ARPINSTALLLOCATION','[INSTALLDIR]')
add_ui(table,add,root)
for key,directory in [('DesktopShortcut','DesktopFolder'),('StartShortcut','AppMenu')]:
    add('Shortcut',key,directory,'Repaintko',pycomp,f'[#{pykey}]',None,'Repaintko Bildbearbeitung',None,'RepainkoIcon',0,1,'INSTALLDIR')
table('RemoveFile','`FileKey` CHAR(72) NOT NULL, `Component_` CHAR(72) NOT NULL, `FileName` CHAR(255), `DirProperty` CHAR(72) NOT NULL, `InstallMode` SHORT NOT NULL','`FileKey`')
add('RemoveFile','RemoveAppMenu',pycomp,None,'AppMenu',2)
table('Upgrade','`UpgradeCode` CHAR(38) NOT NULL, `VersionMin` CHAR(20), `VersionMax` CHAR(20), `Language` CHAR(255), `Attributes` LONG NOT NULL, `Remove` CHAR(255), `ActionProperty` CHAR(72) NOT NULL','`UpgradeCode`, `VersionMin`, `VersionMax`, `Language`, `Attributes`')
add('Upgrade',properties['UpgradeCode'],None,'13.1.0',None,513,None,'OLDPRODUCTS')
add('Upgrade',properties['UpgradeCode'],'13.1.0',None,None,2,None,'NEWERPRODUCTS')
table('LaunchCondition','`Condition` CHAR(255) NOT NULL, `Description` CHAR(255) NOT NULL','`Condition`')
add('LaunchCondition','VersionNT64','Repaintko benoetigt Windows 64 Bit.')
add('LaunchCondition','NOT NEWERPRODUCTS','Eine neuere Repaintko-Version ist bereits installiert.')
sequence=[('FindRelatedProducts',25),('AppSearch',50),('LaunchConditions',100),('CostInitialize',800),('FileCost',900),('CostFinalize',1000),('RequireTerms',1050),('RecordLocation',1060),
 ('InstallValidate',1400),('InstallInitialize',1500),('RemoveExistingProducts',1510),('ProcessComponents',1600),
 ('UnpublishFeatures',1800),('RemoveRegistryValues',2600),('RemoveShortcuts',3200),('RemoveFiles',3500),('RemoveFolders',3600),('CreateFolders',3700),('InstallFiles',4000),('CreateShortcuts',4500),('WriteRegistryValues',5000),
 ('RegisterUser',6000),('RegisterProduct',6100),('PublishFeatures',6300),('PublishProduct',6400),('InstallFinalize',6600)]
for name in ('InstallExecuteSequence','InstallUISequence','AdminExecuteSequence'):
    table(name,'`Action` CHAR(72) NOT NULL, `Condition` CHAR(255), `Sequence` SHORT','`Action`')
for action,seq in sequence:
    condition={'RemoveExistingProducts':'OLDPRODUCTS','RequireTerms':'NOT Installed AND NOT OLDPRODUCTS AND ACCEPTTERMS <> "1"'}.get(action)
    add('InstallExecuteSequence',action,condition,seq)
for action,seq in [('FindRelatedProducts',25),('AppSearch',50),('LaunchConditions',100),('CostInitialize',800),('FileCost',900),('CostFinalize',1000),
                   ('SetupDlg',1200),('MaintenanceDlg',1201),('UpgradeDlg',1202),('ProgressDlg',1290),('ExecuteAction',1300),('CompleteDlg',-1),('FailedDlg',-3)]:
    condition={'SetupDlg':'NOT Installed AND NOT OLDPRODUCTS','MaintenanceDlg':'Installed AND NOT REMOVE',
               'UpgradeDlg':'NOT Installed AND OLDPRODUCTS','CompleteDlg':'NOT REMOVE'}.get(action)
    add('InstallUISequence',action,condition,seq)
for action,seq in [('CostInitialize',800),('FileCost',900),('CostFinalize',1000),('InstallValidate',1400),('InstallInitialize',1500),('InstallAdminPackage',3900),('InstallFiles',4000),('InstallFinalize',6600)]:add('AdminExecuteSequence',action,None,seq)
info=H();check(summary(db,None,20,c.byref(info)))
for prop,value in {1:1252,2:'Repaintko Setup',3:'Repaintko 13.1.0',4:'Repaintko',7:'x64;1031',9:'{'+str(uuid.uuid4()).upper()+'}',14:500,15:2,18:'Repaintko MSI Builder',19:2}.items():
    check(sumset(info,prop,3 if isinstance(value,int) else 30,value if isinstance(value,int) else 0,None,value if isinstance(value,str) else None))
check(sumpersist(info));close(info);check(commit(db));close(db)
(root/'work/msi-manifest1310.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(output,round(output.stat().st_size/1024**2,1),'MiB;',len(files),'files')
