# Setup implementation

`main.py` implements the two-file-selection form and a progress bar with GTK 3.
`backend.py` handles discovery, prefix migration, validated Microsoft downloads,
runtime reuse, executable installation, and desktop integration.

The frozen app also has an internal `--support SCRIPT ...` mode. The wrapper
uses the installed runtime to run its Python helpers, so it never depends on
an AppImage mount or the build machine's Python path. Support mode loads no GTK
and restores the host environment before spawning Wine.

The UI starts work only after Continue. On success the window closes before the
persistent launcher is started. Closing during setup cancels only the setup's
own subprocess group. Failed or interrupted setup can be run again.

The Microsoft Cabinet DLL is fetched from Microsoft's public symbol service by
its PE identity and verified against the pinned download SHA-256. The setup
redirects its `ntdll.dll` import to our XPRESS helper without altering its API
exports. Existing validated local compression assets are reused, including the
original ISO-supplied DLL. No Microsoft binary is redistributed in the AppImage.

CLI options `--check` and `--install --exe PATH --proton PATH --no-launch` support
verification. `--test-root PATH` keeps test shortcuts and configuration separate
from a real user installation. The test suite covers reuse, new installs,
checksum rejection, cancellation, discovery across Steam libraries, and paths
with spaces/shell metacharacters.
