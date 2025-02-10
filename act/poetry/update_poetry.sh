#!/usr/bin/env bash

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
