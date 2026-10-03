#!/usr/bin/env bash
# Fetch this runner's Nix tarball from a nix-quick-install-action release and
# verify it against nix-archives.sha256; upstream installs it unchecked. Drop
# this script once upstream verifies archives itself.
#
# Usage:
#   fetch-nix.sh               # CI: emit archives-url for nix_archives_url
#   fetch-nix.sh update <tag>  # regenerate digests after bumping the pin
set -euo pipefail

repo=nixbuild/nix-quick-install-action
sums="${BASH_SOURCE[0]%/*}/nix-archives.sha256"

update() {
  local tag="${1:?usage: $0 update <tag>}" digests
  digests="$(curl -fsS "https://api.github.com/repos/$repo/releases/tags/$tag" \
    | jq -r '.assets[] | select(.digest) | "\(.digest | ltrimstr("sha256:"))  \(.name)"' \
    | sort -k2)"
  if [[ -z "$digests" ]]; then
    echo "$tag publishes no asset digests" >&2
    exit 1
  fi
  printf '%s\n' \
    "# SHA-256 of nix-quick-install-action Nix archives; see fetch-nix.sh." \
    "# release: $tag" \
    "$digests" > "$sums"
}

platform() {
  local arch os
  arch="$(uname -m)"
  case "$OSTYPE" in darwin*) os=darwin ;; *) os=linux ;; esac
  echo "${arch/arm64/aarch64}-$os"
}

fetch() {
  : "${NIX_VERSION:?}" "${RUNNER_TEMP:?}" "${GITHUB_OUTPUT:?}"
  local release name digest dir
  release="$(sed -n 's/^# release: //p' "$sums")"
  name="nix-$NIX_VERSION-$(platform).tar.zstd"
  digest="${NIX_SHA256:-$(awk -v n="$name" '$2 == n { print $1 }' "$sums")}"
  if [[ -z "$digest" ]]; then
    echo "::error::$release ships no $name; set nix-sha256"
    exit 1
  fi

  dir="$RUNNER_TEMP/nix-archives"
  mkdir -p "$dir"
  curl -fsSL --retry 3 --proto '=https' --proto-redir '=https' \
    -o "$dir/$name" "https://github.com/$repo/releases/download/$release/$name"
  (cd "$dir" && shasum -a 256 -c - <<<"$digest  $name")
  echo "archives-url=file://$dir" >> "$GITHUB_OUTPUT"
}

case "${1:-}" in
  update) update "${2:-}" ;;
  *) fetch ;;
esac
