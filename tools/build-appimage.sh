#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
project="$PWD"
compat/lynrtl/build.sh
compat/cursor/build.sh
python3 tools/appimage.py prepare
docker build --tag lynix-patch-builder:0.1 --file tools/AppImage.Dockerfile tools
docker run --rm --user "$(id -u):$(id -g)" \
  -e HOME=/tmp -e PYINSTALLER_CONFIG_DIR=/build/pyinstaller-cache -e LYNIX_BUILD_ROOT=/build \
  -v "$project:/project:ro" -v "$project/.build/appimage:/build" \
  lynix-patch-builder:0.1 \
  /opt/build-venv/bin/python /project/tools/freeze.py
python3 tools/appimage.py package
