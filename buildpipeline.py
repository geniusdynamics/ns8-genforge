#!/usr/bin/env python3

#
# Copyright (C) 2026 Genius Dynamics
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Build pipeline.json, the CI state shown by the "Pipeline" dialog of the website.

For each ns8-* module of the organization that has a "Test module" workflow,
it reports the release group, the dev commit, the "Publish images" run of that
commit, the QEMU test of dev that followed it, the latest QEMU test of main,
the open pull requests to dev and from dev to main, how far dev is ahead of
main, and the next step.

Everything it writes is public data read from the GitHub REST API.
Only the Python standard library is needed.
"""

import argparse
import json
import os
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

API = "https://api.github.com"
TEST_WORKFLOW = "test-module.yml"        # workflow "Test module"
PUBLISH_WORKFLOW = "publish-images.yml"  # workflow "Publish images"
TEST_DEV = "Test dev on QEMU"
TEST_MAIN = "Test main on QEMU"
# Stop calling the API when fewer requests than this are left, so other jobs keep working.
RESERVE = 50

STABLE, TESTING, UNRELEASED = "stable", "testing", "unreleased"
GROUPS = {STABLE: "Stable release", TESTING: "Testing release", UNRELEASED: "Not released"}


def log(*args):
    print(*args, file=sys.stderr)


class ApiError(Exception):
    pass


class GitHub:
    """A small REST client that counts its calls and watches the rate limit."""

    def __init__(self, token):
        self.token = token
        self.calls = 0
        self.remaining = None
        self.lock = threading.Lock()

    def get(self, path):
        """Return the decoded JSON answer, None for HTTP 404, or raise ApiError."""
        with self.lock:
            if self.remaining is not None and self.remaining < RESERVE:
                raise ApiError("rate limit reserve reached, skipped")
            self.calls += 1
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "ns8-forge-pipeline-builder",
                   "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            with urllib.request.urlopen(urllib.request.Request(API + path, headers=headers), timeout=30) as res:
                self._track(res.headers)
                return json.load(res)
        except urllib.error.HTTPError as ex:
            self._track(ex.headers)
            if ex.code == 404:
                return None
            raise ApiError(f"HTTP {ex.code} on {path.split('?')[0]}") from None
        except (urllib.error.URLError, TimeoutError, ValueError) as ex:
            raise ApiError(f"{type(ex).__name__} on {path.split('?')[0]}") from None

    def _track(self, headers):
        value = (headers or {}).get("X-RateLimit-Remaining")
        if value and value.isdigit():
            with self.lock:
                self.remaining = int(value)


def org_repos(gh, org):
    """Every public repository of the organization."""
    repos = []
    for page in range(1, 11):
        batch = gh.get(f"/orgs/{org}/repos?type=public&per_page=100&page={page}") or []
        repos.extend(batch)
        if len(batch) < 100:
            break
    return repos


def run_state(run):
    """One word for a workflow run: passed, failed, running, queued, cancelled, skipped..., or none."""
    if not run or not run.get("status"):
        return "none"
    status, conclusion = run["status"], run.get("conclusion")
    if status != "completed":
        return "running" if status == "in_progress" else "queued"
    return {"success": "passed", "failure": "failed", "timed_out": "failed", "startup_failure": "failed"}.get(
        conclusion, conclusion or "unknown")


def run_info(run):
    if not run:
        return None
    return {"status": run_state(run), "url": run.get("html_url"), "created_at": run.get("created_at")}


def pick_dev_test(test_runs, publish_run):
    """The QEMU test of the current dev commit.

    "Test module" runs on the default branch (workflow_run), so its head_sha is
    not the dev one: take the runs named "Test dev on QEMU" started after the
    publish run of the dev commit, and prefer the latest one that was not
    skipped, since a re-run after a skipped run is the one that counts.
    """
    if not publish_run:
        return None
    since = publish_run.get("created_at") or ""
    candidates = sorted((r for r in test_runs if r.get("display_title") == TEST_DEV and (r.get("created_at") or "") >= since),
                        key=lambda r: r.get("created_at") or "")
    if not candidates:
        return None
    real = [r for r in candidates if r.get("conclusion") != "skipped"]
    return real[-1] if real else candidates[0]


def pick_main_test(test_runs):
    """The latest "Test main on QEMU" run."""
    runs = [r for r in test_runs if r.get("display_title") == TEST_MAIN]
    return max(runs, key=lambda r: r.get("created_at") or "", default=None)


def release_group(releases):
    """stable when a published release is not a pre-release, testing with only pre-releases, else unreleased."""
    published = [r for r in releases or [] if not r.get("draft")]
    if any(not r.get("prerelease") for r in published):
        return STABLE
    return TESTING if published else UNRELEASED


def overall(publish, test):
    """The bucket used by the dashboard summary: passed, failed, running or none."""
    if "failed" in (publish, test):
        return "failed"
    if publish in ("running", "queued") or test in ("running", "queued"):
        return "running"
    return "passed" if test == "passed" else "none"


def next_step(group, publish, test, prs_to_dev, prs_to_main, ahead):
    if prs_to_dev:
        return "Merge the open PR to dev once its checks pass"
    if publish in ("queued", "running"):
        return "Waiting for Publish images"
    if publish == "failed":
        return "Fix the image build on dev"
    if publish == "none":
        return "Run Publish images on the dev commit"
    if test == "none" and publish == "passed":
        return "Waiting for the QEMU test of the current dev"
    if test in ("queued", "running"):
        return "Waiting for Test dev on QEMU"
    if test == "failed":
        return "Fix the failing QEMU test on dev"
    if test == "passed" and prs_to_main:
        return "Release owner merges the PR to main" if group == STABLE else "Merge the PR to main"
    if test == "passed":
        return "Nothing to promote" if not ahead else "Open the PR to main"
    return "Waiting for the test run"


def pr_info(pr):
    return {"number": pr.get("number"), "url": pr.get("html_url"), "title": pr.get("title"),
            "head": (pr.get("head") or {}).get("ref"), "draft": bool(pr.get("draft"))}


def module_row(gh, org, repo):
    """The pipeline row of one repository, or None when it has no "Test module" workflow."""
    name = repo["name"]
    base = f"/repos/{org}/{name}"
    # 1. The test runs; a 404 means the repository has no "Test module" workflow.
    tests = gh.get(f"{base}/actions/workflows/{TEST_WORKFLOW}/runs?per_page=100&exclude_pull_requests=true")
    if tests is None:
        return None
    test_runs = tests.get("workflow_runs") or []
    row = {"name": name, "module": name.removeprefix("ns8-"), "repo": repo.get("html_url") or f"https://github.com/{org}/{name}",
           "group": UNRELEASED, "release": None, "dev_sha": None, "dev_publish": None, "dev_test": None,
           "main_test": run_info(pick_main_test(test_runs)), "prs_to_dev": [], "prs_to_main": [],
           "dev_ahead_of_main": None, "status": "none", "next_step": "", "error": None}
    try:
        # 2. Releases give the group.
        releases = gh.get(f"{base}/releases?per_page=100") or []
        row["group"] = release_group(releases)
        latest = next((r for r in releases if not r.get("draft")), None)
        if latest:
            row["release"] = {"tag": latest.get("tag_name"), "url": latest.get("html_url"), "prerelease": bool(latest.get("prerelease"))}
        # 3. The comparison gives how far dev is ahead and the dev commit itself.
        compare = gh.get(f"{base}/compare/main...dev")
        dev_sha = None
        if compare:
            row["dev_ahead_of_main"] = compare.get("ahead_by")
            commits = compare.get("commits") or []
            if not compare.get("ahead_by"):
                dev_sha = (compare.get("merge_base_commit") or {}).get("sha")  # dev is contained in main
            elif len(commits) >= compare["ahead_by"]:
                dev_sha = commits[-1].get("sha")
        if not dev_sha:
            dev_sha = (gh.get(f"{base}/commits/dev") or {}).get("sha")
        row["dev_sha"] = dev_sha
        # 4. The publish run of that commit.
        publish_run = None
        if dev_sha:
            query = urllib.parse.urlencode({"branch": "dev", "head_sha": dev_sha, "per_page": 5})
            runs = (gh.get(f"{base}/actions/workflows/{PUBLISH_WORKFLOW}/runs?{query}") or {}).get("workflow_runs") or []
            publish_run = max(runs, key=lambda r: r.get("created_at") or "", default=None)
        row["dev_publish"] = run_info(publish_run)
        row["dev_test"] = run_info(pick_dev_test(test_runs, publish_run))
        # 5. Open pull requests.
        pulls = gh.get(f"{base}/pulls?state=open&per_page=100") or []
        row["prs_to_dev"] = [pr_info(p) for p in pulls if (p.get("base") or {}).get("ref") == "dev"]
        row["prs_to_main"] = [pr_info(p) for p in pulls if (p.get("base") or {}).get("ref") == "main"
                              and (p.get("head") or {}).get("ref") == "dev"]
    except ApiError as ex:
        row["error"] = str(ex)
    publish = (row["dev_publish"] or {}).get("status", "none")
    test = (row["dev_test"] or {}).get("status", "none")
    row["status"] = "error" if row["error"] else overall(publish, test)
    row["next_step"] = "Check the error and run again" if row["error"] else \
        next_step(row["group"], publish, test, row["prs_to_dev"], row["prs_to_main"], row["dev_ahead_of_main"])
    return row


def safe_row(gh, org, repo):
    """A failure in one repository is recorded on its row and never stops the run."""
    try:
        return module_row(gh, org, repo)
    except Exception as ex:
        log(f"[WARNING] {repo.get('name')}: {ex}")
        return {"name": repo.get("name"), "module": (repo.get("name") or "").removeprefix("ns8-"),
                "repo": repo.get("html_url"), "group": UNRELEASED, "release": None, "dev_sha": None,
                "dev_publish": None, "dev_test": None, "main_test": None, "prs_to_dev": [], "prs_to_main": [],
                "dev_ahead_of_main": None, "status": "error", "next_step": "Check the error and run again",
                "error": str(ex) if isinstance(ex, ApiError) else type(ex).__name__}


def candidates(repos, cfg):
    skip = {t.lower() for t in (cfg.get("tools") or []) + (cfg.get("exclude") or [])}
    skip.add((cfg.get("forge_repo") or "").lower())
    return sorted((r for r in repos if r["name"].lower().startswith("ns8-") and r["name"].lower() not in skip
                   and not r.get("archived") and not r.get("private") and not r.get("fork")),
                  key=lambda r: r["name"].lower())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="site.json")
    parser.add_argument("--output", default="pipeline.json")
    parser.add_argument("--org-repos", help="JSON file with the repository list, instead of listing the organization")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    cfg = json.load(open(args.config))
    org = cfg["org"]
    gh = GitHub(os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN"))
    if args.org_repos:
        repos = json.load(open(args.org_repos))
    else:
        try:
            repos = org_repos(gh, org)
        except ApiError as ex:
            log(f"[ERROR] cannot list the repositories of {org}: {ex}")
            return 1
    todo = candidates(repos, cfg)
    with ThreadPoolExecutor(args.workers) as pool:
        rows = [r for r in pool.map(lambda repo: safe_row(gh, org, repo), todo) if r]

    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    pipeline = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "org": org,
        "groups": GROUPS,
        "counts": counts,
        "api_calls": gh.calls,
        "modules": rows,
    }
    with open(args.output, "w", encoding="utf-8") as out:
        json.dump(pipeline, out, ensure_ascii=False, indent=1)
        out.write("\n")
    errors = counts.get("error", 0)
    log(f"wrote {args.output}: {len(rows)} modules of {len(todo)} repositories, {errors} with errors, "
        f"{gh.calls} API calls, {gh.remaining if gh.remaining is not None else '?'} left")
    return 0


if __name__ == "__main__":
    sys.exit(main())
