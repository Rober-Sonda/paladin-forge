#!/usr/bin/env bash
set -euo pipefail
name="${1:-}"
if [[ -z "$name" ]]; then
  echo "Uso: new-skill.sh <skill-name>"
  exit 1
fi
out="$HOME/.rcsonda-devteam/skills/${name}.md"
cp "$HOME/.rcsonda-devteam/templates/skill-template.md" "$out"
echo "Creada: $out"
