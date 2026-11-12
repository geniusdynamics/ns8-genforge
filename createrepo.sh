#!/bin/bash

#
# Copyright (C) 2026 Nethesis S.r.l.
# SPDX-License-Identifier: GPL-3.0-or-later
#

set -e

if ! buildah containers --format "{{.ContainerName}}" | grep -q nethforgemd-builder; then
    echo "Pulling Python runtime and Skopeo..."
    buildah from --name nethforgemd-builder -v "${PWD}:/usr/src:Z" docker.io/library/python:3.11-alpine
    buildah run nethforgemd-builder sh <<EOF
python3 -mvenv /opt/pyenv --upgrade-deps
/opt/pyenv/bin/pip3 install semver==3.0.1 filetype PyYAML
apk add skopeo
EOF
fi

buildah run --workingdir /usr/src nethforgemd-builder /opt/pyenv/bin/python3 createrepo.py
