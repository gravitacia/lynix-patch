#!/usr/bin/env python3
"""Hide the host cursor only while the focused Roblox client requests a tiny clip."""
import argparse
import ctypes as C
import ctypes.util
import fcntl
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import time


class Desktop:
    def __init__(self):
        self.x = C.CDLL(ctypes.util.find_library('X11'))
        self.f = C.CDLL(ctypes.util.find_library('Xfixes'))
        self.x.XOpenDisplay.argtypes = [C.c_char_p]
        self.x.XOpenDisplay.restype = C.c_void_p
        self.x.XDefaultRootWindow.argtypes = [C.c_void_p]
        self.x.XDefaultRootWindow.restype = C.c_ulong
        self.x.XInternAtom.argtypes = [C.c_void_p, C.c_char_p, C.c_int]
        self.x.XInternAtom.restype = C.c_ulong
        self.x.XGetInputFocus.argtypes = [C.c_void_p, C.POINTER(C.c_ulong), C.POINTER(C.c_int)]
        self.x.XGetWindowProperty.argtypes = [C.c_void_p,C.c_ulong,C.c_ulong,C.c_long,C.c_long,C.c_int,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_int),C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.c_void_p)]
        self.x.XQueryTree.argtypes = [C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.c_void_p),C.POINTER(C.c_uint)]
        self.x.XFree.argtypes = [C.c_void_p]
        self.x.XFlush.argtypes = [C.c_void_p]
        self.x.XCloseDisplay.argtypes = [C.c_void_p]
        for name in ('XFixesHideCursor', 'XFixesShowCursor'):
            getattr(self.f,name).argtypes = [C.c_void_p,C.c_ulong]
        # A window can disappear between the focus query and property lookup.
        self.error = C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_void_p)(lambda *_: 0)
        self.x.XSetErrorHandler.argtypes = [C.c_void_p]
        self.x.XSetErrorHandler(self.error)
        self.d = self.x.XOpenDisplay(None)
        if not self.d:
            raise RuntimeError('X display unavailable')
        self.root = self.x.XDefaultRootWindow(self.d)
        self.pid_atom = self.x.XInternAtom(self.d,b'_NET_WM_PID',0)
        self.hidden = False

    def game_focused(self, prefix):
        window=C.c_ulong();revert=C.c_int()
        self.x.XGetInputFocus(self.d,C.byref(window),C.byref(revert))
        for _ in range(10):
            if window.value in (0,1,self.root):
                return False
            actual=C.c_ulong();fmt=C.c_int();count=C.c_ulong();after=C.c_ulong();data=C.c_void_p()
            self.x.XGetWindowProperty(self.d,window.value,self.pid_atom,0,1,0,0,C.byref(actual),C.byref(fmt),C.byref(count),C.byref(after),C.byref(data))
            try:
                if data.value and count.value and fmt.value == 32:
                    pid=C.cast(data,C.POINTER(C.c_ulong))[0]
                    proc=Path(f'/proc/{pid}')
                    try:
                        command=(proc/'cmdline').read_bytes().split(b'\0')[0].lower()
                        env=(proc/'environ').read_bytes().split(b'\0')
                        if command.endswith(b'\\robloxplayerbeta.exe'):
                            return any(e.rstrip(b'/') == b'WINEPREFIX='+os.fsencode(prefix/'pfx') for e in env)
                    except OSError:
                        return False
            finally:
                if data.value:self.x.XFree(data)
            root=C.c_ulong();parent=C.c_ulong();children=C.c_void_p();n=C.c_uint()
            if not self.x.XQueryTree(self.d,window.value,C.byref(root),C.byref(parent),C.byref(children),C.byref(n)):
                return False
            if children.value:self.x.XFree(children)
            window=parent
        return False

    def hide(self, hidden):
        if hidden != self.hidden:
            (self.f.XFixesHideCursor if hidden else self.f.XFixesShowCursor)(self.d,self.root)
            self.x.XFlush(self.d)
            self.hidden=hidden

    def close(self):
        self.hide(False)
        self.x.XCloseDisplay(self.d)


def game_process(prefix, previous=None):
    """Don't start a Wine reporter without a game: it would hold Proton open."""
    expected = os.fsencode((prefix/'pfx').resolve())
    def matches(proc):
        try:
            first = (proc/'cmdline').read_bytes().split(b'\0')[0].lower().replace(b'/', b'\\')
            if not first.endswith(b'\\robloxplayerbeta.exe'):
                return False
            for entry in (proc/'environ').read_bytes().split(b'\0'):
                if entry.startswith(b'WINEPREFIX='):
                    return os.path.realpath(entry.split(b'=',1)[1]) == expected
        except OSError:
            pass
        return False
    if previous is not None and matches(previous):
        return previous
    return next((proc for proc in Path('/proc').glob('[0-9]*') if matches(proc)), None)


def run(args):
    desktop=Desktop();proc=None;sel=selectors.DefaultSelector()
    stop=False
    def shutdown(*_):
        nonlocal stop
        stop=True
    def stop_reporter():
        nonlocal proc
        if proc is None:
            return
        if proc.stdout is not None:
            sel.unregister(proc.stdout)
            proc.stdout.close()
        if proc.poll() is None:
            os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=2)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        proc=None
    for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):signal.signal(sig,shutdown)
    try:
        parent=Path(f'/proc/{args.parent}')
        stamp=(parent/'stat').read_text().rsplit(')',1)[1].split()[19]
        env=dict(os.environ,WINEPREFIX=str(args.prefix/'pfx'),WINEDEBUG='-all')
        pending=b'';last=0;tiny=False;game=None;next_scan=0
        while not stop and parent.exists():
            try:
                if (parent/'stat').read_text().rsplit(')',1)[1].split()[19] != stamp:break
            except FileNotFoundError:
                break
            if time.monotonic() >= next_scan:
                game=game_process(args.prefix,game)
                next_scan=time.monotonic()+.35
            if game is None:
                desktop.hide(False)
                stop_reporter()
                time.sleep(.1)
                continue
            if proc is not None and proc.poll() is not None:
                stop_reporter()
            if proc is None:
                pending=b'';last=0;tiny=False
                proc=subprocess.Popen([str(args.wine),str(args.reporter)],env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,start_new_session=True)
                sel.register(proc.stdout,selectors.EVENT_READ)
            if sel.select(.1):
                data=os.read(proc.stdout.fileno(),16384)
                if not data:
                    desktop.hide(False)
                    stop_reporter()
                    continue
                pending+=data
                if b'\n' in pending:
                    complete,pending=pending.rsplit(b'\n',1)
                    match=re.search(rb'clip=(-?\d+),(-?\d+),(-?\d+),(-?\d+)',complete.splitlines()[-1])
                    if match:
                        left,top,right,bottom=map(int,match.groups())
                        tiny=0 < right-left <= 2 and 0 < bottom-top <= 2
                        last=time.monotonic()
            desktop.hide(tiny and time.monotonic()-last < .5 and desktop.game_focused(args.prefix))
    finally:
        desktop.close()
        stop_reporter()
        sel.close()


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--prefix',type=Path,required=True)
    p.add_argument('--wine',type=Path,required=True)
    p.add_argument('--reporter',type=Path,required=True)
    p.add_argument('--parent',type=int,required=True)
    args=p.parse_args()
    with (args.prefix/'.lynix-cursor.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit(0)
        run(args)
