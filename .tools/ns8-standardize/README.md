# ns8-standardize

Applies the mechanical, module-agnostic part of the current NethServer 8
module standards to a module repository, using
[NethServer/ns8-kickstart](https://github.com/NethServer/ns8-kickstart) as
the reference. It lives in a dot-directory on purpose: `createrepo.py` treats
every top-level directory as a module and skips the ones starting with a dot.

## What it does

- Copies the kickstart workflows (publish, QEMU test, API docs, registry
  clean-up, Renovate UI build), `renovate.json`, `.vscode` and the devcontainer.
- Updates the UI toolchain files (Node 26, Corepack, Yarn 4, `ns8-ui-lib` 2,
  Vue 2.7). Module-specific UI dependencies are kept; `yarn.lock` is copied
  when the dependencies match the template, otherwise regenerate it.
- Patches the Node/Corepack block of `build-images.sh`.
- Removes `package.json`, `test-module.sh` and `tests/pythonreq.txt`, adds the
  kickstart `tests/__init__.robot` and a `tests/<name>.robot` starting point.
- Fixes `ui/public/metadata.json` (authors, bug and code URLs, image source).
- Rewrites `%S/state` to `%E/state` in the systemd units and removes the
  smarthost hook files and lines, which were removed from the current module.
- It is idempotent: running it twice gives the same result.

It prints a `TODO` list for everything that needs a human look: floating or
partial image tags, image variables the units use that the label does not
provide (a sign of a leftover from another template), secrets passed through
`agent.set_env()`, placeholder metadata and README boilerplate.

## What it does not do

Image versions and breaking changes, systemd units, backup and restore,
configure/get-configuration actions, real tests and the README are specific
to each application. Follow the `nethserver-ns8-module` skill from
[NethServer/agents](https://github.com/NethServer/agents) for those.

## Usage

```bash
git clone https://github.com/geniusdynamics/ns8-mymodule
python3 .tools/ns8-standardize/ns8-standardize.py ns8-mymodule
cd ns8-mymodule/ui && corepack enable && yarn install && \
  NODE_OPTIONS=--openssl-legacy-provider yarn build
```

Options: `--kickstart DIR` uses an existing kickstart checkout (default: shallow
clone into a temporary directory), `--owner ORG` sets the GitHub organization
(default `geniusdynamics`), `--author-name` and `--author-email` fill the
metadata. The module name defaults to the directory name without `ns8-`.

Review `git diff` before committing, and never add `ui/node_modules` or
`ui/dist`.
