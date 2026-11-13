# Local Roblox compression compatibility fix

The verified launch failure on GE-Proton11-11 had two causes:

1. Wine's Cabinet DLL did not export ordinal 40 (`CreateDecompressor`).
2. Microsoft's Cabinet DLL then called `RtlGetCompressionWorkSpaceSize(4, ...)`,
   which Wine rejected with `STATUS_UNSUPPORTED_COMPRESSION` for XPRESS Huffman.

The working fix uses a Windows Cabinet DLL already obtained during setup.
Its sole `ntdll.dll` import descriptor is redirected to `lynrt.dll`. The small
Rust helper supplies the two required XPRESS Huffman APIs using the pinned
`ms-compress` 0.2.1 codec. Other imported APIs forward to Wine's ntdll.
Only format 4 is implemented by these two helper functions.

Installed assets are in `~/.local/share/lynix-proton/compat/`:

- `cabinet.dll`: the Windows DLL with the import name redirected.
- `lynrt.dll`: the built helper (the build output is named `lynrtl.dll`).
- `manifest.json`: SHA-256 hashes of both installed assets.
- `roblox-compression.py`: idempotent repair and version-folder watcher.

`lynix-proton.sh` enables `cabinet=native,builtin` for `RobloxPlayerBeta.exe`
only, repairs existing Roblox versions before launch, and runs the quiet watcher
while the wrapper is alive. It checks new or overwritten version folders every
second. Existing DLLs are backed up by content hash under
`~/.local/share/lynix-proton/backups/roblox-compression/` before replacement.
The helper is installed before the Cabinet DLL and each replacement is atomic.
Wine/Proton's own libraries remain unchanged. Future Roblox releases still need
compatibility testing; this preserves the tested workaround, not a guarantee
that every future client will work.

To rebuild the helper, run `lynrtl/build.sh` with Rust, LLVM's `llvm-dlltool-18`,
Clang, and Python 3 available. It installs Rust's Windows MSVC target and uses
Rust's bundled linker; no Windows SDK is needed. Set `WINE` to the selected
Proton `files/bin/wine` and `WINEPREFIX` to the test prefix to also run the
Windows smoke test (known XPRESS Huffman output and truncated-input rejection).
The dependency version and checksum are pinned in `Cargo.lock`.

The Windows Cabinet binary is kept only in the local installation, outside
this source tree. Its unmodified backup is
`~/.local/share/lynix-proton/backups/cabinet-unmodified.dll`.
To recreate its import redirection, replace the one NUL-terminated
`ntdll.dll` string with the equally sized `lynrt.dll` string in that backup.
Do not apply the previous `RtlDecompressBufferEx` name patch.

## Desktop cursor and native window borders

The launch wrapper must remain executable (`install -m 755 lynix-proton.sh
~/.local/bin/lynix-proton.sh`). Copying the source with its former mode 0600
caused the desktop shortcut to fail before any launch logging occurred.

`prepare-proton.py` prepares a private, space-saving hard-link copy of the
selected GE-Proton11-11 build under the wrapper's `proton-desktop` directory.
It replaces the private `winex11.so` with a two-byte guarded patch: ignore the
Mutter-specific decoration veto in `get_mwm_decorations_for_style`. The source
Proton library is never modified. Both the source SHA-256 and original machine
instructions must match; unknown Proton builds fall back to the selected
unmodified build. The pinned source implementation is visible at
https://github.com/ValveSoftware/wine/blob/proton_11.0/dlls/winex11.drv/window.c .
The resulting X11 windows request native decorations, verified with nonzero
`_MOTIF_WM_HINTS` decorations and a compositor-provided `_NET_FRAME_EXTENTS`.

Roblox-specific registry settings enable fullscreen grabbing, Windows cursor
shapes, window-manager control, and DirectInput mouse warping. They are scoped
to the executable, so a Roblox version-folder update keeps them.

The remaining visual cursor issue was observed while Wine reported a real
one-pixel `GetClipCursor` rectangle during both camera locking modes. The
`cursor-state.exe` reporter reads that shared cursor state without attaching
to or changing the game. `cursor-visibility.py` checks X11 input focus and the
focused process's executable and Wine prefix, and hides the host pointer with
XFixes only while the focused Roblox process has a one- or two-pixel cursor
lock. It restores the pointer on release, focus loss, stale telemetry, helper
shutdown, or parent exit. Ordinary menu and desktop pointing stays visible.

Both helpers start quietly with the normal desktop launcher and stop when the
launcher exits. Per-prefix locks prevent duplicate watchers. The cursor reader
can be rebuilt with `cursor/build.sh` (LLVM, Clang and Rust's bundled linker).
