#!/usr/bin/env python3
"""Private, checksum-guarded Proton driver fix for native Mutter decorations."""
import argparse
import fcntl
import hashlib
import os
from pathlib import Path
import shutil
import tempfile

REL = Path('files/lib/wine/x86_64-unix/winex11.so')
EXPECTED = '1c19c7d032c02f92fdf63653f242f5e87e2abd636b4e507283ac77a45b14b5b3'
OFFSET = 0x3e3ca  # get_mwm_decorations_for_style: mov %eax,%ecx -> xor %ecx,%ecx


def prepare(source, cache):
    source = source.resolve()
    data = (source / REL).read_bytes()
    if hashlib.sha256(data).hexdigest() != EXPECTED or data[OFFSET:OFFSET+2] != b'\x89\xc1':
        raise ValueError('Native border patch is not verified for this Proton build')
    patched = data[:OFFSET] + b'\x31\xc9' + data[OFFSET+2:]
    key = hashlib.sha256(str(source).encode() + (source/'version').read_bytes() + data).hexdigest()[:16]
    dest = cache / ('native-borders-' + key)
    cache.mkdir(parents=True, exist_ok=True)
    with (cache / '.native-borders.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not dest.exists():
            staging = Path(tempfile.mkdtemp(prefix='.native-borders-', dir=cache))
            try:
                # Hard links save space; never edit their contents. Replace the
                # one changed library atomically to leave the source untouched.
                def link_or_copy(src, dst):
                    try:
                        return os.link(src, dst)
                    except OSError:
                        return shutil.copy2(src, dst)
                shutil.copytree(source, staging, symlinks=True, copy_function=link_or_copy, dirs_exist_ok=True)
                target = staging / REL
                target.unlink()
                target.write_bytes(patched)
                target.chmod(0o755)
                os.rename(staging, dest)
            finally:
                if staging.exists():
                    shutil.rmtree(staging)
        if (dest / REL).read_bytes() != patched:
            raise ValueError('Private Proton driver checksum mismatch')
    return dest


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--proton', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    args = p.parse_args()
    print(prepare(args.proton, args.cache))
