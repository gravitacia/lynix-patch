# Lynix-patch

A small Linux setup app for your own **UI.exe**, plus the Lynix Proton wrapper
with persistent Roblox launch, cursor, and native window-border fixes.

Based on the original [Lynix by synapzis](https://github.com/synapzis/lynix)
and [alloc-nullptr's upstream](https://github.com/alloc-nullptr/lynix).
The original MIT license and attribution are preserved in [LICENSE](LICENSE).

## Setup AppImage

**[Download the setup AppImage](https://github.com/snooped-xl/lynix-patch/releases/latest/download/Lynix-patch-Setup-x86_64.AppImage)**
· [Releases and checksums](https://github.com/snooped-xl/lynix-patch/releases/latest)

Open `Lynix-patch-Setup-x86_64.AppImage`, choose your **UI.exe** and a **Proton
folder**, then click **Continue**. The setup app:

1. Detects Proton in normal Steam, GE-Proton, Flatpak Steam, and additional
   Steam library locations. A custom Proton folder can also be selected.
2. Reuses an existing Lynx/Lynix prefix when detected, including installations
   made with the earlier wrapper. Existing Microsoft runtimes and compression
   DLLs are kept; missing components are downloaded at setup time.
3. Installs the launcher and compatibility helpers persistently in your home
   folder, creates the **Lynx** application-menu shortcut, closes setup, and
   launches Lynx.

**Recommended and tested: GE-Proton11-11, x86_64.** Other Proton versions are
selectable, but have not been tested with this client. The native-border driver
patch applies only to the exact verified GE-Proton build and safely falls back
for unknown builds. Roblox/Lynx updates can introduce new compatibility issues.

The AppImage targets x86_64 Linux with glibc 2.35 or newer (Ubuntu 22.04+).
It bundles its Python/GTK setup runtime and the open-source helpers. It does
**not** bundle UI.exe, Roblox, a Proton build, a Windows prefix, user data, or
proprietary Windows DLLs. Required Microsoft files download from Microsoft.
Lynx handles downloading its own client files. Keep your UI.exe and Proton in
their chosen locations; the installer does not copy them.

If needed, mark the downloaded AppImage executable:

```sh
chmod +x Lynix-patch-Setup-x86_64.AppImage
./Lynix-patch-Setup-x86_64.AppImage
```

Without FUSE, use `./Lynix-patch-Setup-x86_64.AppImage --appimage-extract-and-run`.
The installed shortcut keeps working if you move or delete the setup AppImage.

## What persists

- The compression fix repairs existing/new Roblox version folders while Lynx
  runs and checks them again on each launch.
- The cursor helper hides the stray desktop cursor only while the focused
  Roblox window reports a tiny camera-lock rectangle. It restores the cursor
  when that lock ends, focus changes, or the helper exits.
- A private copy of the verified Proton driver uses native desktop title bars
  instead of forcing Wine's classic border under Mutter. Steam's Proton files
  stay unchanged.
- Installer upgrades preserve old launcher/configuration files as backups and
  always install the launcher with executable permission.

No separate terminal/log window opens. Setup errors stay in the setup window;
logs are saved under `~/.local/share/lynix-proton/logs/`.

## Build from source

On an x86_64 Linux host, install Docker, Rust (1.96+), Clang, LLVM's
`llvm-dlltool-18`, Python 3, and `mksquashfs`, then run:

```sh
./tools/build-appimage.sh
```

The output is `dist/Lynix-patch-Setup-x86_64.AppImage`, with a SHA-256 file.
The build uses an Ubuntu 22.04 container for Python/GTK compatibility. AppImage
runtime and Rust codec downloads are pinned by checksum. Native helpers are
built from source; no Windows DLL or UI.exe is included in the payload.
Build and dependency source/notices are included inside the AppImage.

Run installer logic tests with:

```sh
python3 -m unittest discover -s setup/tests -v
```

Implementation details and rollback locations: [compat/README.md](compat/README.md).
Underlying wrapper options: [docs/WRAPPER.md](docs/WRAPPER.md).

## Credits

- **alloc-nullptr** — original Lynix wrapper and its MIT license.
- **synapzis/lynix** — original repository this patch builds on.
- **snooped-xl** — patched setup and Linux compatibility fixes.
- **CaddyGlow/ms-compress**, based in part on **Eric Biggers' wimlib** — XPRESS
  Huffman codec. The dependency's LGPL and other notices, exact dependency
  source, and helper relinking source are supplied with the build.
- **Wine/Proton**, **GTK/PyGObject**, **Python**, **PyInstaller**, and
  **AppImage/type2-runtime** — the compatibility and setup infrastructure.
