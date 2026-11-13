#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
# Rust's bundled linker avoids requiring a Windows SDK or system-wide MinGW.
rustup target add x86_64-pc-windows-msvc
sysroot="$(rustc --print sysroot)"
host="$(rustc -vV | sed -n 's/^host: //p')"
mkdir -p .cargo
python3 - "$PWD" "$sysroot/lib/rustlib/$host/bin/rust-lld" <<'PY'
import json,sys,os
from pathlib import Path
root,linker=sys.argv[1:]
flags=[f'-Lnative={root}','-Clink-arg=/nodefaultlib','-Clink-arg=/entry:DllMain',f'-Clink-arg=/def:{root}/lynrtl.def',f'--remap-path-prefix={root}=lynix-patch/compat/lynrtl',f'--remap-path-prefix={os.path.expanduser("~/.cargo")}=rust-crates']
Path('.cargo/config.toml').write_text('[target.x86_64-pc-windows-msvc]\nlinker = '+json.dumps(linker)+'\nrustflags = '+json.dumps(flags)+'\n')
PY
for lib in kernel32 msvcrt ntdll; do
  llvm-dlltool-18 -m i386:x86-64 -d "$lib.def" -l "$lib.lib"
done
cargo build --locked --release --target x86_64-pc-windows-msvc
cp target/x86_64-pc-windows-msvc/release/lynrtl.dll lynrtl.dll
# Run the Windows ABI/decoder smoke test when WINE is supplied.
if [ -n "${WINE:-}" ]; then
  llvm-dlltool-18 -m i386:x86-64 -d test-kernel32.def -l test-kernel32.lib
  clang --target=x86_64-pc-windows-msvc -c -O2 test-helper.c -o test-helper.obj
  "$sysroot/lib/rustlib/$host/bin/rust-lld" -flavor link /entry:mainCRTStartup \
    /subsystem:console /nodefaultlib /out:test-helper.exe test-helper.obj test-kernel32.lib msvcrt.lib
  "$WINE" test-helper.exe
fi
