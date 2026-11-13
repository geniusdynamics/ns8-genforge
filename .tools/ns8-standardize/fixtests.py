#!/usr/bin/env python3
"""Make a module's Robot suite configure a valid host and check the app through Traefik.

usage: fixtests.py <module-repo-dir>...   (idempotent)

- ${HOST} is <module>.example.org (name derived from the absolute repo path)
- the configure payload is built from imageroot/actions/configure-module/validate-input.json:
  host, http2https and lets_encrypt plus every other required field, using the first
  schema example where there is one
- the 'works as expected' check goes through Traefik with retries
- json.loads($output)['output'] is fixed (api-cli prints the action output directly)
"""
import glob
import json
import os
import re
import sys


def payload_for(repo):
    p = os.path.join(repo, "imageroot/actions/configure-module/validate-input.json")
    try:
        schema = json.load(open(p))
    except (OSError, ValueError):
        schema = {}
    props = schema.get("properties", {})
    required = schema.get("required", ["host", "http2https", "lets_encrypt"])
    example = (schema.get("examples") or [{}])[0]
    out = {"host": "${HOST}", "http2https": True, "lets_encrypt": False}
    for key in required:
        if key in out:
            continue
        if key in example and example[key] not in (None, ""):
            out[key] = example[key]
            continue
        t = props.get(key, {}).get("type", "string")
        if t == "boolean":
            out[key] = False
        elif t in ("integer", "number"):
            out[key] = props.get(key, {}).get("minimum", 1)
        elif t == "array":
            out[key] = []
        elif re.search(r"pass|secret|token|key", key, re.I):
            out[key] = "Nethesis,1234"
        elif re.search(r"mail", key, re.I):
            out[key] = "admin@example.org"
        else:
            out[key] = "test"
    s = json.dumps(out, separators=(",", ":"))
    return s.replace("'", "")


def fix(repo):
    repo = os.path.abspath(repo)
    name = os.path.basename(repo)[len("ns8-"):]
    files = [f for f in glob.glob(os.path.join(repo, "tests", "*.robot")) if not f.endswith("__init__.robot")]
    if not files:
        return "no suite"
    data = payload_for(repo)
    changed = []
    for path in files:
        s = open(path, encoding="utf-8").read()
        o = s
        s = s.replace("\r\n", "\n")
        s = s.replace("['output']", "")
        # configure payload: only in a template suite with a single configure call;
        # a suite with several calls tests different settings on purpose
        if len(re.findall(r"configure-module --data ", s)) == 1:
          s = re.sub(r"(configure-module --data )'[^\n]*?'(?=\n)", lambda m: f"{m.group(1)}'{data}'", s)
        # host variable
        host_line = f"${{HOST}}    {name}.example.org"
        if re.search(r"^\$\{HOST\}[ \t]", s, re.M):
            s = re.sub(r"^\$\{HOST\}[ \t].*$", lambda m: host_line, s, flags=re.M)
        elif "*** Variables ***" in s:
            s = s.replace("*** Variables ***\n", "*** Variables ***\n" + host_line + "\n", 1)
        elif "*** Keywords ***" in s:
            s = s.replace("*** Keywords ***", "*** Variables ***\n" + host_line + "\n\n*** Keywords ***", 1)
        else:
            s = s.replace("*** Test Cases ***", "*** Variables ***\n" + host_line + "\n\n*** Test Cases ***", 1)
        # works-as-expected check through Traefik (template suites only)
        if len(re.findall(r"configure-module --data ", o)) <= 1:
          s = re.sub(
            r"(Check if [^\n]+ works as expected\n)(?:    [^\n]*\n)+?(?=\n|\Z)",
            lambda m: m.group(1) +
            "    ${rc} =    Execute Command    bash -c 'for i in $(seq 1 60); do curl -k -s -o /dev/null -f --resolve ${HOST}:443:127.0.0.1 https://${HOST}/ && exit 0; sleep 5; done; exit 1'\n"
            "    ...    return_rc=True  return_stdout=False\n"
            "    Should Be Equal As Integers    ${rc}  0\n",
            s)
        if s != o:
            open(path, "w", encoding="utf-8").write(s)
            changed.append(os.path.basename(path))
    return ("changed " + ",".join(changed) + " payload=" + data) if changed else "unchanged"


if __name__ == "__main__":
    for r in sys.argv[1:]:
        print(os.path.basename(os.path.abspath(r)), fix(r))
