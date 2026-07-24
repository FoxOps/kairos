# Versioning Policy - Kairos

## Scheme

Kairos follows [SemVer 2.0.0](https://semver.org/): `MAJOR.MINOR.PATCH`,
optionally followed by a pre-release identifier (`-rc1`, `-rc2`...). This
formalizes what the project already does in practice (`1.0.0-rc1` →
`1.0.0-rc2` → `1.0.0-rc3`), rather than introducing a new scheme.

CalVer was considered and rejected: Kairos has no fixed release cadence -
releases happen when a stabilization pass (security audit, bug hunt, load
test) is actually done, not on a calendar schedule. SemVer's
`MAJOR.MINOR.PATCH` already communicates the one thing that matters to a
self-hosting admin deciding whether to upgrade: whether the change is
breaking, additive, or a fix.

## Source of truth

`app/utils/health.py::APP_VERSION_DEFAULT` is the single source of truth
for the running app's version - imported by `app/__init__.py` (footer
context processor) and `/health`/`/version` (`app/utils/health.py`
itself), so they can never show two different values (this happened once
in the past: the footer stayed stuck on an old version after a bump
elsewhere). Overridable at runtime via the `APP_VERSION` env var (see
`.env.example`/`docker/.env.example`) - the constant is only the fallback
used when that env var isn't set.

`docker-release.yml` reads this same constant (via a `grep` against
`app/utils/health.py`, not a Python import, to avoid needing the full app
importable in a bare CI step) to tag the published Docker image - so this
one file is also what decides the image tag on `ghcr.io/foxops/kairos`.

**Don't** introduce a second place that hardcodes the version (a
`pyproject.toml` `version =`, a `VERSION` file, etc.) - there is
deliberately only one.

## Case convention: lowercase in the version string, uppercase in git refs

`APP_VERSION_DEFAULT`'s pre-release identifier is always **lowercase**
(`"1.0.0-rc3"`, never `"1.0.0-RC3"`) - the conventional casing for a
SemVer pre-release identifier, and important because SemVer identifiers
are compared byte-for-byte: `rc3` and `RC3` would sort as two *different*
identifiers to any tool that actually parses/compares them, even though
they mean the same release to a human.

Git tags and release-stabilization branches, on the other hand,
conventionally use **uppercase** `RC` (`1.0.0-RC3`, both the tag and the
branch merged PRs land on during this release's stabilization) - this
predates the current policy and is kept as-is rather than renamed, since
renaming an already-published git tag breaks anyone who already fetched
it, and renaming the current branch would break every open/merged PR
reference against it.

This is **not** a bug to reconcile by making the two identical strings -
it's a documented, intentional mapping between two different things (a
git ref name meant for humans skimming `git tag`/`git branch -a`, and a
SemVer identifier meant to be machine-compared). Tooling that needs to
compare the two (`scripts/check_version.py`, below) does so
case-insensitively, on purpose - never by requiring literal equality.

## Keeping the tag and the version string in sync: `make check-version`

Nothing previously guaranteed that the git tag pushed for a release
actually matched `APP_VERSION_DEFAULT` at the commit being tagged - both
were bumped/tagged by hand, independently. `scripts/check_version.py`
(`make check-version`) checks this: it requires `HEAD` to be exactly on a
git tag (`git describe --tags --exact-match`), reads
`APP_VERSION_DEFAULT`, and compares the two case-insensitively, failing
loudly on a mismatch.

Run it right after tagging a release, before running `docker-release.yml`
- not on every commit (it deliberately errors out if `HEAD` isn't on a
tag at all, since the check is meaningless anywhere else).

## Bumping the version: `make bump-version VERSION=1.0.0-rc4`

`scripts/bump_version.py` (`make bump-version VERSION=...`) validates the
new version against SemVer's shape (lowercase pre-release identifier
enforced, see above) and rewrites it in the 3 files that hold it in a
fixed, mechanically-parseable form: `app/utils/health.py`,
`.env.example`, `docker/.env.example`.

Prose docs that also mention the current version in free-form sentences
(`README.md`, `ROADMAP.md`, `Docs/guides/USER_GUIDE.md`) are **not**
rewritten automatically - a regex blindly replacing every occurrence of
the old version string risks corrupting a *historical* mention (e.g.
ROADMAP.md's own changelog-style references to `1.0.0-rc2`). Instead, the
script prints every line in those files that still contains the old
version, as a checklist for a manual pass.

Typical flow for a new release candidate:

```bash
make bump-version VERSION=1.0.0-rc4
# review/update the prose docs the script listed
git add -A && git commit -m "chore: bump la version à 1.0.0-rc4"
# ... open/merge the PR ...
git tag 1.0.0-RC4   # uppercase, per the convention above
git push origin 1.0.0-RC4
make check-version  # confirms the tag and APP_VERSION_DEFAULT agree
```

## Docker image tags

Today, `docker-release.yml` publishes exactly two tags per run:
`ghcr.io/foxops/kairos:<version>` (e.g. `1.0.0-rc3`) and `:latest`
(always overwritten, whatever was last built from `main`).

For a **stable** release (`MAJOR.MINOR.PATCH`, no pre-release
identifier), consider also publishing floating `MAJOR.MINOR` and `MAJOR`
tags (e.g. `1.0`, `1`) alongside the exact one - this lets an admin pin a
deployment to "any 1.0.x patch" or "any 1.x" without reconstructing the
tag on every release, the same convention most widely-used base images
follow (`python:3.12`, `postgres:16`...). To set this up:

1. In `docker-release.yml`'s `tags:` step (`docker/build-push-action`),
   compute `MAJOR` and `MAJOR.MINOR` from the version string extracted
   from `APP_VERSION_DEFAULT` (e.g. with a small `cut -d. -f1`/
   `cut -d. -f1,2` step, guarded to only run when the version has **no**
   pre-release suffix - a `-rc*` build must never overwrite a stable
   `1.0`/`1` floating tag).
2. Add the two extra `ghcr.io/foxops/kairos:<major>` /
   `ghcr.io/foxops/kairos:<major>.<minor>` lines to the `tags:` list,
   next to the existing exact-version and `:latest` ones.
3. Keep `:latest` itself unconditional (as today) - it already tracks
   "whatever was last built from `main`", which is a separate, simpler
   guarantee than the floating major/minor tags.
4. Pre-release builds (anything with a `-rc*`/pre-release suffix) should
   **not** get a floating tag at all, and should not touch `:latest`
   either if `main` at release time is expected to always be
   production-ready - otherwise a production deployment tracking
   `:latest` could silently pull a release candidate. Given
   `docker-release.yml` already only ever runs from `main`, and `main`
   only receives merges after a stabilization branch is done, `:latest`
   already reflects a real release, not an in-progress RC - so this is
   mostly a matter of gating the *new* floating major/minor tags, not
   changing `:latest`'s existing behavior.

Not implemented yet - this section is the plan to follow when the
project cuts its first fully stable (non-RC) release.

## Dev build metadata: `.github/workflows/docker-dev-build.yml`

`APP_VERSION_DEFAULT`/the git tag are for actual releases only - bumped
deliberately, once per release, per the flow above. In between releases,
a dev branch can be built and pushed as a disposable test image without
touching that version string at all, via a separate, `main`-excluded
workflow.

`docker-dev-build.yml` (manual-only, `workflow_dispatch`, same
minutes-conscious philosophy as `docker-release.yml`) computes a version
string of the form `<APP_VERSION_DEFAULT>+dev.<run number>.<short sha>` -
SemVer **build metadata** (the `+...` suffix defined by the spec itself,
never affecting version precedence/ordering, so it can never be mistaken
for or outrank a real release version) - and passes it into the image
build as the `APP_VERSION` build-arg (`docker/Dockerfile`). The running
container then reports this full string at `/version` and in the app
footer, with no extra runtime configuration needed - `os.environ.get
("APP_VERSION") or APP_VERSION_DEFAULT` (both call sites, `app/__init__.py`
and `app/utils/health.py`) already picks it up.

This is what "verify a test build is on the latest code" means in
practice: compare the short SHA shown at `/version` against `git
rev-parse --short HEAD` of the branch the image is supposed to have been
built from. The run number exists alongside the SHA as a free,
already-unique, monotonically increasing counter - nothing hand-maintained
to keep in sync across parallel branches, unlike a manually incremented
build counter would be.

**`main` never carries build metadata.** `docker-dev-build.yml`'s
`require-not-main` job refuses to run at all if triggered from `main` -
main is production, and a build produced by `docker-release.yml` always
reports a clean `APP_VERSION_DEFAULT` with no `+dev...` suffix (the
`APP_VERSION` build-arg is simply never passed on that path, so it stays
present-but-empty and falls back). This is a deliberate, enforced split,
not just a convention: a "production" image with build metadata attached
would blur the one thing `/version` exists to answer unambiguously - is
this exact container a real release, or a disposable test build.

Image tags: dev builds are pushed to the same `ghcr.io/foxops/kairos`
package as releases, but as `dev-<branch-slug>-<short-sha>` - never
`:latest` (reserved for the last real `docker-release.yml` build from
`main`) and never a bare version tag (reserved for an actual release).
Each dev build also gets the floating `:dev` tag, moved to point at
whichever dev build ran most recently (any branch) - "give me the
newest test image" without knowing the exact tag, same idea as
`:latest` but scoped to dev builds and never mixed with it.

**Retention: only the 5 most recent dev builds are kept.** A
`cleanup-old-dev-builds` job runs after every push
(`actions/delete-package-versions`), keeping the 5 newest package
versions and deleting the rest - `ignore-versions` excludes anything
tagged `latest`, `dev`, or a bare SemVer version from ever being counted
or deleted by this job, so it only ever prunes old
`dev-<branch-slug>-<short-sha>` versions, never a release. Without this,
a disposable-by-design build would accumulate in the registry forever.
