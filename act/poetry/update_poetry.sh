#!/usr/bin/env bash
#
# This script can be used to quickly update the transient dependencies in the Poetry
# meta environment used by the composite action. The script isn't doing anything very
# complicated or unusual, it's just a convenience helper to make it easier to keep
# this lockfile up to date.
#
# To update the transient dependencies, simply run `update_poetry.sh` and your
# workstation's version of Poetry will be used to compute a valid lockfile that meets
# the version requirements, and then export that lockfile in requirements.txt format
# for the composite action to use.
#

set -e

function updatePoetry() {
    local target="${1}"
    local requirements="${1}/requirements.txt"
    local now=$(command date --iso-8601=minutes)

    local poetry_version_active=$(poetry --version --no-ansi)
    local poetry_version_installs="Poetry (version $(poetry show poetry --directory=$target | grep 'version' | cut -d ':' -f 2 | xargs))"

    echo "Updating Python dependencies for ${poetry_version_installs} using ${poetry_version_active}"
    poetry lock \
        --directory="${target}" \
        --no-interaction \
        --no-ansi

    echo "Exporting requirements from Poetry to Pip-compatible format"
    local requirements_tmp=$(mktemp --quiet)

    poetry export \
        --directory="${target}" \
        --format=requirements.txt \
        --output="${requirements_tmp}" \
        --no-interaction \
        --no-ansi \
        --quiet

    echo "Updating static requirements file at ${requirements}"

    cat > "${requirements}"<< EOF
# This file is generated automatically - Do not manually edit
#
# See https://github.com/freedomofpress/actionslib/ for more information
#
# Generated with ${poetry_version_active}
# Generated at ${now}
#
# This requirements file installs ${poetry_version_installs}
#
EOF

    cat "${requirements_tmp}" >> "${requirements}"

    rm --force "${requirements_tmp}"

    echo "Done"
}

function main() {
    local poetry_targets=$(ls --directory --color=never poetry-*)
    local local_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

    for target in ${poetry_targets}; do
        echo "Updating ${target}..."
        updatePoetry "${local_dir}/${target}"
    done
}

main "$@"
