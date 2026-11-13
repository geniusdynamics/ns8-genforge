#!/usr/bin/env python3
"""Audit every module against the NS8 kickstart layout and the ns8-apps quality checks (read only)."""
import glob
import json
import os
import re
import subprocess
import sys
from collections import Counter

BR = "claude/relaxed-allen-kitkqz"
K = sorted(glob.glob("/tmp/ns8-kickstart-*"))[0]
STD_CATS = {"collaboration", "communication", "core", "database", "development", "documentation", "monitoring",
            "multimedia", "office", "security", "storage", "system_administration", "web"}
rows = json.load(open("/tmp/claude-0/scratchpad/batch/status.json"))["rows"]
forge = "/home/user/ns8-genforge"
forge_dirs = {}
for d in os.listdir(forge):
    mp = f"{forge}/{d}/metadata.json"
    if os.path.exists(mp):
        try:
            cu = json.load(open(mp)).get("docs", {}).get("code_url", "")
            forge_dirs[cu.rsplit("/ns8-", 1)[-1].lower()] = d
        except ValueError:
            pass


def show(repo, path, ref=BR):
    r = subprocess.run(["git", "-C", repo, "show", f"{ref}:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def exists(repo, path, ref=BR):
    return subprocess.run(["git", "-C", repo, "cat-file", "-e", f"{ref}:{path}"], capture_output=True).returncode == 0


kpkg = json.load(open(f"{K}/ui/package.json"))
kdeps = {**kpkg["dependencies"], **kpkg["devDependencies"]}
report = {}
for r in rows:
    m = r["module"]
    repo = f"/home/user/ns8-{m}"
    if not os.path.isdir(repo):
        report[m] = ["no local clone"]
        continue
    if subprocess.run(["git", "-C", repo, "rev-parse", "-q", "--verify", BR], capture_output=True).returncode != 0:
        report[m] = ["no branch"]
        continue
    miss = []
    for w in ["build-apidoc", "clean-apidoc", "publish-images", "test-module", "test-ui-build-renovate"]:
        t = show(repo, f".github/workflows/{w}.yml")
        if t is None:
            miss.append(f"workflow {w} missing")
        elif t != open(f"{K}/.github/workflows/{w}.yml").read():
            miss.append(f"workflow {w} differs from kickstart")
    for f in ["renovate.json", ".devcontainer/devcontainer.json", ".vscode/settings.json", "ui/.yarnrc.yml",
              "ui/Containerfile", "ui/vue.config.js", "ui/.eslintrc.js", "tests/__init__.robot", "LICENSE", "README.md",
              "imageroot/etc/state-include.conf"]:
        if not exists(repo, f):
            miss.append(f"{f} missing")
    for f in ["package.json", "test-module.sh", "tests/pythonreq.txt"]:
        if exists(repo, f):
            miss.append(f"legacy {f} still present")
    pk = show(repo, "ui/package.json")
    if pk:
        try:
            p = json.loads(pk)
            deps = {**p.get("dependencies", {}), **p.get("devDependencies", {})}
            old = [d for d, v in kdeps.items() if d in deps and deps[d] != v]
            if old:
                miss.append(f"ui deps differ from kickstart: {', '.join(old[:4])}{'…' if len(old) > 4 else ''}")
            if p.get("packageManager") != kpkg["packageManager"]:
                miss.append("ui packageManager differs")
        except ValueError:
            miss.append("ui/package.json unreadable")
    if not exists(repo, "ui/yarn.lock"):
        miss.append("ui/yarn.lock missing")
    bi = show(repo, "build-images.sh") or ""
    live = "\n".join(l for l in bi.splitlines() if not l.lstrip().startswith("#"))
    if "corepack" not in live:
        miss.append("build-images.sh: no Corepack install")
    if "node:lts" in live or re.search(r"node:\d+(\.\d+)*(?!-slim)\b(?!-)", live) and "-slim" not in live:
        miss.append("build-images.sh: node image not pinned to -slim")
    for lab in ["authorizations", "tcp-ports-demand", "rootfull", "images", "min-core"]:
        if f"org.nethserver.{lab}=" not in live:
            miss.append(f"label {lab} missing")
    if re.search(r"\b(latest|master|main|stable)\b", re.search(r'org\.nethserver\.images=([^"]*)"', live).group(1) if re.search(r'org\.nethserver\.images=([^"]*)"', live) else ""):
        miss.append("image label has a floating tag")
    # metadata
    md = show(repo, "ui/public/metadata.json")
    try:
        md = json.loads(md)
    except Exception:
        md = {}
    desc = md.get("description", {})
    if len(desc.get("en", "")) < 60 or desc.get("en", "").startswith(("My ", "Auto-generated")):
        miss.append("description.en under 60 chars or placeholder")
    if not [k for k in desc if k != "en"]:
        miss.append("description has no translation")
    cats = [c.lower() for c in md.get("categories", [])]
    if not cats or any(c not in STD_CATS for c in cats):
        miss.append(f"categories not standard: {md.get('categories')}")
    docs = md.get("docs", {})
    for k in ("documentation_url", "bug_url", "code_url"):
        if not docs.get(k):
            miss.append(f"docs.{k} empty")
    if re.search(r"example|docs\.(rocketchat|kickstart)", docs.get("documentation_url", "")) and False:
        pass
    # forge assets
    d = forge_dirs.get(m.lower())
    if r["group"] in ("Stable release", "Testing release"):
        if not d:
            miss.append("not in the forge folder list")
        else:
            if not os.path.exists(f"{forge}/{d}/logo.png"):
                miss.append("forge: no logo.png")
            if not glob.glob(f"{forge}/{d}/screenshots/*"):
                miss.append("forge: no screenshots")
    report[m] = miss

# topic check through the API (needs no auth for public repos)
topics = {}
for r in rows:
    m = r["module"]
    o = subprocess.run(["gh", "api", f"repos/geniusdynamics/ns8-{m}/topics", "--jq", ".names|join(\",\")"], capture_output=True, text=True).stdout.strip()
    topics[m] = o
    if "ns8" not in o.split(","):
        report.setdefault(m, []).append("GitHub topic ns8 missing")

json.dump({"report": report, "topics": topics}, open("/tmp/claude-0/scratchpad/batch/audit.json", "w"), indent=1)
c = Counter()
for m, items in report.items():
    for i in items:
        c[re.sub(r":.*", "", i) if i.startswith(("categories", "ui deps")) else i] += 1
for k, v in c.most_common():
    print(f"{v:3d}  {k}")
print("modules with no finding:", sum(1 for v in report.values() if not v), "of", len(report))
