#!/usr/bin/env python3
"""Keep the tested compression DLLs installed in this prefix's Roblox versions."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.lynix-', delete=False) as f:
        temp = Path(f.name)
        try:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
            os.chmod(temp, 0o644)
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)


def repair(versions, assets, backups):
    """Idempotent; only write changed DLLs, backing up their previous bytes."""
    for version in versions.glob('version-*'):
        if version.is_symlink() or not (version / 'RobloxPlayerBeta.exe').is_file():
            continue
        # Install the dependency before the DLL that imports it.
        for name in ('lynrt.dll', 'cabinet.dll'):
            dest = version / name
            old = dest.read_bytes() if dest.exists() else None
            data = assets[name]
            if old == data:
                continue
            if old is not None:
                backup = backups / version.name / f'{name}.{digest(old)}'
                if not backup.exists():
                    atomic_write(backup, old)
            atomic_write(dest, data)
            print(f'[compression] Installed {name} in {version.name}', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--backups', type=Path, required=True)
    parser.add_argument('--parent', type=int)
    args = parser.parse_args()
    manifest = json.loads((args.assets / 'manifest.json').read_text())
    assets = {name: (args.assets / name).read_bytes() for name in ('lynrt.dll', 'cabinet.dll')}
    for name, data in assets.items():
        if digest(data) != manifest[name]:
            raise ValueError(f'Compression asset checksum mismatch: {name}')
    versions = args.prefix / 'pfx/drive_c/users/steamuser/AppData/Local/Roblox/Versions'
    if args.parent is None:
        repair(versions, assets, args.backups)
        return
    # One quiet watcher per prefix; the lock releases when the process exits.
    with (args.prefix / '.lynix-compression.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        parent = Path(f'/proc/{args.parent}')
        parent_start = (parent / 'stat').read_text().rsplit(')', 1)[1].split()[19]
        while parent.exists():
            try:
                if (parent / 'stat').read_text().rsplit(')', 1)[1].split()[19] != parent_start:
                    break
                repair(versions, assets, args.backups)
            except FileNotFoundError:
                pass  # A version may be replaced while the launcher updates it.
            except OSError as exc:
                print(f'[compression] Repair deferred: {exc}', flush=True)
            time.sleep(1)


if __name__ == '__main__':
    main()
