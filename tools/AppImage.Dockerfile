# Build on Ubuntu 22.04 to support glibc 2.35 and newer x86_64 Linux systems.
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpython3.10 python3 python3-venv python3-pip python3-gi python3-gi-cairo gir1.2-gtk-3.0 \
    libgtk-3-0 libgdk-pixbuf2.0-bin librsvg2-common adwaita-icon-theme \
    binutils patchelf ca-certificates libxfixes3 \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv --system-site-packages /opt/build-venv \
    && /opt/build-venv/bin/pip install --no-cache-dir pyinstaller==6.22.3 pyinstaller-hooks-contrib==2026.10
