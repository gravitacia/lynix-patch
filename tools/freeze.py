#!/usr/bin/env python3
"""Run inside the Ubuntu build container and preserve dependency notices."""
import importlib.metadata
import os
from pathlib import Path
import shutil
import PyInstaller.__main__

build=Path(os.environ['LYNIX_BUILD_ROOT'])
notices=build/'payload/licenses/system'
notices.mkdir(parents=True,exist_ok=True)
for file in Path('/usr/share/doc').glob('*/copyright'):
    if file.is_file():
        shutil.copy2(file,notices/(file.parent.name+'.txt'))
for name in ('PyInstaller','pyinstaller-hooks-contrib','altgraph','packaging'):
    dist=importlib.metadata.distribution(name)
    for relative in dist.files or []:
        if 'license' in str(relative).lower() or 'copying' in str(relative).lower():
            file=Path(dist.locate_file(relative))
            if file.is_file():shutil.copy2(file,notices/(name+'-'+file.name))
PyInstaller.__main__.run(['--noconfirm','--clean','--distpath',str(build/'frozen'),
                         '--workpath',str(build/'pyinstaller'),'/project/setup/lynix-patch.spec'])
