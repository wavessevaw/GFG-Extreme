#!/usr/bin/env bash
# Bounded, read-only connectivity probe for SteamOS recovery and source hosts.
# It requests at most a 2 KiB range from directory/index URLs; it never fetches
# or mounts an OS image.
set -uo pipefail

printf 'utc='; date -u '+%Y-%m-%dT%H:%M:%SZ'
curl --version | head -n 1

probe() {
  local url="$1" output rc
  printf '\nURL=%s\n' "$url"
  output="$(curl --location --max-time 20 --range 0-2047 --silent --show-error \
    --output /dev/null --write-out 'http_code=%{http_code} bytes=%{size_download} effective_url=%{url_effective}\n' \
    "$url" 2>&1)"
  rc=$?
  printf '%s\n' "$output"
  printf 'curl_exit=%s\n' "$rc"
}

probe 'https://steamdeck-images.steamos.cloud/recovery/'
probe 'https://help.steampowered.com/ru/faqs/view/65B4-2AA3-5F37-4227'
probe 'https://steamdeck-packages.steamos.cloud/archlinux-mirror/jupiter/'
probe 'https://steamdeck-packages.steamos.cloud/archlinux-mirror/holo/'
probe 'https://gitlab.steamos.cloud/'
