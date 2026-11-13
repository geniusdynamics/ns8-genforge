#!/usr/bin/env python3
"""Apply the mechanical, module-agnostic part of the NS8 kickstart standards.

usage: ns8-standardize.py <module-repo-dir> [module-name] [--kickstart DIR] [--owner ORG]

Module-specific work (image pins, units, backup, tests, README) is NOT done
here. The script prints a TODO list of what still needs a human/agent look.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
ap.add_argument("repo", help="path of the module repository (ns8-<name>)")
ap.add_argument("name", nargs="?", help="module name; default: repo directory name without ns8-")
ap.add_argument("--kickstart", help="path of a NethServer/ns8-kickstart checkout; default: shallow clone")
ap.add_argument("--owner", default="geniusdynamics", help="GitHub organization of the module")
ap.add_argument("--author-name", default="Genius Dynamics")
ap.add_argument("--author-email", default="support@genius.ke")
ap.add_argument("--conservative", action="store_true",
                help="only workflows, tooling, UI toolchain, build script and test layout: no code, metadata or unit changes (for released modules)")
args = ap.parse_args()
repo = os.path.abspath(args.repo)
name = args.name or re.sub(r"^ns8-", "", os.path.basename(repo.rstrip("/")))
K = args.kickstart
if not K:
    K = tempfile.mkdtemp(prefix="ns8-kickstart-")
    subprocess.run(["git", "clone", "-q", "--depth", "1", "https://github.com/NethServer/ns8-kickstart", K], check=True)
todo = []


def p(*a):
    return os.path.join(repo, *a)


def read(path):
    with open(path) as f:
        return f.read()


def write(path, s):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(s)


def cp(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


# 1. workflows
for wf in ["build-apidoc", "clean-apidoc", "publish-images", "test-module", "test-ui-build-renovate"]:
    cp(f"{K}/.github/workflows/{wf}.yml", p(".github/workflows", wf + ".yml"))
write(p(".github/workflows/clean-registry.yml"),
      read(f"{K}/.github/workflows/clean-registry.yml").replace('images: "kickstart"', f'images: "{name}"'))

# 2. repo-level files
cp(f"{K}/renovate.json", p("renovate.json"))
cp(f"{K}/.vscode/settings.json", p(".vscode/settings.json"))
write(p(".devcontainer/devcontainer.json"),
      read(f"{K}/.devcontainer/devcontainer.json").replace("ns8-kickstart", f"ns8-{name}"))
for f in ["package.json", "test-module.sh", "tests/pythonreq.txt"]:
    if os.path.exists(p(f)):
        subprocess.run(["git", "-C", repo, "rm", "-q", "-f", f], check=False)

# 3. UI toolchain
for f in [".eslintrc.js", ".gitignore", "Containerfile", "vue.config.js", ".yarnrc.yml", ".env"]:
    cp(f"{K}/ui/{f}", p("ui", f))
if os.path.exists(p("ui/src/components/AppMobileSideMenu.vue")):
    cp(f"{K}/ui/src/components/AppMobileSideMenu.vue", p("ui/src/components/AppMobileSideMenu.vue"))
tpl = json.load(open(f"{K}/ui/package.json"))
pkg = json.load(open(p("ui/package.json")))
extra = [d for d in pkg.get("dependencies", {}) if d not in tpl["dependencies"]]
extra += [d for d in pkg.get("devDependencies", {}) if d not in tpl["devDependencies"]
          and d not in ("babel-eslint", "vue-template-compiler")]
for sect in ("dependencies", "devDependencies"):
    merged = dict(tpl[sect])
    for d, v in pkg.get(sect, {}).items():
        if d not in merged and d not in ("babel-eslint", "vue-template-compiler"):
            merged[d] = v  # module-specific dependency, kept as is
    pkg[sect] = dict(sorted(merged.items()))
pkg["scripts"] = tpl["scripts"]
pkg["packageManager"] = tpl["packageManager"]
write(p("ui/package.json"), json.dumps(pkg, indent=2) + "\n")
if extra:
    todo.append(f"ui: module-specific dependencies kept, check they build: {extra}")
    # lockfile must be regenerated, run yarn install in ui/
else:
    cp(f"{K}/ui/yarn.lock", p("ui/yarn.lock"))
write(p("ui/README.md"), read(f"{K}/ui/README.md").replace("kickstart", name))

# 4. build-images.sh
bi = read(p("build-images.sh"))
if "corepack" not in bi:
    bi = re.sub(r'(reponame="[^"]*"\n)',
                r'\1# Node.js 25+ no longer ships Corepack, install it from npm\n'
                r'# renovate: datasource=npm packageName=corepack\ncorepack_version=0.36.0\n', bi, count=1)
    bi = re.sub(r'([ \t]*)(buildah from --name nodebuilder-(\S+) -v "\$\{PWD\}:/usr/src:Z" )docker\.io/library/node:\S+\n',
                lambda m: f'{m.group(1)}{m.group(2)}docker.io/library/node:26.13.0-slim\n'
                          f'{m.group(1)}buildah run nodebuilder-{m.group(3)} sh -c "npm install -g corepack@${{corepack_version}} && corepack enable"\n',
                bi, count=1)
    if "corepack enable" not in bi:
        todo.append("build-images.sh: node/corepack block not patched")
write(p("build-images.sh"), bi)
for m in re.finditer(r'org\.nethserver\.images=([^"]*)"', bi):
    todo.append("images label: " + m.group(1))
if "org.nethserver.authorizations" not in bi:
    todo.append("build-images.sh: no authorizations label")

# 5. tests
cp(f"{K}/tests/__init__.robot", p("tests/__init__.robot"))
if os.path.exists(p("tests/kickstart.robot")):
    if os.path.exists(p(f"tests/{name}.robot")):
        subprocess.run(["git", "-C", repo, "rm", "-q", "-f", "tests/kickstart.robot"], check=False)
    else:
        # keep the module's only suite: rename it after the module
        write(p(f"tests/{name}.robot"), read(p("tests/kickstart.robot")).replace("kickstart", name))
        subprocess.run(["git", "-C", repo, "rm", "-q", "-f", "tests/kickstart.robot"], check=False)
        todo.append(f"tests/kickstart.robot renamed to tests/{name}.robot: check the configure payload and URL check")
if not os.path.exists(p(f"tests/{name}.robot")) and not args.conservative:
    write(p(f"tests/{name}.robot"), read(f"{K}/tests/kickstart.robot").replace("kickstart", name))
    todo.append(f"tests/{name}.robot generated from template: set real configure payload and URL check")

# 6. metadata (only fill the template placeholders)
mp = p("ui/public/metadata.json")
if args.conservative:
    print("\n".join("TODO " + t for t in todo))
    sys.exit(0)
md = json.load(open(mp))
md["name"] = md.get("name") or name
md["authors"] = [{"name": args.author_name, "email": args.author_email}]
md.setdefault("docs", {})
md["docs"]["bug_url"] = f"https://github.com/{args.owner}/ns8-{name}/issues"
md["docs"]["code_url"] = f"https://github.com/{args.owner}/ns8-{name}"
md["source"] = f"ghcr.io/{args.owner}/{name}"
if md["docs"].get("documentation_url", "").startswith("https://docs.") and f"{name}.com" in md["docs"]["documentation_url"]:
    todo.append("metadata: documentation_url is a placeholder")
if not md.get("categories"):
    todo.append("metadata: categories empty (use standard categories)")
if len(md.get("description", {}).get("en", "")) < 60 or md["description"]["en"].startswith("My "):
    todo.append("metadata: description.en needs >= 60 real chars (+ it translation)")
write(mp, json.dumps(md, indent=2, ensure_ascii=False) + "\n")

# 7. report things the script cannot judge
for root, _, files in os.walk(p("imageroot/systemd")):
    for f in files:
        s = read(os.path.join(root, f))
        if "%S/state" in s:
            todo.append(f"{f}: uses %S/state, kickstart uses %E/state")
if os.path.exists(p("imageroot/bin/discover-smarthost")):
    todo.append("discover-smarthost still present: remove if the app does not use SMTP")
if re.search(r'set_env\([^)]*(PASSWORD|SECRET|TOKEN|KEY)', "".join(
        read(os.path.join(r, f)) for r, _, fs in os.walk(p("imageroot/actions")) for f in fs
        if not f.endswith(".json")), re.I):
    todo.append("secrets passed through agent.set_env(): move to state/passwords.env")
if not os.path.exists(p("imageroot/etc/state-include.conf")):
    todo.append("no etc/state-include.conf")
if not os.path.exists(p("ui/yarn.lock")) or extra:
    todo.append("run `yarn install` in ui/ to regenerate yarn.lock, then `yarn build`")
rd = read(p("README.md")) if os.path.exists(p("README.md")) else ""
if "template module" in rd or "Use this template" in rd:
    todo.append("README still has the template boilerplate")
# 8. fixes that are safe to apply automatically
for root, _, files in os.walk(p("imageroot/systemd")):
    for f in files:
        fp = os.path.join(root, f)
        s0 = read(fp)
        s1 = s0.replace("%S/state", "%E/state")
        if s1 != s0:
            write(fp, s1)
            todo.append(f"{f}: %S/state changed to %E/state (review the bind mounts that remain)")
for hook in ("bin/discover-smarthost", "events/smarthost-changed"):
    hp = p("imageroot", hook)
    if os.path.isdir(hp):
        shutil.rmtree(hp)
    elif os.path.exists(hp):
        os.remove(hp)
for root, _, files in os.walk(p("imageroot")):
    for f in files:
        fp = os.path.join(root, f)
        try:
            s0 = read(fp)
        except (UnicodeDecodeError, IsADirectoryError):
            continue
        if "smarthost" in s0:
            lines = [l for l in s0.splitlines(keepends=True) if "smarthost" not in l]
            write(fp, "".join(lines))
            todo.append(f"{os.path.relpath(fp, repo)}: smarthost lines removed, check the unit still starts")

# 9. image pins: floating tags and variables used but not in the label
bi_text = read(p("build-images.sh")) if os.path.exists(p("build-images.sh")) else ""
var_vals = dict(re.findall(r'^([a-z_]+_image)="([^"]+)"', bi_text, re.M))
label = re.search(r'org\.nethserver\.images=([^"]*)"', bi_text)
label_items = []
if label:
    for item in label.group(1).split():
        label_items.append(item)
for k, v in var_vals.items():
    if v not in label_items:
        pass
expanded = " ".join(var_vals.get(i[2:-1], i) if i.startswith("${") else i
                     for i in (label.group(1).split() if label else []))
for img in expanded.split():
    tag = img.rsplit(":", 1)[1] if ":" in img.split("/")[-1] else ""
    if tag in ("", "latest", "main", "stable", "lts") or re.fullmatch(r"\d+(\.\d+)?", tag or "x") \
            or tag.endswith("-alpine") and not re.search(r"\d", tag):
        todo.append(f"floating or partial image tag, pin a full version: {img}")
used = set()
for root, _, files in os.walk(p("imageroot")):
    for f in files:
        try:
            used |= set(re.findall(r"\$\{?([A-Z][A-Z0-9_]*_IMAGE)\}?", read(os.path.join(root, f))))
        except (UnicodeDecodeError, IsADirectoryError):
            pass
names = {os.path.basename(i.rsplit(":", 1)[0]).upper().replace("-", "_") + "_IMAGE" for i in expanded.split()}
for u in sorted(used - names):
    todo.append(f"{u} is used by the module but no image in the label provides it: leftover from the template?")

print("\n".join("TODO " + t for t in todo))
