#!/usr/bin/env bash

set -e

if [ -z "${REPOSITORY}" ]; then
    echo "FATAL: No github repository specified; define 'REPOSITORY=owner/repo'" 1>&2
    exit 1
fi

if [ -z "${ARTIFACT_ID}" ]; then
    echo "FATAL: No artifact ID specified; define 'ARTIFACT_ID=id'" 1>&2
    exit 1
fi

if [ -z "${GITHUB_TOKEN}" ]; then
    echo "FATAL: No Github API token specified; define 'GITHUB_TOKEN=token'" 1>&2
    exit 1
fi

curl "https://api.github.com/repos/${REPOSITORY}/actions/artifacts/${ARTIFACT_ID}" \
      --fail \
      --request DELETE \
      --location \
      --header "Accept: application/vnd.github+json" \
      --header "Authorization: Bearer ${GITHUB_TOKEN}" \
      --header "X-GitHub-Api-Version: 2022-11-28"

echo "Deleted ${REPOSITORY}/actions/artifacts/${ARTIFACT_ID}" 1>&2
