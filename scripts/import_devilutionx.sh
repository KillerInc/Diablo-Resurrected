#!/usr/bin/env bash
# Run on a dedicated integration branch from a clean project checkout.
set -euo pipefail
if [[ -n "$(git status --porcelain)" ]]; then
    echo 'Working tree is not clean. Commit or stash first.' >&2
    exit 1
fi
if ! git remote get-url devilutionx >/dev/null 2>&1; then
    git remote add devilutionx https://github.com/diasurgical/DevilutionX.git
fi
git fetch devilutionx master
git merge --allow-unrelated-histories -X ours --no-edit devilutionx/master
echo 'Review merge, preserve notices, and run upstream tests.'
