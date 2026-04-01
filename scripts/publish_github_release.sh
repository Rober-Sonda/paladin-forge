#!/usr/bin/env bash
set -euo pipefail

REPO="Rober-Sonda/paladin-forge"
TAG="v0.1.0"
TITLE="AgentForge v0.1.0 — Initial public release"
DESC="Epic multi-agent terminal cockpit for prompt composition, stage delegation, and local delivery pipelines."
TOPICS=(
  agent-orchestration
  terminal-ui
  developer-tools
  ai-agents
  prompt-engineering
  cli
  productivity
  automation
  pipeline
)

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh no está instalado."
  exit 1
fi

if ! gh auth status -h github.com >/dev/null 2>&1; then
  echo "ERROR: gh no autenticado. Ejecuta: gh auth login -h github.com -w"
  exit 1
fi

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

args=(repo edit "$REPO" --description "$DESC")
for topic in "${TOPICS[@]}"; do
  args+=(--add-topic "$topic")
done

gh "${args[@]}"

if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
  gh release edit "$TAG" --repo "$REPO" --title "$TITLE" --notes-file CHANGELOG.md
else
  gh release create "$TAG" --repo "$REPO" --title "$TITLE" --notes-file CHANGELOG.md
fi

echo "DONE: metadata + release configurados en $REPO"
