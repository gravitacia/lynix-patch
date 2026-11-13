import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend import (Cancelled, Installer, Layout, checksum, detect_prefix,
                     discover_proton, proton_name, quote_desktop, vc_present,
                     webview_present)


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.layout=Layout.isolated(self.root/'home')
        self.payload=self.root/'payload'

    def tearDown(self):
        self.temp.cleanup()

    def proton(self,path,name):
        path.mkdir(parents=True)
        (path/'proton').write_text('#!/bin/sh\nexit 0\n');(path/'proton').chmod(0o755)
        (path/'files').mkdir();(path/'version').write_text('123 '+name)
        return path

    def prefix(self,path):
        pfx=path/'pfx';(pfx/'drive_c').mkdir(parents=True)
        (pfx/'system.reg').write_text('[Software\\\\Microsoft\\\\VisualStudio\\\\14.0\\\\VC\\\\Runtimes\\\\x64]\n"Version"="v14.52.37029.00"\n')
        web=pfx/'drive_c/Program Files (x86)/Microsoft/EdgeWebView/Application/157'
        web.mkdir(parents=True);(web/'msedgewebview2.exe').write_bytes(b'MZ')
        return path

    def fixture(self):
        p=self.payload;p.mkdir()
        (p/'compat').mkdir()
        source=Path(__file__).resolve().parents[2]
        for name in ('roblox-compression.py','cursor-visibility.py','prepare-proton.py'):
            (p/'compat'/name).write_bytes((source/'compat'/name).read_bytes())
        for name in ('lynrt.dll','cursor-state.exe'):(p/'compat'/name).write_bytes(b'MZfixture')
        (p/'setup/assets').mkdir(parents=True)
        (p/'setup/assets/lynix-patch.svg').write_text('<svg/>')
        (p/'lynix-proton.sh').write_text('''#!/bin/bash
set -euo pipefail
exe=""; proton=""
while [ "$#" -gt 0 ]; do
 case "$1" in --exe) exe="$2"; shift;; --proton) proton="$2";shift;; esac
 shift
done
mkdir -p "$LYNIX_CONFIG_DIR"
printf 'EXE_PATH=%s\nPROTON_DIR=%s\n' "$exe" "$proton" >"$LYNIX_CONFIG_DIR/config"
printf 'LYNIX_PROGRESS|92|Runtime setup complete\n'
''')
        compat=self.layout.data/'compat';compat.mkdir(parents=True)
        (compat/'cabinet.dll').write_bytes(b'MZexisting-lynrt.dll\0')
        (compat/'lynrt.dll').write_bytes(b'MZfixture')
        (compat/'manifest.json').write_text(json.dumps({n:checksum(compat/n) for n in ('cabinet.dll','lynrt.dll')}))

    def test_discovery_deduplicates_and_reads_other_libraries(self):
        steam=self.layout.home/'.local/share/Steam'
        recommended=self.proton(steam/'compatibilitytools.d/GE','GE-Proton11-11')
        other=self.root/'Another Library'
        experiment=self.proton(other/'steamapps/common/Proton Experimental','experimental-11')
        (steam/'steamapps').mkdir()
        (steam/'steamapps/libraryfolders.vdf').write_text('"libraryfolders" { "1" { "path" "'+str(other)+'" } }')
        (self.layout.home/'.steam').mkdir();(self.layout.home/'.steam/steam').symlink_to(steam)
        result=discover_proton(self.layout)
        self.assertEqual(result[0],recommended)
        self.assertEqual(result.count(recommended),1)
        self.assertIn(experiment,result)

    def test_prefix_migration_without_executing_old_entry(self):
        prefix=self.prefix(self.root/'old prefix')
        self.layout.bin.mkdir(parents=True)
        (self.layout.bin/'lynix').write_text('#!/bin/sh\nSTEAM_PREFIX_DEFAULT="'+str(prefix)+'"\ntouch /tmp/should-never-run\n')
        with mock.patch.dict(os.environ,{},clear=True):
            self.assertEqual(detect_prefix(self.layout),prefix)
        self.assertTrue(vc_present(prefix));self.assertTrue(webview_present(prefix))

    def test_existing_install_skips_all_downloads_and_preserves_ui(self):
        self.fixture()
        prefix=self.prefix(self.root/'existing-prefix')
        exe=self.root/'user-owned/UI.exe';exe.parent.mkdir();exe.write_bytes(b'MZuser-file-do-not-copy')
        proton=self.proton(self.root/'Proton with spaces $dollars','GE-Proton11-11')
        events=[]
        i=Installer(self.layout,self.payload,lambda v,t:events.append((v,t)))
        with mock.patch.object(i,'download',side_effect=AssertionError('unexpected download')):
            i.install(exe,proton,prefix)
            installed_mtime=(self.layout.data/'compat/cabinet.dll').stat().st_mtime_ns
            i.install(exe,proton,prefix)
        self.assertEqual(exe.read_bytes(),b'MZuser-file-do-not-copy')
        self.assertFalse(list(self.layout.data.rglob('UI.exe')))
        self.assertEqual(installed_mtime,(self.layout.data/'compat/cabinet.dll').stat().st_mtime_ns)
        self.assertTrue(os.access(self.layout.bin/'lynix',os.X_OK))
        self.assertTrue(os.access(self.layout.bin/'lynix-proton.sh',os.X_OK))
        self.assertIn('skipping',' '.join(t for _,t in events))
        parsed=json.loads((self.layout.config/'setup.json').read_text())
        self.assertEqual(parsed['prefix'],str(prefix))
        subprocess.run(['bash','-n',str(self.layout.bin/'lynix')],check=True)
        self.assertIn(quote_desktop(self.layout.bin/'lynix'),(self.layout.applications/'lynx.desktop').read_text())

    def test_fresh_install_downloads_and_redirects_only_dll_import(self):
        self.fixture()
        (self.layout.data/'compat/cabinet.dll').unlink()
        exe=self.root/'UI.exe';exe.write_bytes(b'MZuser')
        proton=self.proton(self.root/'GE','GE-Proton11-11')
        i=Installer(self.layout,self.payload)
        calls=[]
        def download(url,dest,*args,**kwargs):
            calls.append(url)
            data=b'MZ'+b'ntdll.dll\0' if 'symbols' in url else b'MZinstaller'
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);return data
        with mock.patch.object(i,'download',side_effect=download):
            i.install(exe,proton,self.root/'new-prefix')
        self.assertEqual(len(calls),3)
        self.assertEqual((self.layout.data/'compat/cabinet.dll').read_bytes(),b'MZlynrt.dll\0')

    def test_bad_download_hash_is_never_installed(self):
        i=Installer(self.layout,self.payload)
        response=io.BytesIO(b'wrong');response.headers={'Content-Length':'5'}
        dest=self.root/'download.dll'
        with mock.patch('urllib.request.urlopen',return_value=response):
            with self.assertRaisesRegex(ValueError,'checksum'):
                i.download('https://example.invalid/file',dest,0,1,'test',sha='0'*64)
        self.assertFalse(dest.exists());self.assertFalse(dest.with_suffix('.dll.part').exists())

    def test_cancel_before_changes(self):
        stop=threading.Event();stop.set()
        i=Installer(self.layout,self.payload,cancel=stop)
        with self.assertRaises(Cancelled):i.note(.1,'cancelled')
        self.assertFalse(i.log.exists())

    def test_invalid_proton_does_not_change_install(self):
        i=Installer(self.layout,self.payload)
        exe=self.root/'UI.exe';exe.write_bytes(b'MZuser')
        with self.assertRaisesRegex(ValueError,'Proton'):
            i.install(exe,self.root/'missing')
        self.assertFalse(self.layout.data.exists())


if __name__=='__main__':unittest.main()
