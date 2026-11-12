#!/usr/bin/env python3

#
# Copyright (C) 2026 Nethesis S.r.l.
# SPDX-License-Identifier: GPL-3.0-or-later
#

#
# Create NethServer repository metadata
# Walk all directories on the given path: each path represent a package
#

import os
import sys
import copy
import json
import filetype
import semver
import subprocess
import glob
import urllib.request
import yaml


try:
    pins = yaml.safe_load(open("pins.yml")) or {}
except Exception as ex:
    print("[WARNING] while parsing pins.yml:", ex, file=sys.stderr)
    pins = {}

def pins_match_remove(entry_name, semver_tag):
    global pins
    if entry_name in pins:
        for opin in pins[entry_name]:
            if opin.get('remove') == True and opin.get('match'):
                if semver_tag.match(opin['match']):
                    return True
    return False

def is_pngfile(file_path):
    kind = filetype.guess(file_path)
    if kind is None:
        return False

    return kind.extension == 'png'

path = '.'
index = []
defaults = {
    "name": "",
    "description": { "en": "" },
    "logo": None,
    "screenshots": [],
    "categories" : [ "unknown" ],
    "authors" : [ {"name": "unknown", "email": "info@nethserver.org" } ],
    "docs": { 
        "documentation_url": "https://docs.nethserver.org",
        "bug_url": "https://github.com/NethServer/dev",
        "code_url": "https://github.com/NethServer/"
    },
    "source": "ghcr.io/nethserver",
    "versions": []
}

# Get current working directory if no path is specified
if len(sys.argv) >= 2:
    path = sys.argv[1]

# Walk all subdirectories
for entry_path in glob.glob(path + '/*'): # do not match .git and similar
    if not os.path.isdir(entry_path):
        continue # ignore files

    entry_name = entry_path[len(path + '/'):]

    # make sure to copy the defaults and do not just creating a reference
    metadata = copy.deepcopy(defaults)
    # prepare default values
    metadata["name"] = entry_name
    metadata["description"]["en"] = f"Auto-generated description for {entry_name}"
    metadata["source"] = f"{metadata['source']}/{entry_name}"
    # this field will be used to calculate the base name of images
    metadata["id"] = entry_name

    version_labels = {}
    metadata_file = os.path.join(entry_name, "metadata.json")

    # local file overrides the remote one
    # if a file is not present, download from git repository:
    # assume the source package is hosted on GithHub under NethServer organization
    if not os.path.isfile(metadata_file):
        print(f'Downloading metadata for {metadata["name"]}', file=sys.stderr)
        url = f'https://raw.githubusercontent.com/NethServer/ns8-{metadata["name"]}/main/ui/public/metadata.json'
        res = urllib.request.urlopen(urllib.request.Request(url))
        with open(metadata_file, 'wb') as metadata_fpw:
             metadata_fpw.write(res.read())

    with open(metadata_file) as metadata_fp:
        # merge defaults and JSON file, the latter one has precedence
        metadata = {**metadata, **json.load(metadata_fp)}

    # download logo if not present
    # add it only if it's a PNG
    logo = os.path.join(entry_name, "logo.png")
    if not os.path.isfile(logo):
        print(f'Downloading logo for {metadata["name"]}', file=sys.stderr)
        url = f'https://raw.githubusercontent.com/NethServer/ns8-{metadata["name"]}/main/ui/src/assets/module_default_logo.png'
        try:
            res = urllib.request.urlopen(urllib.request.Request(url))
            with open(logo, 'wb') as logo_fpw:
                logo_fpw.write(res.read())
        except:
            pass

    if os.path.isfile(logo) and is_pngfile(logo):
        metadata["logo"] = "logo.png"

    # add screenshots if pngs are available inside the screenshots directory
    screenshot_dirs = os.path.join(entry_name, "screenshots")
    if os.path.isdir(screenshot_dirs):
        with os.scandir(screenshot_dirs) as sdir:
            for screenshot in sdir:
                if is_pngfile(screenshot.path):
                    metadata["screenshots"].append(os.path.join("screenshots",screenshot.name))

    print("Inspect " + metadata["source"], file=sys.stderr)
    metadata["versions"] = []
    # Parse the image info from remote registry to retrieve tags
    try:
        with subprocess.Popen(["skopeo", "inspect", 'docker://' + metadata["source"]], stdout=subprocess.PIPE, stderr=sys.stderr) as proc:
            repo_inspect = json.load(proc.stdout)

        # Filter out non-semver tags and reverse-sort remaining tags from
        # younger to older:
        semver_tags = list(sorted(filter(semver.VersionInfo.is_valid, repo_inspect["RepoTags"]),
            key=semver.parse_version_info,
            reverse=True,
        ))

    except Exception as ex:
        print(f'[ERROR] cannot inspect {metadata["source"]}', ex, file=sys.stderr)
        continue

    testing_found = False # record if a testing release was found
    for tag in semver_tags:
        semver_tag = semver.parse_version_info(tag)

        if testing_found and semver_tag.prerelease is not None:
            # skip older testing releases, we do not need them
            continue

        # Ignore tags that match remove-pins:
        if pins_match_remove(entry_name, semver_tag):
            print("* Removed pinned version", tag, file=sys.stderr)
            continue

        try:
            # Fetch the image labels
            with subprocess.Popen(["skopeo", "inspect", f'docker://{metadata["source"]}:{tag}'], stdout=subprocess.PIPE, stderr=sys.stderr) as proc:
                image_inspect = json.load(proc.stdout)
            image_labels = image_inspect['Labels']
        except Exception as ex:
            print(f'[ERROR] cannot inspect {metadata["source"]}:{tag}', ex, file=sys.stderr)
            continue

        image_version = {
            "tag": tag,
            "testing": semver_tag.prerelease is not None,
            "labels": image_labels,
        }
        print("* Add registry version", tag, file=sys.stderr)
        metadata["versions"].append(image_version)

        if semver_tag.prerelease is None:
            # Only the last stable tag is actually needed: stop here
            break
        else:
            testing_found = True

    for opin in pins.get(entry_name, []):
        if type(opin) is str:
            tag = opin
            prepend_pin = False
        elif 'tag' in opin:
            tag = opin['tag']
            prepend_pin = opin['prepend']
        else:
            continue # skip remove pins
        semver_tag = semver.parse_version_info(tag)
        try:
            # Fetch the pinned image labels
            with subprocess.Popen(["skopeo", "inspect", f'docker://{metadata["source"]}:{tag}'], stdout=subprocess.PIPE, stderr=sys.stderr) as proc:
                image_inspect = json.load(proc.stdout)
            image_labels = image_inspect['Labels']
        except Exception as ex:
            print(f'[ERROR] cannot inspect {metadata["source"]}:{tag}', ex, file=sys.stderr)
            continue
        image_version = {
            "tag": tag,
            "testing": semver_tag.prerelease is not None,
            "labels": image_labels,
        }
        if image_version in metadata["versions"]:
            print("* Skipped pinned version", tag, "because it is already present.", "Image labels:", image_labels, file=sys.stderr)
        else:
            if prepend_pin:
                print("* Prepend pinned version", tag, "Image labels:", image_labels, file=sys.stderr)
                metadata["versions"].insert(0, image_version)
            else:
                print("* Append pinned version", tag, "Image labels:", image_labels, file=sys.stderr)
                metadata["versions"].append(image_version)

    if not metadata["versions"]:
        print("[WARNING] no versions found for", metadata["source"], file=sys.stderr)
    index.append(metadata)

with open (os.path.join(path, 'repodata.json'), 'w') as outfile:
    json.dump(index, outfile, separators=(',', ':'))
