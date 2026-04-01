#!/usr/bin/env bash
set -euo pipefail
echo "== PROMPTS =="
ls -1 "$HOME/.rcsonda-devteam/prompts" || true
echo "== SKILLS =="
ls -1 "$HOME/.rcsonda-devteam/skills" || true
echo "== PROFILES =="
ls -1 "$HOME/.rcsonda-devteam/profiles" || true
