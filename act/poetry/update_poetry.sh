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

function main() {
    local poetry_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
    local requirements="${poetry_dir}/requirements-poetry.txt"
    local poetry_version=$(poetry --version)
    local now=$(command date --iso-8601=minutes)

    echo "Updating Python dependencies using ${poetry_version}"
    poetry lock \
        --directory="${poetry_dir}" \
        --no-interaction \
        --no-ansi

    echo "Exporting requirements from Poetry to Pip-compatible format"
    local requirements_tmp=$(mktemp --quiet)

    poetry export \
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
# Generated using ${poetry_version}
# Generated at ${now}

EOF

    cat "${requirements_tmp}" >> "${requirements}"

    rm --force "${requirements_tmp}"
    rm --recursive --force $(poetry env info --path)

    echo "Done"
}

main "$@"
