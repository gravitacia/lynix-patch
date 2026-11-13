#!/usr/bin/env python3
"""Prepare the source-only payload and assemble a standard type-2 AppImage."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request

PROJECT=Path(__file__).resolve().parents[1]
BUILD=PROJECT/'.build/appimage'
RUNTIME_URL='https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64'
RUNTIME_SHA='617aa77314d57c8b8e4fae9c3f0b35af7b30d5529cb69e98f64f92510ed98a46'
CRATE_SHA='319b99243f88f9fd7cc338135241d91b711be88fb2ce2a4a3ee0fb09ae283d05'


def fetch(url,path,sha):
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==sha:return
    path.parent.mkdir(parents=True,exist_ok=True)
    with urllib.request.urlopen(url,timeout=60) as response:
        data=response.read()
    if hashlib.sha256(data).hexdigest()!=sha:raise ValueError(f'Build dependency checksum mismatch: {path.name}')
    path.write_bytes(data)


def prepare():
    payload=BUILD/'payload'
    if payload.exists():shutil.rmtree(payload)
    payload.mkdir(parents=True)
    def copy(source,dest):
        dest=payload/dest;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PROJECT/source,dest)
    copy('lynix-proton.sh','lynix-proton.sh')
    copy('LICENSE','licenses/Lynix-MIT.txt')
    for name in ('prepare-proton.py','cursor-visibility.py','roblox-compression.py'):
        copy('compat/'+name,'compat/'+name)
    copy('compat/lynrtl/lynrtl.dll','compat/lynrt.dll')
    copy('compat/cursor/cursor-state.exe','compat/cursor-state.exe')
    copy('setup/assets/lynix-patch.svg','setup/assets/lynix-patch.svg')
    deps=PROJECT/'.build/deps'
    fetch(RUNTIME_URL,deps/'runtime-x86_64',RUNTIME_SHA)
    fetch('https://static.crates.io/crates/ms-compress/ms-compress-0.2.1.crate',deps/'ms-compress-0.2.1.crate',CRATE_SHA)
    (payload/'sources').mkdir()
    shutil.copy2(deps/'ms-compress-0.2.1.crate',payload/'sources/ms-compress-0.2.1.crate')
    # Supply the exact helper source and relinking instructions alongside the DLL.
    with tarfile.open(payload/'sources/lynix-patch-source.tar.gz','w:gz') as archive:
        for file in sorted(PROJECT.rglob('*')):
            relative=file.relative_to(PROJECT)
            if any(part in {'.git','.build','.build-venv','target','.cargo','__pycache__','dist'} for part in relative.parts):continue
            if file.is_file() and (file.suffix in {'.py','.sh','.c','.rs','.toml','.lock','.def','.md','.spec','.svg'} or file.name in {'LICENSE','AppImage.Dockerfile'}):
                archive.add(file,arcname=str(relative))
    (payload/'licenses/THIRD-PARTY.txt').write_text('''Lynix-patch is based on Lynix by alloc-nullptr, distributed by synapzis.\nOriginal: https://github.com/synapzis/lynix\nUpstream: https://github.com/alloc-nullptr/lynix\nOriginal MIT notice: Lynix-MIT.txt.\n\nXPRESS Huffman implementation: ms-compress 0.2.1 by CaddyGlow, based on\nwimlib by Eric Biggers (LGPL-2.1-or-later); other crate portions carry the\nnotices declared in its Cargo.toml and source files. Exact dependency source\nand the helper build source are provided in ../sources/ for rebuilding and\nrelinking. https://github.com/CaddyGlow/ms-compress\n\nThe setup runtime bundles Python (PSF), PyGObject (LGPL), GTK/GLib (LGPL),\nPyInstaller (GPL with bootloader exception), and their Linux dependencies.\nLibrary copyright notices are included under this directory.\nAppImage runtime: https://github.com/AppImage/type2-runtime (MIT).\nNo UI.exe, Roblox binary, proprietary Windows DLL, prefix, or user\nconfiguration is bundled. Microsoft components download at setup time.\n''')
    for source,name in [('https://raw.githubusercontent.com/AppImage/type2-runtime/main/LICENSE','AppImage-runtime.txt'),
                        ('https://raw.githubusercontent.com/python/cpython/3.10/LICENSE','Python.txt')]:
        with urllib.request.urlopen(source,timeout=30) as response:(payload/'licenses'/name).write_bytes(response.read())
    # Include local system notices; the builder adds its matching library notices too.
    identity=hashlib.sha256()
    for file in sorted(payload.rglob('*')):
        if file.is_file():identity.update(str(file.relative_to(payload)).encode()+file.read_bytes())
    (payload/'build-id').write_text(identity.hexdigest()+'\n')
    print('Prepared payload:',payload)


def package():
    appdir=BUILD/'Lynix-patch.AppDir'
    if appdir.exists():shutil.rmtree(appdir)
    destination=appdir/'usr/lib/lynix-patch'
    destination.parent.mkdir(parents=True)
    shutil.copytree(BUILD/'frozen/lynix-patch',destination,symlinks=True)
    (appdir/'AppRun').write_text('#!/bin/sh\nset -eu\nappdir="${APPDIR:-$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)}"\nexec "$appdir/usr/lib/lynix-patch/lynix-patch" "$@"\n')
    (appdir/'AppRun').chmod(0o755)
    icon=PROJECT/'setup/assets/lynix-patch.svg'
    shutil.copy2(icon,appdir/'lynix-patch.svg')
    (appdir/'.DirIcon').symlink_to('lynix-patch.svg')
    (appdir/'lynix-patch.desktop').write_text('''[Desktop Entry]
Type=Application
Name=Lynix-patch
Comment=Set up Lynx on Linux
Exec=lynix-patch
Icon=lynix-patch
Terminal=false
Categories=Utility;Game;
''')
    # Reject accidental proprietary payloads before producing the distributable.
    for file in appdir.rglob('*'):
        if file.name.lower()=='ui.exe' or file.name.lower()=='cabinet.dll' or file.name.lower().startswith('robloxplayer'):
            raise ValueError(f'Unexpected proprietary payload: {file}')
    squash=BUILD/'payload.squashfs'
    subprocess.run(['mksquashfs',str(appdir),str(squash),'-noappend','-root-owned','-comp','zstd','-processors','2','-mkfs-time','0','-all-time','0'],check=True)
    runtime=PROJECT/'.build/deps/runtime-x86_64'
    if hashlib.sha256(runtime.read_bytes()).hexdigest()!=RUNTIME_SHA:raise ValueError('Runtime checksum mismatch')
    dist=PROJECT/'dist';dist.mkdir(exist_ok=True)
    image=dist/'Lynix-patch-Setup-x86_64.AppImage'
    with image.open('wb') as out:
        for part in (runtime,squash):
            with part.open('rb') as stream:shutil.copyfileobj(stream,out)
    image.chmod(0o755)
    sha=hashlib.sha256(image.read_bytes()).hexdigest()
    image.with_suffix('.AppImage.sha256').write_text(sha+'  '+image.name+'\n')
    print('Built:',image)
    print('SHA-256:',sha)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','package']);args=p.parse_args()
    (prepare if args.stage=='prepare' else package)()
