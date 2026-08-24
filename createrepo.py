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

from pathlib import Path
import re
from datetime import datetime, timezone
import os
import requests
from jinja2 import Template
import markdown
from bs4 import BeautifulSoup

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def get_github_stars(repo_url, github_token=None):
    if not repo_url or not repo_url.startswith("https://github.com/"):
        return 0
    api_url = f"https://api.github.com/repos/{repo_url.replace('https://github.com/', '')}"
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if github_token:
        headers['Authorization'] = f'token {github_token}'
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get('stargazers_count', 0)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching stars for {repo_url}: {e}")
        return 0


def parse_readme_tables(readme_text):
    html = markdown.markdown(readme_text, extensions=['tables'])
    soup = BeautifulSoup(html, 'html.parser')
    app_cards = []

    categories_header = soup.find('h1', string='Categories')
    if not categories_header:
        return []

    for header in categories_header.find_all_next('h2'):
        category = header.text.strip()
        table = header.find_next_sibling('table')
        if table:
            for row in table.find_all('tr')[1:]:  # Skip header row
                cols = row.find_all('td')
                if len(cols) >= 2:
                    company_cell = cols[1]
                    description = cols[2].text.strip()
                    
                    app_link_tag = company_cell.find('a')
                    app_name = app_link_tag.text.strip() if app_link_tag else company_cell.text.strip()
                    app_link = app_link_tag['href'] if app_link_tag else ""

                    # Github stars
                    stars_link_tag = cols[3].find('a') if len(cols) > 3 else None
                    repo_link = stars_link_tag['href'] if stars_link_tag else ""
                    stars = get_github_stars(repo_link, GITHUB_TOKEN)

                    # Alternatives
                    alt_cell = cols[4] if len(cols) > 4 else None
                    alternatives = []
                    if alt_cell:
                        for link in alt_cell.find_all('a'):
                            alternatives.append({'name': link.text.strip(), 'link': link['href']})

                    # NS8 Link
                    ns8_link_tag = cols[5].find('a') if len(cols) > 5 else None
                    ns8_link = ns8_link_tag['href'] if ns8_link_tag else f"https://github.com/geniusdynamics/ns8-{app_name.lower().replace(' ', '-')}"


                    print(f"DEBUG: category={category}, app_name={app_name}, description={description}, app_link={app_link}")
                    app_cards.append({
                        "category": category,
                        "name": app_name,
                        "desc": description,
                        "link": app_link,
                        "repo_link": repo_link,
                        "stars": stars,
                        "alt": alternatives,
                        "ns8_link": ns8_link
                    })
    return app_cards

def generate_html(cards):
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    
    def get_category_sort_key(category_string):
        match = re.match(r'(\d+)', category_string)
        if match:
            return int(match.group(1))
        return float('inf')  # Put categories without numbers at the end

    categories = sorted(list(set(card['category'] for card in cards)), key=get_category_sort_key)

    html_template = Template(r'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GenForge App Directory</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary-color: #0366d6;
                --background-color: #f6f8fa;
                --card-background: #ffffff;
                --text-color: #24292e;
                --subtle-text-color: #586069;
                --border-color: #e1e4e8;
                --shadow-color: rgba(0, 0, 0, 0.1);
            }
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                margin: 0;
                background-color: var(--background-color);
                color: var(--text-color);
            }
            .container {
                display: flex;
            }
            .sidebar {
                width: 250px;
                background-color: var(--card-background);
                border-right: 1px solid var(--border-color);
                padding: 20px;
                height: 100vh;
                position: fixed;
                overflow-y: auto;
                transition: transform 0.3s ease;
            }
            .sidebar h2 {
                font-size: 1.5em;
                color: var(--primary-color);
                margin-top: 0;
            }
            .sidebar ul {
                list-style: none;
                padding: 0;
            }
            .sidebar li {
                margin-bottom: 10px;
            }
            .sidebar a {
                text-decoration: none;
                color: var(--subtle-text-color);
                font-weight: 600;
            }
            .sidebar a:hover {
                color: var(--primary-color);
            }
            .main-content {
                margin-left: 270px;
                padding: 20px;
                width: calc(100% - 270px);
            }
            header {
                text-align: center;
                margin-bottom: 40px;
            }
            header h1 {
                font-size: 3em;
                color: var(--primary-color);
                margin: 0;
            }
            header p {
                color: var(--subtle-text-color);
                margin-top: 5px;
            }
            .about-section {
                background-color: var(--card-background);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 40px;
            }
            .about-section details {
                cursor: pointer;
            }
            .about-section summary {
                font-weight: 600;
                color: var(--primary-color);
            }
            .search-container {
                margin-bottom: 40px;
            }
            #search-input {
                width: 100%;
                padding: 15px;
                font-size: 1.2em;
                border: 1px solid var(--border-color);
                border-radius: 8px;
            }
            .app-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 24px;
            }
            .app-card {
                background: var(--card-background);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 20px;
                display: flex;
                flex-direction: column;
                transition: transform 0.2s, box-shadow 0.2s;
                box-shadow: 0 2px 4px var(--shadow-color);
            }
            .app-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 6px 12px var(--shadow-color);
            }
            .app-card h3 {
                margin: 0 0 10px 0;
                font-size: 1.8em;
            }
            .app-card h3 a {
                color: var(--text-color);
                text-decoration: none;
                font-weight: 700;
            }
            .app-card .category {
                font-size: 0.9em;
                font-weight: 600;
                color: var(--primary-color);
                margin-bottom: 15px;
            }
            .app-card .description {
                flex-grow: 1;
                color: var(--subtle-text-color);
                margin-bottom: 15px;
            }
            .app-links {
                margin-top: 15px;
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
            }
            .app-links a {
                padding: 8px 12px;
                font-size: 0.9em;
                background-color: var(--primary-color);
                color: white;
                text-decoration: none;
                border-radius: 6px;
                display: inline-flex;
                align-items: center;
                gap: 5px;
            }
            .alternatives {
                font-size: 0.9em;
                margin-top: 15px;
                color: var(--subtle-text-color);
            }
            footer {
                text-align: center;
                padding: 20px;
                margin-top: 40px;
                font-size: 0.9em;
                color: var(--subtle-text-color);
                border-top: 1px solid var(--border-color);
            }
            @media (max-width: 768px) {
                .container {
                    flex-direction: column;
                }
                .sidebar {
                    position: static;
                    width: 100%;
                    height: auto;
                    border-right: none;
                    border-bottom: 1px solid var(--border-color);
                }
                .main-content {
                    margin-left: 0;
                    width: 100%;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <nav class="sidebar">
                <h2>Categories</h2>
                <ul>
                    {% for category in categories %}
                    <li><a href="#{{ category.lower().replace(' ', '-') }}">{{ category }}</a></li>
                    {% endfor %}
                </ul>
            </nav>
            <div class="main-content">
                <header>
                    <h1>GenForge App Directory</h1>
                    <p>Last updated: {{ timestamp }}</p>
                    <p>Metadata are built every 4 hours at 00:25, 06:25 ,12:25, 18:25 UTC and on each commit to the main branch.</p>
                </header>
                <div class="about-section">
                    <details>
                        <summary>About this page and how to contribute</summary>
                        <p>If you want to add a module to this repository, just follow the
 <a href="https://nethserver.github.io/ns8-core/modules/new_module/#step-5-publish-to-ns8-software-repository">
  instructions
 </a>
 for
 <code>
  ns8-repomd
 </code>
 , finally open the pull request here!</p>
                    </details>
                </div>
                <main>
                    <div class="search-container">
                        <input type="text" id="search-input" placeholder="Search for applications...">
                    </div>
                    {% for category in categories %}
                    <section class="category-section" id="{{ category.lower().replace(' ', '-') }}">
                        <h2>{{ category }}</h2>
                        <div class="app-grid">
                            {% for app in cards if app.category == category %}
                            <div class="app-card" data-name="{{ app.name.lower() }}" data-category="{{ app.category.lower() }}">
                                <p class="category">{{ app.category }}</p>
                                <h3><a href="{{ app.link }}" target="_blank" rel="noopener noreferrer">{{ app.name }}</a></h3>
                                <p class="description">{{ app.desc }}</p>
                                {% if app.alt %}<div class="alternatives"><strong>Alternatives:</strong> 
                                {% for alt in app.alt %}
                                {{ alt.name }}{% if not loop.last %}, {% endif %}
                                {% endfor %}
                                </div>{% endif %}
                                <div class="app-links">
                                    {% if app.repo_link %}<a href="{{ app.repo_link }}" target="_blank" rel="noopener noreferrer">⭐ {{ app.stars }} Stars</a>{% endif %}
                                    <a href="{{ app.ns8_link }}" target="_blank" rel="noopener noreferrer">NS8 Module</a>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                    </section>
                    {% endfor %}
                </main>
                <footer>
                    <p>This page is generated from the <a href="https://github.com/geniusdynamics/ns8-genforge/blob/main/README.md" target="_blank" rel="noopener noreferrer">README.md</a> on GitHub.</p>
                </footer>
            </div>
        </div>
        <script>
            document.getElementById('search-input').addEventListener('input', function(e) {
                const searchTerm = e.target.value.toLowerCase();
                document.querySelectorAll('.app-card').forEach(card => {
                    const appName = card.dataset.name;
                    if (appName.includes(searchTerm)) {
                        card.style.display = '';
                    } else {
                        card.style.display = 'none';
                    }
                });
            });
        </script>
    </body>
    </html>
    ''')

    return html_template.render(timestamp=timestamp, categories=categories, cards=cards)


def generate_html(cards):
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    categories = sorted(list(set(card['category'] for card in cards)))

    html_template = Template(r'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GenForge App Directory</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary-color: #0366d6;
                --background-color: #f6f8fa;
                --card-background: #ffffff;
                --text-color: #24292e;
                --subtle-text-color: #586069;
                --border-color: #e1e4e8;
                --shadow-color: rgba(0, 0, 0, 0.1);
            }
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                margin: 0;
                background-color: var(--background-color);
                color: var(--text-color);
            }
            .container {
                display: flex;
            }
            .sidebar {
                width: 250px;
                background-color: var(--card-background);
                border-right: 1px solid var(--border-color);
                padding: 20px;
                height: 100vh;
                position: fixed;
                overflow-y: auto;
                transition: transform 0.3s ease;
            }
            .sidebar h2 {
                font-size: 1.5em;
                color: var(--primary-color);
                margin-top: 0;
            }
            .sidebar ul {
                list-style: none;
                padding: 0;
            }
            .sidebar li {
                margin-bottom: 10px;
            }
            .sidebar a {
                text-decoration: none;
                color: var(--subtle-text-color);
                font-weight: 600;
            }
            .sidebar a:hover {
                color: var(--primary-color);
            }
            .main-content {
                margin-left: 270px;
                padding: 20px;
                width: calc(100% - 270px);
            }
            header {
                text-align: center;
                margin-bottom: 40px;
            }
            header h1 {
                font-size: 3em;
                color: var(--primary-color);
                margin: 0;
            }
            header p {
                color: var(--subtle-text-color);
                margin-top: 5px;
            }
            .about-section {
                background-color: var(--card-background);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 40px;
            }
            .about-section details {
                cursor: pointer;
            }
            .about-section summary {
                font-weight: 600;
                color: var(--primary-color);
            }
            .search-container {
                margin-bottom: 40px;
            }
            #search-input {
                width: 100%;
                padding: 15px;
                font-size: 1.2em;
                border: 1px solid var(--border-color);
                border-radius: 8px;
            }
            .app-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 24px;
            }
            .app-card {
                background: var(--card-background);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 20px;
                display: flex;
                flex-direction: column;
                transition: transform 0.2s, box-shadow 0.2s;
                box-shadow: 0 2px 4px var(--shadow-color);
            }
            .app-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 6px 12px var(--shadow-color);
            }
            .app-card h3 {
                margin: 0 0 10px 0;
                font-size: 1.8em;
            }
            .app-card h3 a {
                color: var(--text-color);
                text-decoration: none;
                font-weight: 700;
            }
            .app-card .category {
                font-size: 0.9em;
                font-weight: 600;
                color: var(--primary-color);
                margin-bottom: 15px;
            }
            .app-card .description {
                flex-grow: 1;
                color: var(--subtle-text-color);
                margin-bottom: 15px;
            }
            .app-links {
                margin-top: 15px;
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
            }
            .app-links a {
                padding: 8px 12px;
                font-size: 0.9em;
                background-color: var(--primary-color);
                color: white;
                text-decoration: none;
                border-radius: 6px;
                display: inline-flex;
                align-items: center;
                gap: 5px;
            }
            footer {
                text-align: center;
                padding: 20px;
                margin-top: 40px;
                font-size: 0.9em;
                color: var(--subtle-text-color);
                border-top: 1px solid var(--border-color);
            }
            @media (max-width: 768px) {
                .container {
                    flex-direction: column;
                }
                .sidebar {
                    position: static;
                    width: 100%;
                    height: auto;
                    border-right: none;
                    border-bottom: 1px solid var(--border-color);
                }
                .main-content {
                    margin-left: 0;
                    width: 100%;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <nav class="sidebar">
                <h2>Categories</h2>
                <ul>
                    {% for category in categories %}
                    <li><a href="#{{ category.lower().replace(' ', '-') }}">{{ category }}</a></li>
                    {% endfor %}
                </ul>
            </nav>
            <div class="main-content">
                <header>
                    <h1>GenForge App Directory</h1>
                    <p>Last updated: {{ timestamp }}</p>
                    <p>Metadata are built every 4 hours at 00:25, 06:25 ,12:25, 18:25 UTC and on each commit to the main branch.</p>
                </header>
                <div class="about-section">
                    <details>
                        <summary>About this page and how to contribute</summary>
                        <p>If you want to add a module to this repository, just follow the
 <a href="https://nethserver.github.io/ns8-core/modules/new_module/#step-5-publish-to-ns8-software-repository">
  instructions
 </a>
 for
 <code>
  ns8-repomd
 </code>
 , finally open the pull request here!</p>
                    </details>
                </div>
                <main>
                    <div class="search-container">
                        <input type="text" id="search-input" placeholder="Search for applications...">
                    </div>
                    {% for category in categories %}
                    <section class="category-section" id="{{ category.lower().replace(' ', '-') }}">
                        <h2>{{ category }}</h2>
                        <div class="app-grid">
                            {% for app in cards if app.category == category %}
                            <div class="app-card" data-name="{{ app.name.lower() }}" data-category="{{ app.category.lower() }}">
                                <p class="category">{{ app.category }}</p>
                                <h3><a href="{{ app.link }}" target="_blank" rel="noopener noreferrer">{{ app.name }}</a></h3>
                                <p class="description">{{ app.desc }}</p>
                                {% if app.alt %}<div class="alternatives"><strong>Alternatives:</strong>
                                {% for alt in app.alt %}
                                <a href="{{ alt.link }}" target="_blank" rel="noopener noreferrer">{{ alt.name }}</a>{% if not loop.last %}, {% endif %}
                                {% endfor %}
                                </div>{% endif %}
                                <div class="app-links">
                                    {% if app.repo_link %}<a href="{{ app.repo_link }}" target="_blank" rel="noopener noreferrer">⭐ {{ app.stars }} Stars</a>{% endif %}
                                    <a href="{{ app.ns8_link }}" target="_blank" rel="noopener noreferrer">NS8 Module</a>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                    </section>
                    {% endfor %}
                </main>
                <footer>
                    <p>This page is generated from the <a href="https://github.com/geniusdynamics/ns8-genforge/blob/main/README.md" target="_blank" rel="noopener noreferrer">README.md</a> on GitHub.</p>
                </footer>
            </div>
        </div>
        <script>
            document.getElementById('search-input').addEventListener('input', function(e) {
                const searchTerm = e.target.value.toLowerCase();
                document.querySelectorAll('.app-card').forEach(card => {
                    const appName = card.dataset.name;
                    if (appName.includes(searchTerm)) {
                        card.style.display = '';
                    } else {
                        card.style.display = 'none';
                    }
                });
            });
        </script>
    </body>
    </html>
    ''')

    return html_template.render(timestamp=timestamp, categories=categories, cards=cards)


def generate_index_main():
    readme_path = Path("README.md")
    output_path = Path("index.html")

    if not readme_path.exists():
        print("❌ README.md not found")
        return

    try:
        readme_content = readme_path.read_text(encoding="utf-8")
        cards = parse_readme_tables(readme_content)
        if not cards:
            print("⚠️ No application cards were parsed from the README. The output file will be empty.")
        
        html_output = generate_html(cards)
        output_path.write_text(html_output, encoding="utf-8")
        print(f"✅ index.html generated successfully with {len(cards)} apps.")

    except Exception as e:
        print(f"❌ An error occurred: {e}")


if __name__ == '__main__':
    generate_index_main()
