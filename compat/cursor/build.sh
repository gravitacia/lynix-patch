#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
for lib in user32 kernel32 msvcrt; do
 llvm-dlltool-18 -m i386:x86-64 -d "$lib.def" -l "$lib.lib"
done
clang --target=x86_64-pc-windows-msvc -c -O2 state.c -o state.obj
sysroot="$(rustc --print sysroot)"
host="$(rustc -vV | sed -n 's/^host: //p')"
"$sysroot/lib/rustlib/$host/bin/rust-lld" -flavor link /entry:mainCRTStartup \
 /subsystem:windows /nodefaultlib /out:cursor-state.exe state.obj user32.lib kernel32.lib msvcrt.lib ../lynrtl/msvcrt.lib
