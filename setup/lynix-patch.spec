# PyInstaller bundles Python/GTK; no UI.exe, Windows DLL, prefix or user config.
import os
from pathlib import Path
project=Path(SPECPATH).parent
build=Path(os.environ['LYNIX_BUILD_ROOT'])
a=Analysis([str(project/'setup/main.py')],pathex=[str(project/'setup')],
           binaries=[],datas=[(str(build/'payload'),'payload')],
           hiddenimports=['ctypes.util','gi.repository.GdkPixbuf','gi.repository.Gdk','gi.repository.Gtk'],
           hooksconfig={'gi':{'icons':['Adwaita'],'themes':['Adwaita'],'languages':['en_US','en_GB'],
                              'module-versions':{'Gtk':'3.0','Gdk':'3.0'}}},
           excludes=['tkinter','pytest','unittest'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='lynix-patch',debug=False,strip=False,upx=False,console=True)
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='lynix-patch')
