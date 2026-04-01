#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE="${AGENTFORGE_HOME:-$(cd "$SCRIPT_DIR/.." && pwd)}"
PROMPTS_DIR="$BASE/prompts"
SKILLS_DIR="$BASE/skills"
PROFILES_DIR="$BASE/profiles"

usage() {
  cat <<USAGE
Uso:
  agent-run.sh --prompt <prompt-name> [--profile <profile-name>] [--skill <skill-name> ...]
  agent-run.sh --profile <profile-name> [--skill <skill-name> ...]

Ejemplos:
  agent-run.sh --prompt migrator --skill flutter-design-system
  agent-run.sh --profile flutter-migration --skill lint-rules --skill tests-min

Salida:
  Imprime un prompt compuesto (prompt base + profile + skills) listo para pegar en tu agente.
USAGE
}

PROMPT_NAME=""
PROFILE_NAME=""
SKILLS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prompt)
      PROMPT_NAME="${2:-}"
      shift 2
      ;;
    --profile)
      PROFILE_NAME="${2:-}"
      shift 2
      ;;
    --skill)
      SKILLS+=("${2:-}")
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Argumento desconocido: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -n "$PROFILE_NAME" ]]; then
  PROFILE_FILE="$PROFILES_DIR/${PROFILE_NAME}.profile"
  [[ -f "$PROFILE_FILE" ]] || { echo "No existe profile: $PROFILE_FILE" >&2; exit 1; }

  while IFS='=' read -r key value; do
    key="$(echo "$key" | xargs)"
    value="$(echo "$value" | xargs)"
    [[ -z "$key" ]] && continue
    [[ "$key" =~ ^# ]] && continue

    if [[ "$key" == "prompt" && -z "$PROMPT_NAME" ]]; then
      value="${value#prompts/}"
      value="${value%.md}"
      PROMPT_NAME="$value"
    fi

    if [[ "$key" == "skills" && -n "$value" ]]; then
      IFS=',' read -r -a profile_skills <<< "$value"
      for s in "${profile_skills[@]}"; do
        s="$(echo "$s" | xargs)"
        [[ -n "$s" ]] && SKILLS+=("$s")
      done
    fi
  done < "$PROFILE_FILE"
fi

[[ -n "$PROMPT_NAME" ]] || { echo "Debes indicar --prompt o un --profile con prompt." >&2; exit 1; }

PROMPT_FILE="$PROMPTS_DIR/${PROMPT_NAME}.md"
[[ -f "$PROMPT_FILE" ]] || { echo "No existe prompt: $PROMPT_FILE" >&2; exit 1; }

declare -A seen
unique_skills=()
for s in "${SKILLS[@]}"; do
  s="$(echo "$s" | xargs)"
  [[ -z "$s" ]] && continue
  if [[ -z "${seen[$s]+x}" ]]; then
    seen[$s]=1
    unique_skills+=("$s")
  fi
done

echo "# ===== AGENT PROMPT COMPOSED ====="
echo "# generated: $(date '+%Y-%m-%d %H:%M:%S')"
echo "# prompt: $PROMPT_NAME"
if [[ -n "$PROFILE_NAME" ]]; then
  echo "# profile: $PROFILE_NAME"
fi
if [[ ${#unique_skills[@]} -gt 0 ]]; then
  echo "# skills: ${unique_skills[*]}"
else
  echo "# skills: (none)"
fi
echo

echo "## BASE PROMPT"
cat "$PROMPT_FILE"

for s in "${unique_skills[@]}"; do
  SKILL_FILE="$SKILLS_DIR/${s}.md"
  [[ -f "$SKILL_FILE" ]] || { echo "No existe skill: $SKILL_FILE" >&2; exit 1; }
  echo
  echo "## SKILL: $s"
  cat "$SKILL_FILE"
done
