import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest import mock

spec=importlib.util.spec_from_file_location('cursor_visibility',Path(__file__).resolve().parents[2]/'compat/cursor-visibility.py')
cursor=importlib.util.module_from_spec(spec);spec.loader.exec_module(cursor)


class CursorLifecycleTests(unittest.TestCase):
    def test_game_detector_checks_executable_and_prefix(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);proc=root/'123';proc.mkdir();prefix=root/'prefix'
            (proc/'cmdline').write_bytes(b'C:\\Roblox\\RobloxPlayerBeta.exe\0')
            (proc/'environ').write_bytes(b'WINEPREFIX='+os.fsencode(prefix/'pfx')+b'/\0')
            with mock.patch.object(Path,'glob',return_value=[proc]):
                self.assertEqual(cursor.game_process(prefix),proc)
                self.assertIsNone(cursor.game_process(root/'other-prefix'))
                (proc/'cmdline').write_bytes(b'C:\\Other.exe\0')
                self.assertIsNone(cursor.game_process(prefix))

    def test_reporter_stops_when_game_exits_without_holding_prefix_open(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);prefix=root/'prefix';prefix.mkdir();marker=root/'child.pid'
            script=root/'reporter.py'
            script.write_text('import os,time\nfrom pathlib import Path\nPath('+repr(str(marker))+').write_text(str(os.getpid()))\nwhile True:\n print("clip=10,10,11,11",flush=True)\n time.sleep(.02)\n')
            states=[]
            class Desktop:
                def game_focused(self,prefix):return True
                def hide(self,hidden):states.append(hidden)
                def close(self):states.append(False)
            parent=subprocess.Popen(['sleep','1.1'])
            reaper=threading.Thread(target=parent.wait);reaper.start()
            start=time.monotonic()
            def game(*_):return root/'game' if time.monotonic()-start<.25 else None
            args=types.SimpleNamespace(prefix=prefix,parent=parent.pid,wine=Path(sys.executable),reporter=script)
            try:
                with mock.patch.object(cursor,'Desktop',Desktop),mock.patch.object(cursor,'game_process',side_effect=game),mock.patch.object(cursor.signal,'signal'):
                    cursor.run(args)
                self.assertTrue(marker.exists())
                self.assertFalse(Path('/proc/'+marker.read_text()).exists())
                self.assertIn(True,states)
                self.assertFalse(states[-1])
            finally:
                if parent.poll() is None:parent.terminate()
                reaper.join(timeout=2)


if __name__=='__main__':unittest.main()
