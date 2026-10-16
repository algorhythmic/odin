# Monorepo mechanics for Odin: one repository, one release train

Reference for a single operator, current as of 2026-10-16. It covers
how to fold heimdall, skald and braid (Go), the Python service and MCP
projects, and the new Odin service into the existing `algorhythmic/odin`
repository with history, and how to build, version, package and release
three deployables from it.

**Basis.** Tool facts were checked against current documentation (URLs
in §13). Some steps were also rehearsed on this machine (uv 0.13.0,
git 2.55.0, pacman 7.1.0, git-filter-repo a40bce548d2c via `uvx`), using
fresh clones in a scratch directory. The source repositories were not
changed. Results from that rehearsal are marked **[rehearsed]**. Go is
not installed here, so the Go steps come from the documentation and were
not executed.

---

## 0. Recommendations at a glance

| Question | Recommendation |
|---|---|
| Trunk repository | The existing `algorhythmic/odin`. Its commit hashes and its frozen `docs/` stay unchanged. The imported repositories get rewritten hashes. |
| Import method | In a fresh clone, run `git filter-repo --to-subdirectory-filter <name> --tag-rename ':<name>/'`, then `git merge --allow-unrelated-histories`. Push the merge commits directly; never squash them. Do not use `git subtree add`. |
| Go | One module at the repository root (`github.com/algorhythmic/odin`) with `go 1.25.0` and `toolchain go1.27.1`. No `go.work`. Each imported project keeps its own `internal/` tree. Every former binary still builds with `go build ./<name>/cmd/<name>`. |
| Python | One uv workspace with a virtual root (`package = false`) and one `uv.lock`. The service, the MCP server and the shared library are members. Docker images install a subset with `uv sync --package … --frozen --no-editable`. |
| TypeScript (only if Odin is written in TS) | A pnpm workspace in the same repository. Use `pnpm --filter … deploy` for images. |
| Orchestration | A root `justfile` with one recipe group per deployable. No Bazel, Nx or Pants at this scale. |
| Versioning | Semver per deployable, with tags `<deployable>/vX.Y.Z`, and a repo-wide `release/manifest.json` that serves as the train. No root `vX.Y.Z` tags. |
| CI | `ci.yml` runs a `changes` job (`dorny/paths-filter@v4`), then jobs for Go, Python, the plugin and docs, then a single `ci-ok` aggregator, which is the only required check. `release.yml` runs on `*/v*` tag pushes and dispatches by deployable. |
| Arch / Omarchy | One PKGBUILD per binary in `deploy/arch/<pkg>/`, installed with `makepkg -si`. Units go in `/usr/lib/systemd/user` and are enabled with `systemctl --user`. Set up a local pacman repository only once a second Arch machine needs the packages. |
| License | The root `LICENSE` (Apache-2.0, currently untracked: `?? LICENSE`) and a short `NOTICE`. Put a copy of `LICENSE` in every unit that is distributed from a subdirectory: the plugin directory and each Python package. |

---

## 1. Prerequisites in Odin's own decision record (resolve first)

The mechanics below are straightforward. The governance is the part
that blocks:

1. **D14 is locked, shared and verbatim:** "`saga` and `odin`; the
   standalone repos stay where they are" (`docs/DECISIONS.md`, D14.1 in
   `docs/provenance/DECISION-MAP.md`). Importing heimdall, skald and
   braid reverses that. Under AGENTS.md §2, the change needs an
   `ODIN-ADR-nnn` that names D14.1 as superseded, plus an update to the
   map. D14 is shared with Saga and the handoff is not recorded, so an
   Odin ADR cannot amend Saga's copy. Raise an `X-n` issue to reconcile
   it on the Saga side.
2. **The D13 naming rule** (AGENTS.md §7): "Never reuse a name from the
   operator's standalone repositories (heimdall, braid, skald, muninn,
   wayland-computer-use)". In addition, "Heimdall" is the legacy name of
   Saga's launcher. Importing the projects under their own names keeps
   the same projects rather than reusing their names, but the ADR should
   say so explicitly, and prose still has to keep heimdall (the
   continuity daemon) apart from Saga's launcher.
3. **X-5:** Odin has no deliverable prefix yet. The names `odin-homelab`
   and `odin-workstation` in this document are placeholders.
4. **The old repositories must survive.** Odin's docs contain about 846
   commit-pinned links into the standalone repositories (braid 182,
   heimdall 124, muninn 202, skald 184, wayland-computer-use 154; counted
   with `grep -rhoE 'github\.com/algorhythmic/<repo>/(blob|tree|commit)/<sha>'`).
   Most of them sit in frozen research files that cannot be edited.
   Those SHAs will not exist in the monorepo, because the rewrite changes
   them. So the old repositories must be **archived, never deleted,
   renamed or replaced**.

---

## 2. Importing the repositories with history

### 2.1 Choosing a method

| | `git subtree add --prefix=X repo main` | `git filter-repo --to-subdirectory-filter X` + `merge --allow-unrelated-histories` |
|---|---|---|
| Old commits | Kept unchanged, with the same hashes | Rewritten, as if the files had always lived under `X/` |
| `git log -- X/file` across the import | Stops at the subtree merge, because the old commits have the file at `file`, not `X/file`. Honnef rejects subtree merges because they "break file history". | Works without `--follow` |
| `git blame` on old lines | Needs `--follow` and heuristics | Works |
| Tags | Not brought along; collide with Odin's tags if fetched | Renamed during the rewrite (`--tag-rename ':X/'`) |
| Issue references like `#12` in messages | Point at the wrong repository | Can be rewritten to `owner/repo#12` with `--message-callback` |
| Hash references in messages | Unchanged | filter-repo rewrites "(possibly abbreviated) hashes in commit messages to refer to the new post-rewrite commit hashes" |
| Re-running later | n/a | Deterministic. Two rewrites of skald produced identical HEAD `2e94db7…` **[rehearsed]**, so commits added later can be merged incrementally. |

Choose filter-repo. Subtree only makes sense if you need the old hashes
to exist inside the monorepo. You don't, because the archived
repositories keep them.

### 2.2 Procedure

Install it with `sudo pacman -S git-filter-repo`, or run it without
installing via `uvx git-filter-repo` (which is how it was rehearsed).

```bash
# 0. Freeze the source repo: commit or stash everything. Only committed
#    history is imported. (heimdall's PKGBUILD deliberately packages
#    uncommitted work, so check `git status` there.)
#    Do the import on a branch of the trunk:
cd ~/Projects/odin && git switch -c import/2026-10

# 1. Rewrite a throwaway fresh clone. filter-repo aborts unless the clone is fresh.
name=skald
work=$(mktemp -d)
git clone --no-local "https://github.com/algorhythmic/$name.git" "$work/$name"
cd "$work/$name"
git filter-repo --analyze            # report lands in .git/filter-repo/analysis/ (largest blobs, renames)
export IMPORT_NAME="$name"           # single-quoted callback below: no shell/history expansion surprises
git filter-repo \
  --to-subdirectory-filter "$name" \
  --tag-rename ":$name/" \
  --message-callback '
import os, re
repo = os.environ["IMPORT_NAME"].encode()
return re.sub(rb"(?<![\w/])#(\d+)", b"algorhythmic/" + repo + rb"#\1", message)
'
# [rehearsed] "fix: thing (#12), see org/other#3" → "fix: thing (algorhythmic/skald#12), see org/other#3";
#             tag v1.0.0 → skald/v1.0.0; file a → skald/a
mkdir -p ~/Projects/odin/scripts/imports
cp .git/filter-repo/commit-map ~/Projects/odin/scripts/imports/$name.commit-map   # old→new SHA table

# 2. Merge it into the trunk.
cd ~/Projects/odin
git remote add "import-$name" "$work/$name"
git fetch --tags "import-$name"
git merge --allow-unrelated-histories --no-ff \
  -m "chore(import): merge $name history from github.com/algorhythmic/$name" "import-$name/main"
git remote remove "import-$name"

# 3. Verify.
git log --oneline -- "$name" | wc -l             # equals the old repo's commit count
git tag -l "$name/*"                             # skald/v0.1.0, skald/v0.1.1
git describe --tags --long --match "$name/v[0-9]*"
python3 scripts/validate_docs.py                 # expect failures; see §2.5
```

Repeat for heimdall and braid. Each import is one merge commit. Then
`git switch main && git merge --ff-only import/2026-10 && git push origin main --tags`.

Do not open a pull request and squash-merge it, because that discards
the history. The Netlify guide: "If you squashed the PR before
committing, all history would be gone."

Do the follow-up restructuring (removing nested `go.mod` files,
rewriting imports, moving PKGBUILDs) in **separate, later commits**, so
that every imported path keeps an unbroken `git log`.

**[rehearsed]** Importing skald and braid into a clone of the trunk
gave 23 commits, the tags `skald/v0.1.0`, `skald/v0.1.1` and
`braid/v0.1.0`, and `git describe --match 'skald/v*'` →
`skald/v0.1.1-12-g8b107cd`. With heimdall added as well, the pack was
3.3 MiB.

### 2.3 How tags and PKGBUILD version derivation survive

- `--tag-rename ':skald/'` turns `v0.1.1` into `skald/v0.1.1`. That is
  the same scheme as the new per-deployable tags (§6.5), so skald's
  version line simply continues with `skald/v0.1.2`. Annotated tags stay
  annotated (`git cat-file -t skald/v0.1.1` → `tag`).
- For a `pkgver()` based on `git describe`, add `--match` and strip the
  prefix:
  ```bash
  git describe --long --tags --abbrev=7 --match 'skald/v[0-9]*' \
    | sed 's|^skald/v||;s/\([^-]*-g\)/r\1/;s/-/./g'
  # → 0.1.1.r2.ge457611   [rehearsed]
  ```
  In a monorepo, `rN` counts every commit since the tag, including ones
  that never touched skald. For a `-git` package that is acceptable.
- heimdall has no tags. Its PKGBUILD currently emits
  `r<rev-list --count>.g<hash>` (`r25.gd3e4694`). After the import the
  count covers the whole monorepo, so it grows, and pacman still treats
  it as an upgrade. Switching to a tag-based `0.1.0.r3.g…` later is also
  an upgrade: `vercmp 0.1.0.r3.gabc1234 r25.gd3e4694` returns `1`
  **[rehearsed]**. No `epoch` is needed.
- Go pays no attention to these tags. A tag such as `skald/v0.1.1` would
  only matter to Go if `skald/` contained a `go.mod`, which it won't
  under §3.

### 2.4 Keep the old repositories as read-only archives

This is the operator's action on each old repository. It is not done
from Odin's tooling, because AGENTS.md says never to edit peer
repositories from Odin.

```bash
git clone git@github.com:algorhythmic/heimdall.git /tmp/heimdall-archive && cd /tmp/heimdall-archive
cat > README.md <<'EOF'
# heimdall (archived)

Development continues in [algorhythmic/odin](https://github.com/algorhythmic/odin/tree/main/heimdall).
The full history was imported there on 2026-10-NN with rewritten hashes;
tags were renamed `heimdall/vX.Y.Z`. This repository stays read-only so
existing commit links keep working.
EOF
git commit -am "docs: point to the Odin monorepo" && git push
gh repo edit algorhythmic/heimdall --description "Archived: now algorhythmic/odin/heimdall"
gh repo archive algorhythmic/heimdall --yes
```

Archiving makes the repository "read-only for all users". Issues and
PRs become read-only, and you can unarchive it later. GitHub recommends
updating the README and description first, as above. Keep the
`scripts/imports/<name>.commit-map` files so that an old SHA quoted in
notes can be translated to the new one.

### 2.5 Pitfalls

1. **The doc validator scans every `*.md` in the repository.**
   `scripts/validate_docs.py` link-checks `ROOT.rglob("*.md")`, skipping
   only `.git`, the frozen snapshot and `docs/research/`. After importing
   skald and heimdall the validator reported **33 failures
   [rehearsed]**: sibling links such as `../dotprivate/README.md` and
   `../wayland-computer-use/…`, plus absolute `/home/david/.codex/…`
   paths. Placing heimdall at top-level `heimdall/` fixed 15 of skald's
   `../heimdall/…` links, which is one reason for the layout in §10. The
   same `rglob` will also descend into `.venv/`, `node_modules/` and
   makepkg's `src/` and `pkg/` once those exist. Fix it before
   importing:
   - Scope link checking to Odin's own documents:
     ```python
     LINK_SCOPE = ["README.md", "AGENTS.md", "CLAUDE.md", "docs"]   # imported trees get their own pass later
     candidates = [p for s in LINK_SCOPE
                   for p in ((ROOT / s).rglob("*.md") if (ROOT / s).is_dir() else [ROOT / s])]
     ```
   - Alternatively, enumerate tracked files only (this needs git):
     `subprocess.run(["git", "ls-files", "-z", "--", "*.md"], …)`.
   - Then fix the imported docs' links in follow-up commits. Rewrite
     links to repositories that stay separate as GitHub URLs. Those docs
     are live, not frozen.
2. **Nested CI stops running without any warning.** After the import,
   `heimdall/.github/workflows/test.yml` sits inside a subdirectory
   **[rehearsed]**, and GitHub only reads `.github/workflows/` at the
   repository root. Port those jobs into the root workflow (§6).
   Imported `.gitignore` and `.gitattributes` files keep working, scoped
   to their own subdirectory.
3. **Large binaries and screenshots.** GitHub warns at 50 MiB, blocks
   files over 100 MiB, recommends keeping repositories under 1 GB and
   "strongly recommends" under 5 GB. Check `--analyze` before merging.
   To drop blobs, run
   `git filter-repo --strip-blobs-bigger-than 10M` in the throwaway clone
   before merging. For this case the rehearsal found no blob over
   500 KB in heimdall, skald or braid, and one image file in each of
   heimdall and skald, so nothing needs stripping.
4. **LFS.** If a source repository uses LFS
   (`grep filter=lfs .gitattributes`), run `git lfs fetch --all` in the
   clone before rewriting, then `git lfs push --all origin` to the
   monorepo after merging. Two constraints to keep in mind:
   - GitHub Free includes 10 GiB of LFS storage and 10 GiB of bandwidth
     per month.
   - Claude Code's marketplace and plugin clones "never download LFS
     content", so LFS files arrive as pointer files. **Never put files
     the plugin needs under LFS.**
5. **Rewritten hashes break SHA links.** Links in other repositories
   and in Odin's frozen evidence keep working only while the archived
   repositories exist (§1.4). Links to `github.com/…/odin/commit/<old-sha>`
   will never resolve. Use the commit map.
6. **Interleaved history.** `git log` interleaves the imported histories
   by date. Use `git log --first-parent main` for the trunk's own story,
   and `git bisect start --first-parent` so bisect stays off the side
   histories. Those side commits never built as part of the monorepo.
7. **Nested instruction files.** Agent instruction files in imported
   trees, such as a `CLAUDE.md` or `AGENTS.md`, are loaded by Claude Code
   when you work in that subdirectory. None exist in
   heimdall, skald or braid today. Keep it that way, or fold their
   guidance into Odin's AGENTS.md.

---

## 3. Go: single module versus several

### 3.1 Options

| | One root module | One module per former repository + `go.work` |
|---|---|---|
| go.mod files | 1 | 3 or more |
| Tags Go cares about | Root `vX.Y.Z` only, and you won't need any | `heimdall/vX.Y.Z` etc. for each module. Go ignores any tag that lacks the subdirectory prefix. |
| Cross-project change (for example the substrate plus a caller) | One commit, one `go test ./...` | Tag the library and bump `require` in each caller, or rely on an uncommitted `go.work` |
| `go install …@version` | One module, one version line | Refuses modules whose go.mod uses `replace`, which is how local multi-module setups usually get wired |
| Dependency versions | One MVS graph: one version of `modernc.org/sqlite` for everything | Each module drifts. This is Segment's failure mode (§11). |
| `internal/` | Visibility follows the path prefix (§3.3) | The same rule. Module boundaries do not hide `internal/`. |
| Tooling burden | None | OpenTelemetry-Go needs a dedicated tool (`multimod` plus `versions.yaml`) to tag module sets, and Go tags "should not be deleted or changed" once pushed |

The Go documentation calls a single module at the root "the simplest
approach, making your module likely easier to manage over time". It
also says "you publish code in a module when the code should be
versioned independently from code in other modules". Nothing here is
consumed independently by outside importers. heimdall even requires
skald (`github.com/algorhythmic/skald v0.1.1 // indirect`), which a
single module turns into an ordinary internal import.

**Recommendation: one root module.** Do not commit a `go.work`. The Go
workspace design doc was revised to "clearly discourage go.work files in
repos", because a checked-in one overrides a developer's own workspace
and can make CI test the wrong versions. With one module there is
nothing for it to do anyway.

### 3.2 Converting after the import (separate commits)

```bash
cd ~/Projects/odin
git rm heimdall/go.mod heimdall/go.sum skald/go.mod skald/go.sum braid/go.mod braid/go.sum
go mod init github.com/algorhythmic/odin
go mod edit -go=1.25.0 -toolchain=go1.27.1         # braid declared go 1.24.0; the module takes the max

# heimdall's module path was the bare name `heimdall` (imports like "heimdall/internal/actions").
grep -rl --include='*.go' '"heimdall/' heimdall | xargs sed -i 's#"heimdall/#"github.com/algorhythmic/odin/heimdall/#g'
for m in skald braid; do
  grep -rlI "github.com/algorhythmic/$m" . --exclude-dir=.git --exclude-dir=docs \
    | xargs -r sed -i "s#github.com/algorhythmic/$m#github.com/algorhythmic/odin/$m#g"
done   # catches Makefile/ldflags `-X` paths and embeds too; review the diff

cat >> go.mod <<'EOF'

ignore (
	node_modules
	./integrations
	./deploy
	./docs
)
EOF
go mod tidy
gofmt -l . ; go vet ./... ; go test ./...
go build ./heimdall/cmd/heimdall ./skald/cmd/skald ./workstation/cmd/odin-workstation
```

The `ignore` directive is new in Go 1.25. A bare name such as
`node_modules` matches at any depth, and a `./` path is anchored to the
module root. heimdall carries a `node_modules/` for its extension tests,
which `./...` would otherwise walk. Directories starting with `.` or
`_` and `testdata/` are ignored already.

### 3.3 `internal/` across what used to be separate modules

Visibility depends on the import path: "the importing package must have
the same path prefix as the internal package, up to the last
`/internal/` element" (golang/go#38579). Under one root module:

- `github.com/algorhythmic/odin/heimdall/internal/...` stays private to
  `heimdall/...`. Each imported project keeps its encapsulation without
  edits.
- Code shared on purpose (the substrate) goes in
  `github.com/algorhythmic/odin/substrate/...`, which every package can
  import. Use `substrate/internal/...` for code that only the substrate
  itself may see.
- Under a multi-module layout the same rule applies, so sibling modules
  under one prefix *can* import each other's `internal/` packages (Go's
  own `mod_internal` test script confirms it). Splitting into modules
  therefore buys no extra privacy.

### 3.4 `go install`, versions and tags

- `go install github.com/algorhythmic/odin/skald/cmd/skald@latest`
  works. With no root semver tags, `@latest` resolves to a pseudo-version
  of the default branch. For a private repository set
  `GOPRIVATE=github.com/algorhythmic/*`.
- `go install pkg@version` ignores the local `go.mod` and refuses
  modules whose go.mod has `replace` or `exclude` directives. Keep the
  root go.mod free of `replace`.
- **Do not put `vX.Y.Z` tags on the root.** Every root tag becomes a
  public Go module version, and from `v2.0.0` on the module path must
  end in `/v2`, which would mean rewriting every import in the
  repository. Deployable tags such as `workstation/v1.0.0` are ignored
  by the root module.
- If one piece ever needs to be imported independently (say braid by a
  third party), split *that one* into a nested module (`braid/go.mod`)
  with tags `braid/vX.Y.Z`. Module zips exclude nested modules, and
  `pkg.go.dev` only finds a license inside the nested module's tree,
  with a special case that copies a root file named exactly `LICENSE`.

### 3.5 Reproducible builds and version stamping

```bash
CGO_ENABLED=0 go build -trimpath \
  -ldflags "-s -w -X main.version=${VERSION}" \
  -o dist/odin-workstation ./workstation/cmd/odin-workstation
go version -m -json dist/odin-workstation      # Go 1.25+: embedded BuildInfo as JSON
```

- `-trimpath` "removes all file system paths from the resulting
  executable". Builds that use the same toolchain (pinned by
  `toolchain go1.27.1`), the same flags, `CGO_ENABLED` and GOOS/GOARCH
  should produce identical bytes. Go embeds no timestamps.
- Since Go 1.24, `go build` stamps the main module version from VCS tags
  and appends `+dirty` for uncommitted changes. It reads only *root*
  `vX.Y.Z` tags, so under this scheme it stamps a pseudo-version. Stamp
  the deployable version yourself with `-ldflags -X main.version`, which
  needs `var version = "dev"` in package `main`.
- `-buildvcs=auto` (the default) stamps `vcs.revision` only when the
  main package, its module and the current directory are in the same
  repository. Inside Docker builds `.git` is usually excluded, so
  stamping is skipped quietly. Pass the version through ldflags.

---

## 4. Python: one uv workspace

### 4.1 Layout and files

```toml
# /pyproject.toml — virtual workspace root (not a package)
[project]
name = "odin-workspace"
version = "0"
requires-python = ">=3.13"

[tool.uv]
package = false

[tool.uv.workspace]
members = [
  "substrate/python",        # odin-substrate: schema models/validators shared by service and MCP
  "homelab/service",         # odin-service: the homelab processes
  "integrations/mcp/odin-mcp",
  # "homelab/<legacy-service>",   # see 4.5
]

[dependency-groups]
dev = ["pytest>=8", "ruff"]
```

```toml
# /homelab/service/pyproject.toml
[project]
name = "odin-service"
version = "0.1.0"
requires-python = ">=3.13"
license = "Apache-2.0"
license-files = ["LICENSE"]          # globs may not contain ".." → keep a LICENSE copy here
dependencies = ["odin-substrate", "claude-agent-sdk"]

[project.scripts]                     # several processes, one package, one image
odin-gateway   = "odin_service.gateway:main"
odin-scheduler = "odin_service.scheduler:main"
odin-worker    = "odin_service.worker:main"

[tool.uv.sources]
odin-substrate = { workspace = true }

[build-system]
requires = ["uv_build>=0.13.0,<0.14.0"]
build-backend = "uv_build"
```

- "The workspace shares a single lockfile". `requires-python` is the
  **intersection** of all members' values. Workspaces "are *not* suited
  for cases in which members have conflicting requirements".
- Create members with `uv init --package --vcs none <dir>`. When the
  parent directory isn't already a git repository, `uv init` creates a
  nested `.git` in the new member. That broke the rehearsal until it was
  removed **[rehearsed]**.
- Python version: Python 3.15.0 shipped on 2026-10-09 (reported by
  secondary sources), so wheels across the ecosystem are still catching
  up. Use 3.14 images, keep `requires-python` at `>=3.13`, and add 3.15
  to the CI matrix. The Claude Agent SDK is `claude-agent-sdk` on PyPI
  (Python ≥3.10) and `@anthropic-ai/claude-agent-sdk` on npm.

### 4.2 Commands [rehearsed with uv 0.13.0 unless noted]

```bash
uv lock                                      # one uv.lock for the whole workspace
uv sync --locked --all-packages              # dev/CI: everything, fail if the lock is stale
uv run --package odin-service odin-gateway   # run one member's entry point
uv run --all-packages pytest                 # CI test run (not rehearsed)
uv build --package odin-service -o dist      # sdist + wheel for one member
uv export --package odin-service --no-dev --frozen --no-hashes   # requirements for one member
uv version --package odin-service 0.4.0      # bump a member's version (also relocks)
```

### 4.3 The MCP server and the service from one workspace

- In development, run it with
  `uv run --package odin-mcp odin-mcp`.
- From the Claude Code plugin there are two options. Component paths
  must stay inside the plugin root (no `..`), so the plugin cannot point
  at `../../mcp`.
  1. **Pin to the harness tag (recommended).** The plugin's `.mcp.json`
     runs uvx from a git tag:
     ```json
     { "mcpServers": { "odin": {
         "command": "uvx",
         "args": ["--from",
                  "git+ssh://git@github.com/algorhythmic/odin@harness/v0.3.0#subdirectory=integrations/mcp/odin-mcp",
                  "odin-mcp"] } } }
     ```
     This was rehearsed with a `git+file://` URL and the slash tag
     `homelab/v0.1.0`. The member's `{ workspace = true }` sibling was
     resolved from the checkout ("Installed 2 packages")
     **[rehearsed]**. The target machine needs uv and git read access.
  2. **Self-contained.** Put the MCP package inside the plugin directory
     and run
     `uv run --directory ${CLAUDE_PLUGIN_ROOT}/mcp odin-mcp`, with
     `"env": {"UV_PROJECT_ENVIRONMENT": "${CLAUDE_PLUGIN_DATA}/venv"}`.
     `${CLAUDE_PLUGIN_ROOT}` moves on every update, while
     `${CLAUDE_PLUGIN_DATA}` persists across updates.

### 4.4 Docker image from a subset of the workspace

```dockerfile
# deploy/homelab/Dockerfile — build context is the repo root
# syntax=docker/dockerfile:1
FROM python:3.14-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0 UV_NO_DEV=1
# Same path in both stages: entry-point shebangs inside the venv are absolute.
WORKDIR /app
# Layer 1: third-party deps only. Needs just the root pyproject + uv.lock [rehearsed].
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --package odin-service --no-install-workspace --no-editable
# Layer 2: only the members this image needs.
COPY pyproject.toml uv.lock ./
COPY substrate/python substrate/python
COPY homelab/service homelab/service
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --package odin-service --no-editable

FROM python:3.14-slim
COPY --from=build /app/.venv /app/.venv
COPY LICENSE NOTICE /app/
ENV PATH=/app/.venv/bin:$PATH
USER 65534:65534
CMD ["odin-gateway"]
```

```gitignore
# deploy/homelab/Dockerfile.dockerignore — overrides the root .dockerignore for this Dockerfile
**
!pyproject.toml
!uv.lock
!LICENSE
!NOTICE
!substrate/python/**
!homelab/service/**
**/.venv
**/__pycache__
```

- **Use `--frozen`, not `--locked`, in a subset build.** With one member
  missing from the context, `uv sync --locked` fails with "To update the
  lockfile, run `uv lock`" (rc=1), while `--frozen` installs correctly
  **[rehearsed]**. Enforce `--locked` in CI on the full tree instead.
- For several processes, use one image and several services in
  `deploy/homelab/compose.yaml`, each with its own `command:`
  (`odin-gateway`, `odin-scheduler`, …).
- A Dockerfile-specific ignore file "takes precedence over the
  `.dockerignore`", which keeps the repo-root build context small.

### 4.5 The dormant service repository

Import it with history like the others, under `homelab/<name>/`.

- **Compatible dependencies:** make it a workspace member.
- **Conflicting dependencies (old pins, another Python):** list it under
  `[tool.uv.workspace] exclude = [...]` and give it its own
  `pyproject.toml` and `uv.lock`. uv documents path dependencies for
  this case. `uv run --package` then doesn't reach it, so its recipes
  `cd` into the directory.
- Its shell scripts and Dockerfiles stay with it, but move them to
  `deploy/` if it is revived.

---

## 5. If the Odin service is TypeScript

### 5.1 pnpm in the same repository

```yaml
# /pnpm-workspace.yaml
packages:
  - "homelab/service"            # @odin/service, uses @anthropic-ai/claude-agent-sdk
  - "substrate/ts"               # @odin/substrate: types generated from substrate/schemas
  - "integrations/claude-code/odin/hooks"   # only if hooks are TS
allowBuilds:                     # pnpm 11 replaced onlyBuiltDependencies with allowBuilds
  esbuild: true
```

```json
// /package.json
{ "private": true, "packageManager": "pnpm@11.x.y",
  "engines": { "node": ">=24" } }
```

- `workspace:*` dependencies "refuse to resolve to anything other than a
  local workspace package". Use `pnpm -r test` or
  `pnpm --filter @odin/service build`.
- Versions as of October 2026:
  - pnpm 11 is npm's `latest`.
  - pnpm 12, a Rust rewrite released 2026-08-26, is still on the
    `next-12` tag and makes unknown `pnpm-workspace.yaml` keys an error.
  - pnpm 11 moved pnpm-specific settings out of `.npmrc` into
    `pnpm-workspace.yaml`.
  - Node 24 is the Active LTS, and Node 26 is scheduled to enter LTS on
    2026-10-28.
  - Corepack is not bundled from Node 25 on. In CI, use
    `pnpm/action-setup`, which reads the `packageManager` field.
- Build the image with
  `pnpm --filter @odin/service --prod deploy /out`, which copies the
  package and installs "an isolated node_modules" with its workspace
  dependencies. Then copy `/out` into a `node:24-slim` stage.
- Python remains for the MCP server and the dormant service if they are
  Python, so the uv workspace shrinks but stays. Go is unchanged.

### 5.2 Is a polyglot monorepo without a meta-build tool sane here?

Yes. Each language already has a native graph tool: `go build ./...`,
uv workspaces and pnpm filters. What's missing is a place to name the
cross-language tasks, and a `justfile` (`pacman -S just`) or a Makefile
covers that. Recipes are grouped by deployable, and CI calls the same
recipes:

```just
set shell := ["bash", "-euo", "pipefail", "-c"]
default:
    @just --list

# ── everything ───────────────────────────────────────────────
check: docs go-check py-check plugin-check
docs:
    python3 scripts/validate_docs.py

# ── Go: one module ───────────────────────────────────────────
go-check:
    test -z "$(gofmt -l .)"
    go mod tidy -diff
    go vet ./...
    go test ./...

# ── deployable: workstation daemon ───────────────────────────
build-workstation version="dev":
    CGO_ENABLED=0 go build -trimpath -ldflags "-s -w -X main.version={{version}}" \
      -o dist/odin-workstation ./workstation/cmd/odin-workstation
pkg-workstation:
    cd deploy/arch/odin-workstation && makepkg -srci --cleanbuild
pkg-heimdall:
    cd deploy/arch/heimdall && makepkg -srci --cleanbuild

# ── deployable: homelab service ──────────────────────────────
py-check:
    uv sync --locked --all-packages
    uv run --all-packages pytest
image-homelab tag="dev":
    docker build -f deploy/homelab/Dockerfile -t odin-homelab:{{tag}} .
deploy-homelab host="homelab":
    ssh {{host}} 'cd /srv/odin && docker compose pull && docker compose up -d'

# ── deployable: harness integration ──────────────────────────
plugin-check:
    claude plugin validate --strict integrations/claude-code
plugin-dev:
    claude --plugin-dir integrations/claude-code/odin

# ── release train ────────────────────────────────────────────
release deployable version:
    just check
    python3 scripts/release.py {{deployable}} {{version}} --push
```

### 5.3 When a meta-tool becomes worth it

Consider Nx, Pants or Bazel only once one of these is true:

- CI takes more than about 15 minutes per push even with path filters
  and caches.
- Generated code crosses languages along a dependency graph you keep
  getting wrong by hand.
- Several people need remote caching or hermetic builds.
- You need affected-target analysis finer than directory filters.

The cost is real. An ICSE 2024 study of 542 projects that adopted
Bazel found that 61 (11.2%) abandoned it, after a median of 638 days,
mostly for Go build, CMake or plain Make. None of the conditions above
applies to one operator with three deployables.

---

## 6. CI on GitHub Actions

### 6.1 Shape

- **`ci.yml`** runs on pull requests and on pushes to main. A `changes`
  job runs `dorny/paths-filter@v4`. Conditional jobs follow: `go`,
  `python`, optionally `ts`, `plugin` and `image-build`. `docs` always
  runs. A final `ci-ok` job aggregates the results and is the **only**
  required check.
- **`release.yml`** runs on tag pushes matching `*/v*`. A `meta` job
  reads `release/manifest.json` and dispatches to `go-binary`,
  `homelab-image` or `plugin`.

The reason for the aggregator: if a *workflow* is skipped by a `paths:`
filter, its required checks "stay in a 'Pending' state and block
merging". A *job* skipped by `if:` "will report its status as
'Success'". So filter at job level, and require one job that always
runs.

### 6.2 `ci.yml`

```yaml
name: ci
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  changes:
    runs-on: ubuntu-latest
    permissions: { contents: read, pull-requests: read }   # paths-filter needs pull-requests: read
    outputs:
      go: ${{ steps.f.outputs.go }}
      python: ${{ steps.f.outputs.python }}
      plugin: ${{ steps.f.outputs.plugin }}
      image: ${{ steps.f.outputs.image }}
    steps:
      - uses: actions/checkout@v7
      - id: f
        uses: dorny/paths-filter@v4
        with:
          filters: |
            go:     ['go.mod', 'go.sum', '**/*.go', '**/testdata/**']
            python: ['pyproject.toml', 'uv.lock', 'substrate/python/**', 'homelab/**', 'integrations/mcp/**']
            plugin: ['integrations/claude-code/**']
            image:  ['deploy/homelab/**', 'substrate/python/**', 'homelab/service/**', 'uv.lock']

  docs:                                   # always runs: cheap, guards the frozen evidence
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with: { fetch-depth: 0 }
      - run: python3 scripts/validate_docs.py
      - name: Frozen evidence not modified
        env:
          BASE: ${{ github.event.pull_request.base.sha || github.event.before }}
        run: |
          changed=$(git diff --name-only --diff-filter=MDRT "$BASE" HEAD -- \
              docs/history ':(glob)docs/contracts/*/*/**' docs/research/harness-research-2026-10 \
            | grep -v '^docs/research/harness-research-2026-10/README.md$' || true)
          if [ -n "$changed" ]; then echo "::error::frozen files modified"; echo "$changed"; exit 1; fi

  go:
    needs: changes
    if: needs.changes.outputs.go == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-go@v7
        with:
          go-version-file: go.mod          # uses the toolchain directive when present
          cache-dependency-path: go.sum    # default key is go.mod; point it at go.sum
      - run: test -z "$(gofmt -l .)"
      - run: go mod tidy -diff
      - run: go vet ./...
      - run: go test -race ./...
      - run: CGO_ENABLED=0 go build -trimpath ./...

  python:
    needs: changes
    if: needs.changes.outputs.python == 'true'
    runs-on: ubuntu-latest
    strategy:
      matrix: { python: ['3.13', '3.14'] }
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@v10.3.0     # no floating @vN tags since v8: pin a release or a SHA
        with:
          python-version: ${{ matrix.python }}
          enable-cache: true
      - run: uv sync --locked --all-packages
      - run: uv run --all-packages pytest
      - run: uv cache prune --ci

  image-build:                              # build only; pushing happens on release
    needs: changes
    if: needs.changes.outputs.image == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: docker/setup-buildx-action@v4
      - uses: docker/build-push-action@v7
        with:
          context: .
          file: deploy/homelab/Dockerfile
          push: false
          cache-from: type=gha
          cache-to: type=gha,mode=max

  plugin:
    needs: changes
    if: needs.changes.outputs.plugin == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - run: python3 -m json.tool integrations/claude-code/odin/.claude-plugin/plugin.json >/dev/null
      # `claude plugin validate --strict integrations/claude-code` is the authoritative check;
      # run it locally (just plugin-check) or install the CLI here if you want it gated.

  ci-ok:
    if: always()
    needs: [docs, go, python, image-build, plugin]
    runs-on: ubuntu-latest
    steps:
      - run: |
          echo '${{ toJSON(needs) }}' \
            | jq -e 'to_entries | all(.value.result == "success" or .value.result == "skipped")'
```

For a per-language matrix instead of separate jobs, feed the filter's
`changes` output, a "JSON array with names of all filters matching any
of the changed files", into `strategy.matrix.lang: ${{ fromJSON(needs.changes.outputs.changes) }}`
and run `just ci-${{ matrix.lang }}`. Separate jobs are easier to read
when each language needs different setup actions.

### 6.3 `release.yml`

```yaml
name: release
on:
  push:
    tags: ['*/v*']            # homelab/v1.2.3, workstation/v…, harness/v…, heimdall/v…, skald/v…
permissions:
  contents: write             # gh release create
  packages: write             # ghcr.io

jobs:
  meta:
    runs-on: ubuntu-latest
    outputs:
      name: ${{ steps.m.outputs.name }}
      version: ${{ steps.m.outputs.version }}
      kind: ${{ steps.m.outputs.kind }}
      main: ${{ steps.m.outputs.main }}
      bin: ${{ steps.m.outputs.bin }}
    steps:
      - uses: actions/checkout@v7
      - id: m
        run: |
          name="${GITHUB_REF_NAME%%/*}"; version="${GITHUB_REF_NAME#*/v}"
          jq -e --arg n "$name" --arg v "$version" '.deployables[$n].version == $v' release/manifest.json \
            || { echo "::error::manifest does not say $name=$version"; exit 1; }
          for k in kind main bin; do
            echo "$k=$(jq -r --arg n "$name" --arg k "$k" '.deployables[$n][$k] // ""' release/manifest.json)" >> "$GITHUB_OUTPUT"
          done
          echo "name=$name" >> "$GITHUB_OUTPUT"; echo "version=$version" >> "$GITHUB_OUTPUT"

  go-binary:
    needs: meta
    if: needs.meta.outputs.kind == 'go'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with: { fetch-depth: 0 }
      - uses: actions/setup-go@v7
        with: { go-version-file: go.mod, cache-dependency-path: go.sum }
      - env:
          V: ${{ needs.meta.outputs.version }}
          MAIN: ${{ needs.meta.outputs.main }}
          BIN: ${{ needs.meta.outputs.bin }}
          GH_TOKEN: ${{ github.token }}
        run: |
          mkdir -p dist
          for arch in amd64 arm64; do
            d="$BIN-$V-linux-$arch"; mkdir -p "dist/$d"
            CGO_ENABLED=0 GOOS=linux GOARCH=$arch go build -trimpath \
              -ldflags "-s -w -X main.version=$V" -o "dist/$d/$BIN" "$MAIN"
            cp LICENSE NOTICE "dist/$d/"
            tar -C dist -czf "dist/$d.tar.gz" "$d"
          done
          (cd dist && sha256sum *.tar.gz > SHA256SUMS)
          git fetch --force origin "refs/tags/$GITHUB_REF_NAME:refs/tags/$GITHUB_REF_NAME"   # keep the annotated tag object
          git tag -l --format='%(contents)' "$GITHUB_REF_NAME" > notes.md   # release.py wrote path-scoped notes
          gh release create "$GITHUB_REF_NAME" dist/*.tar.gz dist/SHA256SUMS \
            --title "$GITHUB_REF_NAME" --notes-file notes.md

  homelab-image:
    needs: meta
    if: needs.meta.outputs.kind == 'image'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: docker/setup-buildx-action@v4
      - uses: docker/login-action@v4
        with: { registry: ghcr.io, username: '${{ github.actor }}', password: '${{ github.token }}' }
      - id: tags
        uses: docker/metadata-action@v6
        with:
          images: ghcr.io/${{ github.repository_owner }}/odin-homelab
          tags: |
            type=match,pattern=homelab/v(\d+\.\d+\.\d+),group=1
            type=sha
      - uses: docker/build-push-action@v7
        with:
          context: .
          file: deploy/homelab/Dockerfile
          push: true
          tags: ${{ steps.tags.outputs.tags }}
          labels: ${{ steps.tags.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  plugin:
    needs: meta
    if: needs.meta.outputs.kind == 'plugin'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with: { fetch-depth: 0 }
      - env: { GH_TOKEN: '${{ github.token }}' }
        run: |
          git fetch --force origin "refs/tags/$GITHUB_REF_NAME:refs/tags/$GITHUB_REF_NAME"
          (cd integrations/claude-code && zip -r "../../odin-plugin-${{ needs.meta.outputs.version }}.zip" odin)
          gh release create "$GITHUB_REF_NAME" odin-plugin-*.zip --title "$GITHUB_REF_NAME" \
            --notes "$(git tag -l --format='%(contents)' "$GITHUB_REF_NAME")"
```

Notes:

- **Tags created with `GITHUB_TOKEN` do not start workflows.** "Events
  triggered by the GITHUB_TOKEN will not create a new workflow run",
  except `workflow_dispatch` and `repository_dispatch`. Push release
  tags from your own machine (`scripts/release.py --push`). If you
  automate tagging in CI, build in the same workflow run or use a GitHub
  App or personal access token.
- **GoReleaser's `monorepo.tag_prefix` is "exclusively available with
  GoReleaser Pro".** That's why the job above uses plain `go build` and
  `gh release`.
- With prefixed tags, `gh release create --generate-notes` needs
  `--notes-start-tag <name>/v<prev>`. Otherwise it may diff against the
  latest tag of a *different* deployable. The tag-message notes avoid
  that.
- **Billing, private repositories on GitHub Free:**
  - 2,000 Actions minutes and 500 MB of artifact storage per month, plus
    10 GB of cache per repository.
  - Public repositories on standard runners are free.
  - Container registry storage and bandwidth is "currently free".
  - The announced $0.002/min fee for self-hosted runners was postponed
    and, as of mid-2026, had not taken effect.

### 6.4 Caching summary

| Language | Mechanism |
|---|---|
| Go | `actions/setup-go@v7` caches modules and the build cache. Its default key is `go.mod`, so set `cache-dependency-path: go.sum`. Adding `**/*.go` would create a new cache on most commits. |
| Python | `astral-sh/setup-uv` caches automatically (`enable-cache: auto` on GitHub-hosted runners). Its default `cache-dependency-glob` covers `pyproject.toml` and `uv.lock`. Run `uv cache prune --ci` at the end. |
| TS | `actions/setup-node` with `cache: pnpm`, after `pnpm/action-setup`. |
| Docker | `cache-from/to: type=gha`, plus BuildKit `--mount=type=cache` for uv inside the Dockerfile. |

### 6.5 Versioning: one version for everything, or per deployable?

| | One version for everything (`v1.7.0`) | Per-deployable semver + repo-wide manifest |
|---|---|---|
| Tags | `v1.7.0` | `homelab/v0.4.0`, `workstation/v0.2.0`, `harness/v0.3.0`, plus continued lines `heimdall/v…`, `skald/v0.1.2` |
| What a version tells you | Only that *something* changed | Which deployable changed, and whether it broke compatibility |
| Redeploys | Every release rebuilds, retags and reinstalls all three, so the Arch package and daemon restart even for a homelab-only fix | Only the deployable that changed |
| Breaking changes | "A major change in any package will result in all packages having a new major version" (Lerna on fixed mode) | Local to the deployable |
| Go interplay | Root `vX` tags become Go module versions, and `v2.0.0` forces `/v2` import paths repo-wide | Go ignores them |
| Imported version lines | skald's v0.1.x line ends | Continues as `skald/v0.1.2` |
| "Which versions run together?" | Implicit | Explicit: `release/manifest.json` at any commit is the train |
| Tooling | Simplest | Needs a prefix-aware script (below). release-please handles it; GoReleaser OSS doesn't. |

**Recommendation: per-deployable semver with a repo-wide manifest.**
The manifest is the release train: at every commit it records which
versions of the three deployables belong together, and it is what you
deploy from.

```json
// release/manifest.json
{
  "train": "2026-10-16",
  "deployables": {
    "homelab":     { "version": "0.4.0", "kind": "image",  "python_packages": ["odin-service", "odin-substrate"],
                     "paths": ["homelab/", "substrate/", "deploy/homelab/", "pyproject.toml", "uv.lock"] },
    "workstation": { "version": "0.2.0", "kind": "go", "main": "./workstation/cmd/odin-workstation", "bin": "odin-workstation",
                     "paths": ["workstation/", "substrate/", "go.mod", "go.sum", "deploy/arch/odin-workstation/", "deploy/systemd/"] },
    "harness":     { "version": "0.3.0", "kind": "plugin",
                     "plugin_json": "integrations/claude-code/odin/.claude-plugin/plugin.json",
                     "paths": ["integrations/"] },
    "heimdall":    { "version": "0.1.0", "kind": "go", "main": "./heimdall/cmd/heimdall", "bin": "heimdall", "paths": ["heimdall/", "go.mod", "go.sum"] },
    "skald":       { "version": "0.1.2", "kind": "go", "main": "./skald/cmd/skald", "bin": "skald", "paths": ["skald/", "go.mod", "go.sum"] }
  }
}
```

### 6.6 The release script (stdlib only, like the validator) [rehearsed]

`scripts/release.py <deployable> <X.Y.Z> [--push]`:

1. Refuses a dirty tree, a branch other than main, an existing tag, or a
   version that doesn't increase.
2. Bumps the manifest, `plugin.json` (for the harness) and
   `uv version --package …` (for homelab).
3. Commits `release(<deployable>): vX.Y.Z` and creates an annotated tag
   `<deployable>/vX.Y.Z`. The tag message holds notes generated from
   `git log <prev-tag>..HEAD -- <paths>`.
4. Pushes with `--atomic`.

In the rehearsal the notes for `skald/v0.1.2` correctly listed
`fix(skald): …` and left out an unrelated `docs:` commit.

```python
#!/usr/bin/env python3
"""Cut one deployable release: bump release/manifest.json, commit, tag <deployable>/vX.Y.Z.

Usage: python3 scripts/release.py <deployable> <X.Y.Z> [--push]
"""
from __future__ import annotations
import datetime, json, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "release/manifest.json"

def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, text=True,
                          capture_output=True).stdout.strip()

def semver(v: str) -> tuple[int, ...]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", v):
        sys.exit(f"not X.Y.Z: {v}")
    return tuple(int(x) for x in v.split("."))

def main(argv: list[str]) -> None:
    push = "--push" in argv
    args = [a for a in argv if a != "--push"]
    if len(args) != 2:
        sys.exit(__doc__)
    name, version = args
    manifest = json.loads(MANIFEST.read_text())
    entry = manifest["deployables"].get(name) or sys.exit(f"unknown deployable: {name}")
    if semver(version) <= semver(entry["version"]):
        sys.exit(f"{name}: {version} is not greater than {entry['version']}")
    if git("status", "--porcelain"):
        sys.exit("working tree is not clean")
    if git("branch", "--show-current") != "main":
        sys.exit("not on main")
    tag = f"{name}/v{version}"
    if git("tag", "--list", tag):
        sys.exit(f"tag exists: {tag}")
    previous = f"{name}/v{entry['version']}"
    since = previous if git("tag", "--list", previous) else None

    entry["version"] = version
    manifest["train"] = datetime.date.today().isoformat()
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    if entry.get("kind") == "plugin":
        path = ROOT / entry["plugin_json"]
        plugin = json.loads(path.read_text())
        plugin["version"] = version
        path.write_text(json.dumps(plugin, indent=2) + "\n")
    for package in entry.get("python_packages", []):
        subprocess.run(["uv", "version", "--package", package, version], cwd=ROOT, check=True)

    log_range = [f"{since}..HEAD"] if since else ["HEAD"]
    notes = git("log", "--format=- %s (%h)", *log_range, "--", *entry["paths"])
    git("commit", "-am", f"release({name}): v{version}")
    git("tag", "-a", tag, "-m", f"{name} v{version}\n\n{notes or '- no path-scoped changes'}")
    print(f"tagged {tag}\n{notes}")
    if push:
        git("push", "--atomic", "origin", "main", tag)
    else:
        print(f"push with: git push --atomic origin main {tag}")

if __name__ == "__main__":
    main(sys.argv[1:])
```

Shared code changes don't bump anything on their own. When `substrate/`
changes, release each deployable that should ship it. Their `paths`
include `substrate/`, so the notes will show the change.

### 6.7 Alternative: release-please in manifest mode

This fits if you want generated changelogs and an automated "release
PR". The verified config options are `include-component-in-tag`,
`tag-separator`, `include-v-in-tag`, `separate-pull-requests`,
`extra-files` and `exclude-paths`.

```json
// release-please-config.json
{
  "include-component-in-tag": true,
  "tag-separator": "/",
  "separate-pull-requests": false,
  "packages": {
    "homelab":     { "component": "homelab",     "release-type": "python" },
    "workstation": { "component": "workstation", "release-type": "go" },
    "integrations/claude-code": {
      "component": "harness", "release-type": "simple",
      "extra-files": [{ "type": "json", "path": "odin/.claude-plugin/plugin.json", "jsonpath": "$.version" }] }
  }
}
```

The single combined release PR acts as the train, and
`.release-please-manifest.json` records path → version. Caveats:

- It needs conventional commits. You already use them
  (`docs: bootstrap …`).
- It keys each component by **one path**, so a commit that only touches
  `substrate/` bumps no deployable.
- It tags with `GITHUB_TOKEN` unless you give it a personal access
  token. Then tag-triggered `release.yml` won't run, so build inside the
  same workflow using its outputs:
  `steps.release.outputs['workstation--release_created']`.

For one operator, the 60-line script above is less machinery.

---

## 7. Packaging for Arch / Omarchy

### 7.1 A PKGBUILD that builds one binary from the monorepo

```bash
# deploy/arch/odin-workstation/PKGBUILD — release package pinned to a deployable tag
pkgname=odin-workstation
pkgver=0.2.0
pkgrel=1
pkgdesc='Odin workstation daemon'
arch=('x86_64' 'aarch64')
url='https://github.com/algorhythmic/odin'
license=('Apache-2.0')
makedepends=('go' 'git')
options=('!debug')
source=("odin::git+ssh://git@github.com/algorhythmic/odin.git#tag=workstation/v${pkgver}")
sha256sums=('SKIP')            # or run `makepkg -g`: pacman 7 can checksum pinned git sources
_main=./workstation/cmd/odin-workstation

prepare() {
  cd odin
  export GOPATH="$srcdir/gopath"
  go mod download -modcacherw
}

build() {
  cd odin
  export GOPATH="$srcdir/gopath"
  export CGO_ENABLED=0
  # Arch's guideline flags, minus -ldflags=-linkmode=external (that needs cgo):
  export GOFLAGS="-buildmode=pie -trimpath -mod=readonly -modcacherw"
  go build -ldflags "-X main.version=${pkgver}" -o "build/${pkgname}" "${_main}"
}

check() {
  cd odin
  go test ./workstation/... ./substrate/...
}

package() {
  cd odin
  install -Dm755 "build/${pkgname}" "$pkgdir/usr/bin/${pkgname}"
  install -Dm644 "deploy/systemd/user/${pkgname}.service" "$pkgdir/usr/lib/systemd/user/${pkgname}.service"
  install -Dm644 LICENSE NOTICE -t "$pkgdir/usr/share/licenses/${pkgname}/"
}
```

There are two other ways to source the build:

- **A `-git` package tracking main.** Set
  `pkgname=odin-workstation-git`, add
  `provides=(odin-workstation) conflicts=(odin-workstation)`, use
  `source=("odin::git+file:///home/david/Projects/odin#branch=main")`,
  and derive the version from the deployable's tags:
  ```bash
  pkgver() {
    cd odin
    git describe --long --tags --abbrev=7 --match 'workstation/v[0-9]*' \
      | sed 's|^workstation/v||;s/\([^-]*-g\)/r\1/;s/-/./g'
  }
  ```
- **The local working tree, including uncommitted work.** This is
  today's heimdall pattern, adapted for a monorepo. Find the repository
  root instead of assuming `$startdir` is the root:
  ```bash
  _root() { git -C "$startdir" rev-parse --show-toplevel; }
  pkgver() {
    git -C "$(_root)" describe --long --tags --abbrev=7 --match 'heimdall/v[0-9]*' 2>/dev/null \
      | sed 's|^heimdall/v||;s/\([^-]*-g\)/r\1/;s/-/./g' \
      || printf 'r%s.g%s' "$(git -C "$(_root)" rev-list --count HEAD)" "$(git -C "$(_root)" rev-parse --short HEAD)"
  }
  prepare() {
    rm -rf "$srcdir/odin"; mkdir -p "$srcdir/odin"
    (cd "$(_root)" && git ls-files -co --exclude-standard -z | tar --null -T - -cf -) | tar -C "$srcdir/odin" -xf -
  }
  ```

Ignore makepkg's outputs in the repository
(`deploy/arch/*/{src,pkg}/` and `*.pkg.tar.*`). The validator's
`rglob` would otherwise wander into `src/`.

### 7.2 User-level systemd units

```ini
# deploy/systemd/user/odin-workstation.service
[Unit]
Description=Odin workstation daemon
PartOf=graphical-session.target
After=graphical-session.target

[Service]
ExecStart=/usr/bin/odin-workstation run
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical-session.target
```

```bash
makepkg -si                                   # from deploy/arch/odin-workstation/
systemctl --user daemon-reload
systemctl --user enable --now odin-workstation.service
# pacman never restarts user services; after an upgrade:
systemctl --user restart odin-workstation.service
```

- Packaged user units belong in `/usr/lib/systemd/user/`. Root's
  `systemctl enable` only manages system units, so enable user units
  per user, or use `systemctl --global enable` to enable them for every
  user.
- On this machine Omarchy runs Hyprland under uwsm (`uwsm 0.26.7-1`) and
  `graphical-session.target` is active, so binding sensors and capture
  to that target is correct. `Linger=no`: user services start at login,
  not at boot. Use `loginctl enable-linger` only if the daemon must run
  without a session.
- **Copies in `~/.config` take precedence.** The user unit search path
  puts `~/.config/systemd/user` before `/usr/lib/systemd/user`
  (confirmed with `systemd-analyze --user unit-paths`). Today's units
  (`hush.service`, `voxtype.service`, …) live in `~/.config/systemd/user`.
  When heimdall or skald units move into packages, delete or
  `systemctl --user revert` the old copies, or they silently shadow the
  packaged unit.

### 7.3 `makepkg -si` or a local repository?

- **One Arch machine (now):** `just pkg-workstation`, which runs
  `makepkg -srci --cleanbuild`. That's the simplest option and needs no
  repository.
- **Two or more (workstation plus laptop):** build once, then
  `repo-add /srv/arch/odin.db.tar.zst *.pkg.tar.zst`. Serve that
  directory from the homelab over HTTP and add to each machine's
  `/etc/pacman.conf`:
  ```ini
  [odin]
  SigLevel = Optional TrustAll   # or sign with `makepkg --sign` and use PackageRequired
  Server = https://homelab.lan/arch/$arch
  ```
  The repository's name is the database filename without its extension.
  Then `pacman -Syu` updates every machine. A CI job in an
  `archlinux:base-devel` container could attach the `.pkg.tar.zst` to
  the GitHub release, but makepkg refuses to run as root, so the job
  needs a build user. It isn't worth it until you have a second machine.

---

## 8. Licensing

**Current state:**

- Odin's root `LICENSE` is Apache-2.0 but **not yet committed**
  (`?? LICENSE` in git status).
- heimdall, skald and braid each carry Apache-2.0, added on 2026-10-14.
- Two repositories have no license.
- dotprivate is MIT and stays separate.
- `docs/DECISIONS.md` (ODIN-ADR-001) already records "Apache-2.0 as the
  project default, with MIT for dotprivate".

**Steps:**

1. Commit the root `LICENSE`, the unmodified Apache-2.0 text.
2. Add a short `NOTICE`. Apache-2.0 does not require one, but once
   present, §4(d) obliges anyone redistributing to carry it, so keep it
   minimal. The ASF guidance applies by analogy: "Do not add anything to
   NOTICE which is not legally required." Example:
   ```text
   Odin
   Copyright 2026 David Alexander Dunn

   Includes the formerly separate projects heimdall, skald and braid
   (Copyright 2026 David Alexander Dunn), imported with their history.
   ```
3. **Duplicate LICENSE files.** After the move, the imported
   `heimdall/LICENSE` and the others can be deleted, because the root
   file covers a single Go module. **Keep or add copies** wherever a
   distribution is cut from a subdirectory:
   - `integrations/claude-code/odin/LICENSE`, because a `git-subdir`
     plugin source is fetched with a sparse checkout of that path only;
   - each Python member, because `license-files` globs "MUST NOT" use
     `..`;
   - Docker images (`COPY LICENSE NOTICE`);
   - Arch packages (`install … /usr/share/licenses/`). Use
     `license=('Apache-2.0')`, not `custom` as heimdall's PKGBUILD has
     today.
4. **The two unlicensed repositories.** As sole author you can license
   them on import. Check `git shortlog -sne --all` for other human
   contributors first. Record the relicensing (repositories, date, sole
   authorship) in the same ADR as the import. Their archived originals
   stay "no license", which is fine.
5. **SPDX headers are optional.** If you want them, follow REUSE:
   `// SPDX-FileCopyrightText: 2026 David Alexander Dunn` and
   `// SPDX-License-Identifier: Apache-2.0`. Annotate files that cannot
   carry headers through `REUSE.toml`. That includes **everything under
   `docs/history/`**, where adding a header would break the digests.
6. **Third-party notices.** heimdall has `docs/licenses/` with 30 files
   in version-pinned directories (for example
   `gopkg.in_yaml.v3_v3.0.1/NOTICE`). After `go mod tidy` on the merged
   module, MVS may pick other versions, so those directories go stale.
   Regenerate one tree for each shipped binary from
   `go list -deps -f '{{with .Module}}{{.Path}} {{.Version}}{{end}}' ./heimdall/cmd/heimdall | sort -u`,
   or with a tool such as `google/go-licenses`, into `third_party/<bin>/`.
   Ship that tree inside the tarball and the package. Per the ASF howto,
   bundled MIT and BSD dependencies need a pointer and their license
   text, but no NOTICE entry. Apache-2.0 dependencies that ship their own
   NOTICE (yaml.v3) must have it reproduced with the binary.
7. **dotprivate (MIT)** stays separate, so nothing changes. If MIT code
   is ever copied in, keep its license text beside it and add a pointer
   in `LICENSE`.

---

## 9. Repository hygiene for this case

- **CODEOWNERS:** not needed for one person.
- **Branch protection, kept minimal:**
  - protect `main` from force-pushes and deletion;
  - require only `ci-ok`, and only on PRs;
  - give yourself a bypass, so that import merges and release commits
    can be pushed directly.

  Rulesets and protected branches on *private* repositories have
  historically needed a paid plan (Pro for personal accounts). Check
  your plan. Push rulesets that block paths (for example
  `docs/history/**`) target private and internal repositories on Team
  and Enterprise plans, so on a personal account rely on CI and hooks.
- **Keep `docs/history/` verifiable while everything else churns:**
  - The validator already compares SHA-256 digests and an exact file
    allowlist for the snapshot. Run it in the always-on `docs` job.
  - Add the `--diff-filter=MDRT` guard from §6.2. Additions such as a
    new snapshot or a new pinned contract stay allowed; edits do not.
  - Locally, add a hook (`git config core.hooksPath .githooks`):
    ```bash
    # .githooks/pre-commit
    if git diff --cached --name-only --diff-filter=MDRT -- docs/history | grep -q .; then
      echo "refusing: docs/history is frozen"; exit 1; fi
    python3 scripts/validate_docs.py >/dev/null || { python3 scripts/validate_docs.py; exit 1; }
    ```
  - Keep `docs/` at the repository root and `scripts/validate_docs.py`
    where it is. `ROOT = parents[1]` and the required-file list assume
    that layout.
- **`.gitattributes`:**
  ```gitattributes
  # Frozen evidence: byte-exact on every checkout (no EOL conversion)
  docs/history/**                            -text
  docs/contracts/*/*/**                      -text
  docs/research/harness-research-2026-10/*.md -text
  # Lockfiles/generated: collapsed in GitHub diffs, excluded from language stats
  go.sum          linguist-generated
  uv.lock         linguist-generated
  pnpm-lock.yaml  linguist-generated
  **/*.pb.go      linguist-generated
  # Must stay LF for bash/makepkg/systemd
  *.sh            text eol=lf
  PKGBUILD        text eol=lf
  *.service       text eol=lf
  ```
  GitHub hides files marked `linguist-generated` in diffs by default and
  leaves them out of language statistics. `-text` protects the digests
  from `core.autocrlf` on another machine.
- **`.gitignore` additions:** `.venv/`, `node_modules/`, `dist/`,
  `deploy/arch/*/src/`, `deploy/arch/*/pkg/`, `*.pkg.tar.*`, and
  `go.work*`, in case one is created locally.
- **Conventional commits:** keep them. You already use them, and with a
  scope they make path-scoped notes and `git log --grep` useful:
  `feat(workstation): …`, `fix(heimdall): …`, `chore(import): …`,
  `release(harness): v0.3.0`. Enforce them with tooling only if you
  adopt release-please.
- **Dependabot:** one `.github/dependabot.yml` with one entry per
  ecosystem (`gomod`, `uv`, `github-actions`, `docker`), each with
  `directory: "/"` or `directories: […]`. Group updates to cut PR noise.

---

## 10. Recommended layout

### 10.1 Odin in Python (primary)

```text
odin/
├── README.md  AGENTS.md  CLAUDE.md  LICENSE  NOTICE  justfile  .gitattributes  .gitignore
├── go.mod  go.sum                      # one Go module: github.com/algorhythmic/odin
├── pyproject.toml  uv.lock  .python-version   # uv workspace root (virtual)
├── release/manifest.json               # the release train
├── .github/workflows/{ci.yml,release.yml}  .github/dependabot.yml  .githooks/pre-commit
│
├── substrate/                          # shared substrate
│   ├── schemas/                        # JSON Schema record contracts + fixtures (language-neutral; I0)
│   ├── eventlog/  records/  ids/       # Go packages: github.com/algorhythmic/odin/substrate/...
│   └── python/                         # uv member odin-substrate: models/validators for the same schemas
│
├── homelab/                            # DEPLOYABLE 1: homelab service (several processes)
│   ├── service/                        # uv member odin-service; [project.scripts] = one entry per process
│   └── <legacy-service>/               # dormant Python service (member, or excluded with its own lock)
├── workstation/                        # DEPLOYABLE 2: workstation daemon (Go)
│   ├── cmd/odin-workstation/
│   └── internal/{sensors,capture,...}/
├── integrations/                       # DEPLOYABLE 3: harness integration packages
│   ├── claude-code/
│   │   ├── .claude-plugin/marketplace.json
│   │   └── odin/                       # plugin root: .claude-plugin/plugin.json, skills/, hooks/, .mcp.json, LICENSE
│   └── mcp/odin-mcp/                   # uv member: MCP server package
│
├── heimdall/  skald/  braid/           # imported projects, history intact; heimdall and skald still build standalone
│
├── deploy/
│   ├── homelab/                        # Dockerfile, Dockerfile.dockerignore, compose.yaml, .env.example
│   ├── arch/{odin-workstation,heimdall,skald}/PKGBUILD
│   └── systemd/user/*.service
├── scripts/                            # validate_docs.py, release.py, imports/*.commit-map
└── docs/                               # unchanged; docs/history/** frozen
```

Why this shape:

1. **The top level is organised by deployable** (`homelab/`,
   `workstation/`, `integrations/`), not by language. Path filters,
   release notes, the manifest's `paths` and the Docker COPY lines then
   map one-to-one onto what you deploy. One root `go.mod` and one root
   uv workspace make that possible, because neither tool cares where its
   directories sit.
2. **The substrate is shared through contracts, not code.** A Go daemon
   and a Python service cannot import each other. `substrate/schemas/`
   holds JSON Schema and fixtures, the "versioned record schemas" of
   I0. Go packages and the Python member are tested against it. Go code
   shared on purpose lives in `substrate/` and is importable everywhere,
   while each imported tree keeps its own `internal/`.
3. **Imported projects stay whole at the top level**, just as each one
   landed from `--to-subdirectory-filter`. Their `git log` needs no
   `--follow`, their sibling-relative doc links (`../heimdall/…`) still
   resolve (measured in §2.5), and `go build ./heimdall/cmd/heimdall`
   keeps them standalone. Fold braid into `substrate/` later with
   `git mv` if it really is the substrate.
4. **The plugin is self-contained under `integrations/claude-code/odin/`.**
   That follows CLAUDE.md ("keep them under the package's own
   directory") and the plugin rule that paths cannot escape the plugin
   root. Register its marketplace from a subdirectory instead of the
   repository root:
   ```json
   { "extraKnownMarketplaces": { "odin": { "source": {
       "source": "github", "repo": "algorhythmic/odin", "ref": "harness/v0.3.0",
       "path": "integrations/claude-code/.claude-plugin/marketplace.json",
       "sparsePaths": ["integrations/claude-code"] } } } }
   ```
   On the workstation, `claude plugin marketplace add ~/Projects/odin/integrations/claude-code`
   loads it in place. Setting `version` in `plugin.json` gates updates:
   users "stay on their cached copy until the string changes".
5. **`docs/` and `scripts/validate_docs.py` keep their paths**, so the
   validator's `ROOT`, its required files and the snapshot paths in
   `EXTRACTION-MANIFEST.json` keep working.

### 10.2 Odin in TypeScript (alternative)

Only these parts change:

```text
├── package.json  pnpm-workspace.yaml  pnpm-lock.yaml   # pnpm workspace root
├── substrate/ts/                       # @odin/substrate: types generated from substrate/schemas
├── homelab/service/                    # @odin/service (TS) with package.json bin entries per process
├── integrations/claude-code/odin/      # hooks may be TS, built into the plugin dir (no build step at install)
├── integrations/mcp/odin-mcp/          # stays Python (uv member) if it is Python today
└── pyproject.toml  uv.lock             # uv workspace survives for the MCP server and the legacy service
```

The homelab Dockerfile becomes
`pnpm --filter @odin/service --prod deploy /out` in a build stage,
copied into `node:24-slim`. CI gains a `ts` job (`pnpm/action-setup`,
`actions/setup-node` with `cache: pnpm`,
`pnpm install --frozen-lockfile`, `pnpm -r test`) and a `ts` filter in
`changes`. Go, Arch packaging and versioning stay the same. Generating
TS types from `substrate/schemas` keeps one source of truth for both
languages.

---

## 11. Anti-patterns and failure stories (small-team polyglot monorepos)

1. **Repositories whose shared libraries drift.** Segment (2018): "we
   added over 50 new destinations, and that meant 50 new repos". Then
   "the versions of these shared libraries began to diverge across the
   different destination codebases". The fix was one repository and
   "for each of the 120 unique dependencies, we committed to having one
   version". The lesson for here: one `go.mod`, one `uv.lock`. A monorepo
   with per-directory lockfiles brings the drift back.
2. **Adopting a meta-build system before you have the pain.** 11.2% of
   542 projects that adopted Bazel later dropped it, after a median of
   638 days. Many went back to Go build or Make (Alfadel & McIntosh,
   ICSE 2024). Mozilla's blog summarises a "Bazel Fawlty" account (not
   read directly) of a Go team that spent eight months porting to Bazel
   and switched back over slower builds and poor developer experience.
3. **Multi-module Go without the tooling it needs.** OpenTelemetry-Go
   uses `multimod` and `versions.yaml` to tag module sets. Its release
   doc warns that "Go module tags cannot currently be removed once
   incorrectly pushed", and the Go reference says tags "should not be
   deleted or changed".
4. **Committing `go.work`.** The Go workspace design was revised to
   "clearly discourage go.work files in repos". A checked-in file
   overrides developers' own workspaces and can test against the wrong
   dependency versions in CI.
5. **Lockstep versions in a mixed-cadence repository.** Lerna's fixed
   mode: "a major change in any package will result in all packages
   having a new major version". In Go, root `v2+` tags also force `/v2`
   import paths.
6. **Squash-merging the import.** "If you squashed the PR before
   committing, all history would be gone" (Netlify). Branch protection
   can block the merge commit, so allow yourself a bypass for the
   import.
7. **Making path-filtered workflows required checks.** They "stay in a
   'Pending' state and block merging". Use a job-level `if:` and an
   aggregator job.
8. **Expecting CI-created tags to start release workflows.** Tags and
   PRs created with `GITHUB_TOKEN` "will not trigger future GitHub
   actions workflows" (release-please-action README, GitHub docs).
9. **Assuming the open-source release tool understands tag prefixes.**
   GoReleaser's monorepo support is Pro-only.
10. **LFS-tracked plugin files.** Claude Code's plugin clones "never
    download LFS content". They get pointer files.
11. **Imported CI that silently stops.** Workflows under
    `<subdir>/.github/workflows/` are inert (observed with heimdall's
    `test.yml`).
12. **`--locked` in a Docker build of a workspace subset.** It fails when
    any member is missing from the build context **[rehearsed]**. Use
    `--frozen` there and `--locked` in CI.
13. **Stale user units shadowing packaged ones.** `~/.config/systemd/user`
    takes precedence over `/usr/lib/systemd/user`.
14. **Deleting or renaming the old repositories.** That would break about
    846 commit-pinned links in Odin's frozen research (§1.4).

---

## 12. Order of operations

1. Resolve the governance points in §1: an ADR superseding D14.1, the
   D13 note, an X-n issue for Saga, and a note on the X-5 placeholder
   names. Commit `LICENSE`.
2. Scope the validator's link check (§2.5). Add `.gitattributes`, the
   `.gitignore` entries and the frozen-tree hook.
3. Freeze heimdall, skald and braid: commit everything and stop work.
   Import them on `import/2026-10` (§2.2). Save the commit maps.
   Fast-forward main and push with `--tags`.
4. In separate commits:
   - create the single `go.mod`;
   - rewrite imports;
   - add the `ignore` directive;
   - run `go mod tidy`, `go test ./...` and build every `cmd`;
   - move PKGBUILDs and units into `deploy/`;
   - delete `~/.config` unit copies once the packaged ones are
     installed;
   - port the nested workflows into `ci.yml`.
5. Import the Python repositories the same way. Create the uv workspace
   and the lock, and the homelab Dockerfile and compose file.
6. Add `release/manifest.json`, `scripts/release.py`, `release.yml`, and
   the first tags: `skald/v0.1.2` and `heimdall/v0.1.0` continue those
   lines, and `workstation`, `homelab` and `harness` start at `0.1.0`.
7. Archive the old repositories with pointer READMEs (§2.4). Do not
   delete them.

---

## 13. Sources

Git and import
- git-filter-repo manual (options, commit-map, message hash rewriting, fresh-clone rule): https://man.archlinux.org/man/git-filter-repo.1.en
- Netlify, "Migrating Git from multirepo to monorepo without losing history": https://developers.netlify.com/guides/migrating-git-from-multirepo-to-monorepo-without-losing-history/
- Dominik Honnef, "Merging multiple git repositories" (why subtree merges break file history): https://dominik.honnef.co/articles/merging-multiple-git-repositories/
- DEV Community, merging old repos into a monolithic archive (tag-rename prefixes): https://dev.to/ctooley/merging-old-repos-into-a-monolithic-git-repo-archive-4c7h
- GitHub, archiving repositories: https://docs.github.com/en/repositories/archiving-a-github-repository/archiving-repositories
- GitHub, large files and size limits: https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github
- GitHub, Git LFS billing: https://docs.github.com/en/billing/concepts/product-billing/git-lfs

Go
- Managing module source (single vs multiple modules, subdirectory tags): https://go.dev/doc/modules/managing-source
- Go Modules Reference (tags in subdirectories, major version suffixes, `go install` rules, `ignore`, `toolchain`, GOWORK, zip contents): https://go.dev/ref/mod
- Go 1.24 release notes (VCS version stamping, tool directives): https://go.dev/doc/go1.24
- Go 1.25 release notes (`ignore` directive, `go version -m -json`, `work` pattern): https://go.dev/doc/go1.25
- Go 1.27 release notes: https://go.dev/doc/go1.27
- cmd/go (`-trimpath`, `-buildvcs`): https://pkg.go.dev/cmd/go
- internal packages across modules: https://golang.org/issue/38579 and https://go.googlesource.com/vgo/+/master/vendor/cmd/go/testdata/script/mod_internal.txt
- Workspace design discouraging committed go.work: https://go.googlesource.com/proposal/+/21bdf39b35012bd4b5f707e1fc8891869252987f%5E%21/ ; https://golang.org/issue/62179 ; https://appliedgo.net/spotlight/dont-check-in-gowork/
- Nested-module license detection on pkg.go.dev: https://golang.org/issue/37437 ; https://golang.org/issue/43817
- OpenTelemetry-Go multimod release process (mirror): https://github.com/jhannah-mm/opentelemetry-go/blob/main/RELEASING.md
- GoReleaser monorepo (Pro-only): https://goreleaser.com/customization/monorepo/

Python / uv
- uv workspaces: https://docs.astral.sh/uv/concepts/projects/workspaces/
- uv Docker guide: https://docs.astral.sh/uv/guides/integration/docker/
- uv GitHub Actions guide: https://docs.astral.sh/uv/guides/integration/github/
- uv dependencies (git sources, subdirectory): https://docs.astral.sh/uv/concepts/projects/dependencies/
- uv CLI reference: https://docs.astral.sh/uv/reference/cli/
- astral-sh/setup-uv (inputs; current release in README): https://github.com/astral-sh/setup-uv ; immutable releases / no floating tags: https://servala.app.codey.ch/servala/servala-portal/pulls/528
- pyproject `license` / `license-files`: https://packaging.python.org/en/latest/specifications/pyproject-toml/ ; glob rules ("Parent directory indicators (`..`) MUST NOT be used"): https://packaging.python.org/en/latest/specifications/glob-patterns/
- Python 3.15.0 release timing (secondary): https://www.python.org/downloads/release/python-3150rc3/ ; https://endoflife.ai/python/3.15

TypeScript / pnpm / Node
- pnpm workspaces: https://pnpm.io/workspaces ; pnpm deploy: https://pnpm.io/cli/deploy
- pnpm 11 release (settings move to pnpm-workspace.yaml, allowBuilds): https://pnpm.io/blog/releases/11.0 ; pnpm 12: https://pnpm.io/blog/releases/12.0
- Node 26 LTS timing (secondary): https://www.devx.com/coding/nodejs-26-lts-new-features-release-date/
- Corepack no longer bundled from Node 25 (secondary): https://blog.openreplay.com/manage-package-managers-node-corepack/
- Claude Agent SDK packages (secondary): https://www.morphllm.com/claude-agent-sdk

GitHub Actions and release tooling
- Workflow syntax (paths filters, tag filters, concurrency, 3,000-file limit): https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions
- Skipped-but-required checks: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks ; job conditions: https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-jobs-with-conditions
- GITHUB_TOKEN does not trigger workflows: https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow
- dorny/paths-filter: https://github.com/dorny/paths-filter
- actions/setup-go (v7, caching, toolchain directive): https://github.com/actions/setup-go
- docker/build-push-action: https://github.com/docker/build-push-action ; docker/metadata-action (`type=match`): https://github.com/docker/metadata-action
- Docker build context, Dockerfile-specific ignore files: https://docs.docker.com/build/concepts/context/
- release-please manifest mode: https://github.com/googleapis/release-please/blob/main/docs/manifest-releaser.md ; release types: https://github.com/googleapis/release-please/blob/main/docs/customizing.md ; config schema: https://raw.githubusercontent.com/googleapis/release-please/main/schemas/config.json ; action outputs and token caveat: https://github.com/googleapis/release-please-action
- Lerna fixed vs independent versioning: https://lerna.js.org/docs/features/version-and-publish
- Actions billing: https://docs.github.com/en/billing/concepts/product-billing/github-actions ; Packages billing: https://docs.github.com/en/billing/concepts/product-billing/github-packages ; self-hosted fee postponed: https://www.theregister.com/2025/12/17/github_charge_dev_own_hardware/
- Rulesets / push rules: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets ; https://github.blog/changelog/2024-09-10-push-rules-are-now-generally-available-and-updates-to-custom-properties/
- linguist-generated: https://docs.github.com/en/repositories/working-with-files/managing-files/customizing-how-changed-files-appear-on-github

Claude Code plugins
- Marketplaces and `git-subdir` sources: https://code.claude.com/docs/en/plugin-marketplaces ; reference: https://code.claude.com/docs/en/plugins/marketplace-reference
- Hosting, versions, LFS caveat: https://code.claude.com/docs/en/plugins/host-marketplace
- Manifest, `${CLAUDE_PLUGIN_ROOT}`/`${CLAUDE_PLUGIN_DATA}`, path containment: https://code.claude.com/docs/en/plugins-reference
- Plugin dependency tags (`<plugin>--v<version>`): https://code.claude.com/docs/en/plugins/dependencies

Arch / systemd
- ArchWiki VCS package guidelines (mirror; wiki.archlinux.org blocked automated fetches): https://cdn.jsdelivr.net/npm/arch-wiki-md-repo@0.10.84/wiki/_content/english/VCS%20package%20guidelines.md ; live page: https://wiki.archlinux.org/title/VCS_package_guidelines
- ArchWiki Go package guidelines (2026-04 mirror): https://wikipedia.jakami.de/content/archlinux_en_all_maxi_2026-04/Go_package_guidelines
- ArchWiki pacman tips, custom local repository (2026-04 mirror): https://wikipedia.jakami.de/content/archlinux_en_all_maxi_2026-04/Pacman/Tips_and_tricks
- ArchWiki systemd/User: https://wiki.archlinux.org/title/Systemd/User
- Hyprland wiki, uwsm and graphical-session.target: https://wiki.hypr.land/useful-utilities/uwsm/ ; https://wiki.hypr.land/Useful-Utilities/Systemd-start/
- Local: `man PKGBUILD` (USING VCS SOURCES), `man systemd.unit` (user load path), `systemd-analyze --user unit-paths`

Licensing
- Applying the Apache License: https://www.apache.org/legal/apply-license
- ASF LICENSE/NOTICE how-to: https://infra.apache.org/licensing-howto.html
- ASF source header policy: https://www.apache.org/legal/src-headers
- Apache License 2.0 text (§4(d) NOTICE): https://www.apache.org/licenses/LICENSE-2.0
- REUSE FAQ: https://reuse.software/faq/

Failure stories
- Segment, "Goodbye Microservices": https://www.twilio.com/en-us/blog/developers/best-practices/goodbye-microservices/
- Alfadel & McIntosh, "The Classics Never Go Out of Style" (ICSE 2024): https://rebels.cs.uwaterloo.ca/confpaper/2024/04/16/the-classics-never-go-out-of-style.html
- Mozilla blog roundup mentioning "Bazel Fawlty" (secondary): https://blog.mozilla.org/nfroyd/category/uncategorized/
