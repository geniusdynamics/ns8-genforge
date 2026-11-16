#!/usr/bin/env python3

#
# Copyright (C) 2026 Genius Dynamics
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Build catalog.json, the extra data shown by the GenForge website.

repodata.json stays the only file NethServer reads. catalog.json adds what
the website shows on top of it: GitHub stars, release dates, the quality
score used by the NS8 App Index, and the ns8-* repositories of the
organization that are not published in the forge yet.

The quality checks follow https://github.com/NethServer/ns8-apps.
Only the Python standard library is needed.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

API = "https://api.github.com"
MIN_DESCRIPTION = 60
# Categories the NS8 Software Center knows (ns8-core software_center.app_categories).
STANDARD_CATEGORIES = {"core", "development", "collaboration", "system_administration", "office", "documentation",
                       "database", "storage", "monitoring", "web", "communication", "security", "multimedia"}
CATEGORY_ALIASES = {"system": "system_administration", "audio": "multimedia"}


def log(*args):
    print(*args, file=sys.stderr)


def github_get(path, token):
    """Return the decoded JSON answer, or None when the call fails."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "ns8-forge-site-builder"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(API + path, headers=headers), timeout=30) as res:
            return json.load(res)
    except urllib.error.HTTPError as ex:
        if ex.code != 404:
            log(f"[WARNING] GitHub API {path}: HTTP {ex.code}")
    except Exception as ex:
        log(f"[WARNING] GitHub API {path}: {ex}")
    return None


def org_repos(org, token):
    """Every public repository of the organization, keyed by lower-case name."""
    repos = {}
    for page in range(1, 11):
        batch = github_get(f"/orgs/{org}/repos?type=public&per_page=100&page={page}", token)
        if not batch:
            break
        for repo in batch:
            repos[repo["name"].lower()] = repo
        if len(batch) < 100:
            break
    return repos


def repo_name(code_url, org):
    """ns8-foo from https://github.com/<org>/ns8-foo/, or None for another owner."""
    match = re.match(r"https://github\.com/([^/]+)/([^/#?]+)", (code_url or "").strip(), re.I)
    if not match or match.group(1).lower() != org.lower():
        return None
    return match.group(2).removesuffix(".git").lower()


def is_testing(tag):
    return "-" in tag


def version_key(tag):
    main, _, pre = tag.lstrip("vV").partition("-")
    nums = tuple(int(n) for n in re.findall(r"\d+", main)[:4])
    return nums, 0 if pre else 1, tuple(int(n) for n in re.findall(r"\d+", pre))


def shown_version(app):
    """The version the website shows: the newest stable one, else the newest testing one."""
    tags = sorted((v["tag"] for v in app.get("versions") or [] if v.get("tag")), key=version_key, reverse=True)
    stable = next((t for t in tags if not is_testing(t)), None)
    return stable or (tags[0] if tags else None)


def quality_checks(app, repo, tag):
    """The nine checks of the NS8 App Index quality score."""
    description = app.get("description") or {}
    if isinstance(description, str):
        description = {"en": description}
    description = {k: v for k, v in description.items() if v}
    categories = [CATEGORY_ALIASES.get(c.lower(), c.lower()) for c in app.get("categories") or []]
    docs = app.get("docs") or {}
    labels = next((v.get("labels") or {} for v in app.get("versions") or [] if v.get("tag") == tag), {})
    return {
        "topic": "ns8" in ((repo or {}).get("topics") or []),
        "categories": bool(categories) and all(c in STANDARD_CATEGORIES for c in categories),
        "logo": bool(app.get("logo")),
        "screenshots": bool(app.get("screenshots")),
        "description": len(description.get("en", "")) >= MIN_DESCRIPTION,
        "translations": len(description) > 1,
        "docs": bool(docs.get("documentation_url")) and bool(docs.get("bug_url")),
        "min_core": bool(labels.get("org.nethserver.min-core")),
        "license": bool((repo or {}).get("license")),
    }


def readme_rows(readme_path, org):
    """Upstream project and alternatives from the README tables, keyed by module repository name."""
    rows = {}
    try:
        text = open(readme_path, encoding="utf-8").read()
    except OSError:
        return rows
    link = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
    for line in text.splitlines():
        if not line.startswith("| **"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 6:
            continue
        name = repo_name(next((u for _, u in link.findall(cols[5])), None), org)
        if not name:
            continue
        upstream = link.search(cols[1])
        upstream_repo = re.search(r"\]\((https://github\.com/[^)\s]+)\)\s*$", cols[3])
        rows[name] = {
            "label": cols[0].strip("* "),
            "upstream_name": upstream.group(1) if upstream else cols[1],
            "upstream_url": upstream.group(2) if upstream else None,
            "upstream_repo": upstream_repo.group(1) if upstream_repo else None,
            "summary": cols[2],
            "alternatives": [{"name": n, "url": u} for n, u in link.findall(cols[4])],
        }
    return rows


def release_info(org, name, tag, token):
    """Publication date of the release that carries the tag."""
    release = github_get(f"/repos/{org}/{name}/releases/tags/{tag}", token)
    return (release or {}).get("published_at")


def latest_release(org, name, token):
    releases = github_get(f"/repos/{org}/{name}/releases?per_page=1", token)
    if not releases:
        return None
    rel = releases[0]
    return {"tag": rel.get("tag_name"), "prerelease": bool(rel.get("prerelease")) or is_testing(rel.get("tag_name") or ""),
            "published_at": rel.get("published_at")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repodata", default="repodata.json")
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--config", default="site.json")
    parser.add_argument("--output", default="catalog.json")
    parser.add_argument("--skip-upstream", action="store_true", help="Build without upstream registry/release checks")
    parser.add_argument("--upstream-config", default="upstream.json", help="Optional main-image and application-version mappings")
    parser.add_argument("--org-repos", help="JSON file with the repository list, to build without the GitHub API")
    args = parser.parse_args()

    cfg = json.load(open(args.config))
    org = cfg["org"]
    forge_repo = cfg.get("forge_repo", "")
    tools = {t.lower() for t in cfg.get("tools") or []}
    exclude = {t.lower() for t in cfg.get("exclude") or []} | {forge_repo.lower()}
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    offline = bool(args.org_repos)

    repodata = json.load(open(args.repodata))
    if offline:
        repos = {r["name"].lower(): r for r in json.load(open(args.org_repos))}
    else:
        repos = org_repos(org, token)
    if not repos:
        log("[WARNING] no repository information: stars, licenses and unpublished modules are left out")
    rows = readme_rows(args.readme, org)

    def published(app):
        name = repo_name((app.get("docs") or {}).get("code_url"), org)
        repo = repos.get(name) if name else None
        tag = shown_version(app)
        row = rows.get(name) or {}
        checks = quality_checks(app, repo, tag)
        return name, {
            "id": app["id"],
            "repo": repo["html_url"] if repo else None,
            "stars": (repo or {}).get("stargazers_count"),
            "pushed_at": (repo or {}).get("pushed_at"),
            "archived": bool((repo or {}).get("archived")),
            "license": ((repo or {}).get("license") or {}).get("spdx_id"),
            "released_at": release_info(org, repo["name"], tag, token) if repo and tag and not offline else None,
            "checks": checks,
            "score": sum(checks.values()),
            "upstream_name": row.get("upstream_name"),
            "upstream_url": row.get("upstream_url"),
            "upstream_repo": row.get("upstream_repo"),
            "alternatives": row.get("alternatives") or [],
        }

    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(published, repodata))
    apps = [entry for _, entry in results]
    published_names = {name for name, _ in results if name}

    # Optional website enrichment must never prevent publication of the existing catalog.
    try:
        from upstream import enrich
        upstream_cfg = json.load(open(args.upstream_config)) if os.path.isfile(args.upstream_config) else {}
        enrich(apps, repodata, upstream_cfg, github_get, token, shown_version, offline=offline or args.skip_upstream)
    except Exception as ex:
        log(f"[WARNING] upstream checks unavailable: {type(ex).__name__}")

    def unpublished(repo):
        name = repo["name"]
        row = rows.get(name.lower()) or {}
        release = None if offline else latest_release(org, name, token)
        return {
            "name": name,
            "title": row.get("upstream_name") or name.removeprefix("ns8-"),
            "url": repo["html_url"],
            "description": row.get("summary") or repo.get("description") or "",
            "stars": repo.get("stargazers_count", 0),
            "pushed_at": repo.get("pushed_at"),
            "license": (repo.get("license") or {}).get("spdx_id"),
            "release": release,
            # A release means images were built, the module only lacks an entry in the forge.
            "status": "built" if release else "development",
            "upstream_url": row.get("upstream_url"),
            "alternatives": row.get("alternatives") or [],
        }

    pending = [r for n, r in sorted(repos.items())
               if n.startswith("ns8-") and n not in published_names and n not in exclude
               and not r.get("archived") and not r.get("private") and not r.get("fork")]
    with ThreadPoolExecutor(8) as pool:
        entries = list(pool.map(unpublished, pending))
    development = [e for e in entries if e["name"].lower() not in tools]
    tool_list = [e for e in entries if e["name"].lower() in tools]
    for e in tool_list:
        e["status"] = "tool"

    catalog = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "org": org,
        "forge_repo": f"{org}/{forge_repo}",
        "domain": cfg.get("domain"),
        "apps": apps,
        "development": sorted(development, key=lambda e: e["pushed_at"] or "", reverse=True),
        "tools": tool_list,
    }
    with open(args.output, "w", encoding="utf-8") as out:
        json.dump(catalog, out, ensure_ascii=False, indent=1)
        out.write("\n")
    log(f"wrote {args.output}: {len(apps)} published, {len(development)} unpublished, {len(tool_list)} tools")


if __name__ == "__main__":
    main()
