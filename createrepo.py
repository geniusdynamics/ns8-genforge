#!/usr/bin/env python3

#
# Copyright (C) 2023 Nethesis S.r.l.
# SPDX-License-Identifier: GPL-3.0-or-later
#

#
# Create NethForge repository metadata
# Walk all directories on the given path: each path represent a package
#

import os
import sys
import copy
import json
import imghdr
import semver
import subprocess
import glob
import urllib.request

path = '.'
index = []
defaults = {
    "name": "",
    "description": {"en": ""},
    "logo": None,
    "screenshots": [],
    "categories": ["unknown"],
    "authors": [
        {"name": "unknown", "email": "info@nethserver.org"},
        {
            "name": "Kemboi Elvis",
            "email": "kemboielvis@genius.ke"
        },
        {
            "name": "Martin Bhuong",
            "email": "martin@genius.ke"
        }
    ],
    "docs": {
        "documentation_url": "https://docs.nethserver.org",
        "bug_url": "https://github.com/NethServer/dev",
        "code_url": "https://github.com/NethServer/"
    },
    "versions": []
}

# Get current working directory if no path is specified
if len(sys.argv) >= 2:
    path = sys.argv[1]

# Walk all subdirectories
for entry_path in glob.glob(path + '/*'):  # do not match .git and similar
    if not os.path.isdir(entry_path):
        continue  # ignore files

    entry_name = entry_path[len(path + '/'):]

    # make sure to copy the defaults and do not just creating a reference
    metadata = copy.deepcopy(defaults)
    # prepare default values
    metadata["name"] = entry_name.capitalize()
    metadata["description"]["en"] = f"Auto-generated description for {entry_name}"
    # this field will be used to calculate the base name of images
    metadata["id"] = entry_name

    version_labels = {}
    metadata_file = os.path.join(entry_name, "metadata.json")

    try:
        with open(metadata_file) as metadata_fp:
            # merge defaults and JSON file, the latter one has precedence
            metadata = {**metadata, **json.load(metadata_fp)}
    except FileNotFoundError as ex:
        print(f"Module {entry_name} was ignored:", ex, file=sys.stderr)
        continue

    logo = os.path.join(entry_name, "logo.png")
    if os.path.isfile(logo) and imghdr.what(logo) == "png":
        metadata["logo"] = "logo.png"

    # add screenshots if pngs are available inside the screenshots directory
    screenshot_dirs = os.path.join(entry_name, "screenshots")
    if os.path.isdir(screenshot_dirs):
        with os.scandir(screenshot_dirs) as sdir:
            for screenshot in sdir:
                if imghdr.what(screenshot) == "png":
                    metadata["screenshots"].append(os.path.join("screenshots", screenshot.name))

    print("Inspect " + metadata["source"])
    # Parse the image info from remote registry to retrieve tags
    with subprocess.Popen(["skopeo", "inspect", f'docker://{metadata["source"]}'], stdout=subprocess.PIPE,
                          stderr=sys.stderr) as proc:
        info = json.load(proc.stdout)
        metadata["versions"] = []
        versions = []
        for tag in info["RepoTags"]:
            try:
                versions.append(semver.VersionInfo.parse(tag))
                # Retrieve labels for each valid version
                p = subprocess.Popen(["skopeo", "inspect", f'docker://{metadata["source"]}:{tag}'],
                                     stdout=subprocess.PIPE, stderr=sys.stderr)
                info_tags = json.load(p.stdout)
                version_labels[tag] = info_tags['Labels']
            except:
                # skip invalid semantic versions
                pass

        # Sort by most recent
        for v in sorted(versions, reverse=True):
            metadata["versions"].append(
                {"tag": f"{v}", "testing": (not v.prerelease is None), "labels": version_labels[f"{v}"]})

    index.append(metadata)

with open(os.path.join(path, 'repodata.json'), 'w') as outfile:
    json.dump(index, outfile, separators=(',', ':'))
