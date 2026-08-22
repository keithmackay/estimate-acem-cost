#!/usr/bin/env bash
# Regenerates the Codex/Gemini CLI port (skills/estimate-acem-cost/) from
# the canonical root files (SKILL.md, acem_calculate.py, references/).
#
# Run this after editing SKILL.md or acem_calculate.py, or after adding/
# changing files under references/. The nested skills/ directory is
# generated output, not a second hand-maintained copy — don't edit it
# directly.
#
# Usage:
#   ./scripts/sync_ports.sh          # regenerate the port
#   ./scripts/sync_ports.sh --check  # exit non-zero if the port has drifted
#                                     # from the canonical files, without
#                                     # changing anything
set -euo pipefail

cd "$(dirname "$0")/.."

SRC_FILES=(SKILL.md acem_calculate.py references)
DEST="skills/estimate-acem-cost"

if [[ "${1:-}" == "--check" ]]; then
  tmp=$(mktemp -d)
  trap 'rm -rf "$tmp"' EXIT
  mkdir -p "$tmp/$DEST"
  for f in "${SRC_FILES[@]}"; do
    cp -r "$f" "$tmp/$DEST/$f"
  done
  if diff -rq "$tmp/$DEST" "$DEST" >/dev/null 2>&1; then
    echo "OK: $DEST is in sync with the canonical root files."
    exit 0
  else
    echo "DRIFT DETECTED: $DEST does not match the canonical root files." >&2
    diff -rq "$tmp/$DEST" "$DEST" >&2 || true
    echo "Run ./scripts/sync_ports.sh (without --check) to fix." >&2
    exit 1
  fi
fi

mkdir -p "$DEST"
for f in "${SRC_FILES[@]}"; do
  rm -rf "${DEST:?}/$f"
  cp -r "$f" "$DEST/$f"
done

echo "Synced ${SRC_FILES[*]} -> $DEST"
