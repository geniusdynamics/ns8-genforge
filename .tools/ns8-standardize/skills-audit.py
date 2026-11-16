#!/usr/bin/env python3
"""Check modules against the 'Always applies' rules of the NethServer ns8-module skill (read only)."""
import glob
import json
import os
import re
import subprocess
from collections import defaultdict

BR = "claude/relaxed-allen-kitkqz"
rows = json.load(open("/tmp/claude-0/scratchpad/batch/status.json"))["rows"]
SECRET = re.compile(r"(PASS(WORD)?|SECRET|TOKEN|_KEY\b|APIKEY|API_KEY|PEPPER)", re.I)
out = {}
for r in rows:
    m = r["module"]
    repo = f"/home/user/ns8-{m}"
    if not os.path.isdir(repo):
        continue
    subprocess.run(["git", "-C", repo, "checkout", "-q", BR], capture_output=True)
    f = defaultdict(list)
    ir = f"{repo}/imageroot"
    files = [p for p in glob.glob(ir + "/**/*", recursive=True) if os.path.isfile(p)]

    def rd(p):
        try:
            return open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            return ""
    for p in files:
        s = rd(p)
        rel = os.path.relpath(p, repo)
        # rule: never store secrets with agent.set_env()
        for mm in re.finditer(r"(?m)^[^#\n]*?set_env\(\s*['\"]([A-Z0-9_]+)['\"]", s):
            if SECRET.search(mm.group(1)) and not mm.group(1).startswith("TRAEFIK"):
                f["secret in set_env"].append(f"{rel}: {mm.group(1)}")
        # hard-coded credentials
        for mm in re.finditer(r"(Nethesis,1234|postgrespass123|your_[a-z_]*password|H733Kdjndks81|['\"]password['\"]\s*\)|PASSWORD=(?!\$)[A-Za-z0-9,]{4,}\b)", s):
            if "/tests/" in p:
                continue
            f["hard-coded credential"].append(f"{rel}: {mm.group(0)[:40]}")
        # bash actions must log to stderr
        if "/actions/" in p and s.startswith("#!/bin/bash") and "exec 1>&2" not in s and re.search(r"\becho\b|\bprintf\b", s):
            f["bash action may print to stdout"].append(rel)
    # pod master must list every child unit
    units = sorted(os.path.basename(p) for p in glob.glob(ir + "/systemd/user/*.service"))
    pod = f"{ir}/systemd/user/{m}.service"
    pods = [p for p in glob.glob(ir + "/systemd/user/*.service") if "pod create" in rd(p)]
    for pp in pods:
        s = rd(pp)
        req = " ".join(re.findall(r"^(?:Requires|Wants)=(.*)$", s, re.M))
        for u in units:
            if u == os.path.basename(pp) or u.endswith("@.service"):
                continue
            us = rd(f"{ir}/systemd/user/{u}")
            if os.path.basename(pp) in us and "pod-id-file" in us and u not in req:
                f["pod unit does not require child"].append(f"{os.path.basename(pp)} -> {u}")
    # restore must pass every var copied by 06copyenv
    ce = glob.glob(ir + "/actions/restore-module/06*")
    cc = glob.glob(ir + "/actions/restore-module/50*")
    if ce and cc:
        copied = set(re.findall(r'"([A-Z][A-Z0-9_]+)"', rd(ce[0])))
        used = set(re.findall(r'\[\s*["\']([A-Z][A-Z0-9_]+)["\']\s*\]', rd(cc[0])))
        miss = sorted(v for v in copied - used if v.startswith("TRAEFIK") is False)
        if miss:
            f["restore does not pass copied vars to configure"].append(", ".join(miss))
    # floating image tags
    bi = rd(f"{repo}/build-images.sh")
    live = "\n".join(l for l in bi.splitlines() if not l.lstrip().startswith("#"))
    lab = re.search(r'org\.nethserver\.images=([^"]*)"', live)
    shv = dict(re.findall(r'^\s*([A-Za-z_]\w*)="?([^"\s]*)"?\s*$', live, re.M))
    if lab:
        for tok in lab.group(1).split():
            ex = re.sub(r"\$\{(\w+)\}", lambda x: shv.get(x.group(1), x.group(0)), tok)
            tag = ex.rsplit(":", 1)[1] if ":" in ex.split("/")[-1] else "latest"
            if tag in ("latest", "lts", "main", "master", "stable", "dev") or re.fullmatch(r"\d+", tag):
                f["floating image tag"].append(ex)
    # backup list exists
    if not os.path.exists(f"{ir}/etc/state-include.conf"):
        f["no state-include.conf"].append("")
    out[m] = {k: v for k, v in f.items()}

json.dump(out, open("/tmp/claude-0/scratchpad/batch/skills-audit.json", "w"), indent=1)
cnt = defaultdict(list)
for m, f in out.items():
    for k in f:
        cnt[k].append(m)
for k, ms in sorted(cnt.items(), key=lambda x: -len(x[1])):
    print(f"{len(ms):3d}  {k}: {' '.join(ms)}")
