#!/usr/bin/env bash

set -eo pipefail

ERROR_IF_ABSENT=${ERROR_IF_ABSENT:-"true"}

if [ -z "${REPOSITORY}" ]; then
    echo "FATAL: No github repository specified; define 'REPOSITORY=owner/repo'" 1>&2
    exit 1
fi

if [ -z "${ARTIFACT}" ]; then
    echo "FATAL: No artifact name specified; define 'ARTIFACT=name'" 1>&2
    exit 1
fi

if [ -z "${GITHUB_TOKEN}" ]; then
    echo "FATAL: No Github API token specified; define 'GITHUB_TOKEN=token'" 1>&2
    exit 1
fi

artifactData=$(
    curl "https://api.github.com/repos/${REPOSITORY}/actions/artifacts?name=${ARTIFACT}" \
        --fail \
        --location \
        --header "Accept: application/vnd.github+json" \
        --header "Authorization: Bearer ${GITHUB_TOKEN}" \
        --header "X-GitHub-Api-Version: 2022-11-28"
)

echo "$artifactData" | jq --monochrome-output 1>&2

count=$(echo "$artifactData" | jq '.total_count')

# Github supports having multiple artifacts with the same name (for some reason)
# which we need to account for here. The better way to handle this would be to iterate
# over the list of returned artifacts and delete them all, but the bash to do that is
# non-trivial and I don't ant to write it right now. Where we're using this we don't need
# the ability to do this anyway, so for now we'll just error out if it's used that way.
# This may be worth implementing in the future.
if [ "$count" -gt 1 ]; then
    echo "ERROR: Multiple artifacts with name '${ARTIFACT}'" 1>&2
    exit 1
fi

if [ "$count" -eq 0 ] && [ "$ERROR_IF_ABSENT" = 'true' ]; then
    echo "ERROR: Artifact '${ARTIFACT}' does not exist" 1>&2
    exit 1
fi

echo artifact-id=$(echo "$artifactData" | jq '.artifacts[0].id') >>"$GITHUB_OUTPUT"
