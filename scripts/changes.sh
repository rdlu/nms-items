#!/usr/bin/env bash
# Which checks a set of changed paths needs. Reads the paths on stdin, one per
# line (git diff --name-only), and prints, as GITHUB_OUTPUT-style lines:
#
#   python=full|web|none   the whole suite, only the web slice, or nothing
#   web=true|false         svelte-check, the export and the site build
#   locations=true|false   the strict check of data/locations.json
#
# Prose alone needs none of them. data/locations.json alone (a portal address)
# needs only its own check: the suite's tests of it are that same validation,
# and the Pages build on main still exports it before anything goes live.
#
# Shared by .github/workflows/ci.yml and .githooks/pre-push, so CI and the
# local hook skip the same things. Conservative: a path not listed below runs
# everything. The shell lint is not decided here; it takes a second, so both
# always run it.
set -euo pipefail

python=none
web=false
locations=false
while IFS= read -r f; do
  [[ -n $f ]] || continue
  case $f in
    # Prose, and tooling that neither the suite nor the site reads.
    *.md | LICENSE | .github/ISSUE_TEMPLATE/config.yml | .github/dependabot.yml) ;;
    mise-tasks/* | .githooks/* | Containerfile | compose.yaml | .dockerignore | .gitignore) ;;
    # The pdf is built by hand (pdf:build) and committed under docs/pdf/.
    cheatsheet.typ) ;;
    # Shared portal addresses: validated on their own, see above.
    data/locations.json) locations=true ;;
    # The site's own source. The suite reads some of it (core.js against the
    # Python, the storage keys, the route table), so its fast web slice runs.
    site/* | package.json | package-lock.json | vite.config.js)
      web=true
      [[ $python == full ]] || python=web
      ;;
    # Tests do not feed the site build.
    tests/*) python=full ;;
    # src/, scripts/, data/, web/, docs/pdf and docs/img (the export copies
    # them), the lockfiles, mise.toml, the workflows, and anything new.
    *)
      python=full
      web=true
      ;;
  esac
done

echo "python=$python"
echo "web=$web"
echo "locations=$locations"
