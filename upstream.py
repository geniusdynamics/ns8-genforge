"""Best-effort upstream image checks for the website; never changes repodata.json."""
import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

TIMEOUT = 8
MAX_PAGES = 5
HEADERS = {"User-Agent": "GenForge-upstream-checker", "Accept": "application/json"}


def get_json(url, headers=None):
    request = urllib.request.Request(url, headers={**HEADERS, **(headers or {})})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.load(response), response.headers


def image_ref(value):
    """Normalize Docker shorthand, retaining the exact reference shown by the module."""
    value = value.strip()
    if not value or "://" in value:
        return None
    name, _, digest = value.partition("@")
    tail = name.rsplit("/", 1)[-1]
    tag = tail.rsplit(":", 1)[1] if ":" in tail else (None if digest else "latest")
    if ":" in tail:
        name = name.rsplit(":", 1)[0]
    parts = name.split("/")
    registry = parts.pop(0) if len(parts) > 1 and ("." in parts[0] or ":" in parts[0] or parts[0] == "localhost") else "docker.io"
    if registry in {"index.docker.io", "registry-1.docker.io"}:
        registry = "docker.io"
    repo = "/".join(parts)
    if registry == "docker.io" and "/" not in repo:
        repo = "library/" + repo
    if not re.fullmatch(r"[a-z0-9][a-z0-9._/-]*", repo) or ".." in repo or "//" in repo:
        return None
    url = (f"https://hub.docker.com/r/{repo}/tags" if registry == "docker.io" else
           f"https://github.com/{repo.split('/')[0]}/pkgs/container/{urllib.parse.quote(repo.split('/', 1)[-1], safe='')}" if registry == "ghcr.io" else None)
    return {"reference": value, "registry": registry, "repository": repo, "tag": tag,
            "digest": digest or None, "url": url}


def stable_tag(tag, container_build=False):
    """Conservative numeric version + fixed variant; never order arbitrary strings."""
    match = re.fullmatch(r"(v|version-|release-|postgresql-v)?(\d+(?:\.\d+){1,3})(.*)", tag or "")
    if not match:
        return None
    prefix, number, suffix = match.groups()
    numeric_build = bool(container_build and re.fullmatch(r"-\d+(?:\.\d+)+", suffix))
    if suffix and not numeric_build and not re.fullmatch(r"-(?:alpine[\d.]*|bookworm|bullseye|apache|fpm|postgres|slim)", suffix):
        return None
    nums = tuple(map(int, number.split(".")))
    build = re.fullmatch(r"-(\d+(?:\.\d+)*)", suffix) if numeric_build else None
    if build:
        build_nums = tuple(map(int, build.group(1).split(".")))
        return nums + (0,) * (4 - len(nums)) + build_nums + (0,) * (4 - len(build_nums)), (prefix or "", "numeric-build")
    return nums + (0,) * (4 - len(nums)), (prefix or "", suffix)


def registry_tags(key):
    """Bounded, unauthenticated public-registry lookup, with explicit partial results."""
    registry, repo = key
    tags = []
    try:
        if registry == "docker.io":
            url = f"https://hub.docker.com/v2/repositories/{repo}/tags?page_size=100&ordering=last_updated"
            headers = {}
        elif registry == "ghcr.io":
            query = urllib.parse.urlencode({"service": "ghcr.io", "scope": f"repository:{repo}:pull"})
            token, _ = get_json("https://ghcr.io/token?" + query)
            headers = {"Authorization": "Bearer " + token["token"]}
            url = f"https://ghcr.io/v2/{repo}/tags/list?n=1000"
        else:
            return {"tags": [], "complete": False, "reason": "Registry is not supported yet."}
        for _ in range(MAX_PAGES):
            data, response_headers = get_json(url, headers)
            if registry == "docker.io":
                tags.extend(x["name"] for x in data.get("results", []))
                next_url = data.get("next")
            else:
                tags.extend(data.get("tags") or [])
                link = response_headers.get("Link", "")
                match = re.search(r'<([^>]+)>;\s*rel="?next"?', link)
                next_url = urllib.parse.urljoin(url, match.group(1)) if match else None
            if not next_url:
                return {"tags": tags, "complete": True, "reason": None}
            # Follow pagination only on the original registry host; never forward auth elsewhere.
            origin = urllib.parse.urlsplit(url)
            target = urllib.parse.urlsplit(next_url)
            if target.scheme != "https" or target.netloc != origin.netloc or target.path != origin.path:
                raise ValueError("Unexpected pagination URL")
            url = next_url
        return {"tags": tags, "complete": False, "reason": "Registry tag scan reached its page limit."}
    except Exception:
        # Do not put registry auth responses or tokens in the public catalog or logs.
        return {"tags": tags, "complete": False, "reason": "Registry could not be checked (unavailable, private or rate limited)."}


def compare_image(image, result):
    item = {**image, "latest": None, "status": "unknown", "complete": result["complete"], "reason": result.get("reason")}
    if image["registry"] == "ghcr.io" and image["repository"].startswith("geniusdynamics/"):
        item["reason"] = "Custom-built image: its tag is a module version, not an upstream application version."
        return item
    # NetBox documents a composite app-version/container-version tag scheme.
    container_build = image["repository"] == "netboxcommunity/netbox"
    current = stable_tag(image["tag"], container_build=container_build)
    if not current:
        item["reason"] = "Moving, prerelease or nonstandard tag; packaged version cannot be compared safely."
        return item
    candidates = [(stable_tag(tag, container_build=container_build), tag) for tag in result["tags"]]
    candidates = [(parsed[0], tag) for parsed, tag in candidates if parsed and parsed[1] == current[1]]
    if not candidates:
        item["reason"] = item["reason"] or "No stable tag with the same image variant was found."
        return item
    newest, tag = max(candidates)
    item["latest"] = tag
    if newest > current[0]:
        item["status"] = "update_available"
    elif result["complete"] and image["tag"] in result["tags"]:
        item["status"] = "current"
        item["reason"] = "No newer stable tag with the same image variant was found."
    else:
        item["reason"] = item["reason"] or "Packaged tag was not found in the registry."
    if image.get("digest"):
        item["reason"] = (item["reason"] or "Same-variant version comparison.") + " Tag versions only; pinned digest changes are not checked."
    return item


def main_image(images, app_id, config):
    primary = config.get("image")
    if primary:
        return next((i for i in images if i["registry"] + "/" + i["repository"] == primary), None)
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    matches = [i for i in images if norm(i["repository"].split("/")[-1]) == norm(app_id)]
    return matches[0] if len(matches) == 1 else None


def release_check(config, module_tag, github_get, token):
    repo = config.get("github")
    packaged = (config.get("versions") or {}).get(module_tag)
    entry = {"repository": repo, "packaged": packaged, "latest": None, "url": None, "status": "unknown"}
    if not repo or not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        return None
    release = github_get(f"/repos/{repo}/releases/latest", token)
    if not release or release.get("draft") or release.get("prerelease"):
        return entry
    entry.update(latest=release.get("tag_name"), url=release.get("html_url"), published_at=release.get("published_at"))
    current = stable_tag(packaged)
    latest = stable_tag(entry["latest"])
    # Release prefixes (v/release-) have no meaning for a mapped application version.
    if current and latest and current[1][1] == latest[1][1]:
        entry["status"] = "update_available" if latest[0] > current[0] else "current"
    return entry


def enrich(apps, repodata, config, github_get, token, version_for, offline=False):
    """Attach additive optional data, deduplicating registry queries across modules."""
    checked = datetime.now(timezone.utc).isoformat(timespec="seconds")
    raw = {m["id"]: m for m in repodata}
    parsed = {}
    for app in apps:
        module = raw[app["id"]]
        tag = version_for(module)
        labels = next((v.get("labels") or {} for v in module.get("versions") or [] if v.get("tag") == tag), {})
        parsed[app["id"]] = [i for ref in labels.get("org.nethserver.images", "").split() if (i := image_ref(ref))]
    keys = sorted({(i["registry"], i["repository"]) for images in parsed.values() for i in images})
    if offline:
        results = {key: {"tags": [], "complete": False, "reason": "Upstream checks were disabled for this build."} for key in keys}
    else:
        with ThreadPoolExecutor(8) as pool:
            results = dict(zip(keys, pool.map(registry_tags, keys)))

    def attach(app):
        cfg = dict(config.get(app["id"], {}))
        if not cfg.get("github"):
            match = re.fullmatch(r"https://github.com/([\w.-]+/[\w.-]+)/?", app.get("upstream_repo") or "")
            if match:
                cfg["github"] = match.group(1)
        images = [compare_image(i, results[i["registry"], i["repository"]]) for i in parsed[app["id"]]]
        primary = main_image(images, app["id"], cfg)
        module = raw[app["id"]]
        release = release_check(cfg, version_for(module), github_get, token) if not offline else None
        status = ((release if cfg.get("versions") else primary) or {}).get("status", "unknown")
        app["upstream_check"] = {"checked_at": checked, "module_version": version_for(module),
                                 "status": status, "primary_image": primary["reference"] if primary else None,
                                 "images": images, "release": release}
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(attach, apps))
