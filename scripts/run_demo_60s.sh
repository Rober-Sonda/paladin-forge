#!/usr/bin/env bash
set -euo pipefail

PROJECT_PATH="${1:-/tmp/agentforge-demo}"
OUT_FILE="${2:-$(pwd)/docs/demo/console-demo-60s.txt}"

mkdir -p "$(dirname "$OUT_FILE")"

if ! command -v agentforge >/dev/null 2>&1; then
  echo "ERROR: agentforge no está en PATH"
  exit 1
fi

agentforge init "$PROJECT_PATH" --template full-delivery --force >/dev/null

SEQUENCE_FILE="$(mktemp)"
cat > "$SEQUENCE_FILE" <<'EOF'
18

13

14

16
6

17
1

7

0
EOF

if command -v script >/dev/null 2>&1; then
  script -q -c "cat '$SEQUENCE_FILE' | agentforge-console --project '$PROJECT_PATH'" "$OUT_FILE"
else
  cat "$SEQUENCE_FILE" | agentforge-console --project "$PROJECT_PATH" > "$OUT_FILE"
fi

rm -f "$SEQUENCE_FILE"

echo "Demo session generated at: $OUT_FILE"
echo "Tip: comparte este archivo o conviértelo a GIF con tu herramienta favorita."
