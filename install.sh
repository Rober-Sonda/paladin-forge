#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$HOME/.local/bin"
install -m 0755 "$ROOT_DIR/bin/agentforge" "$HOME/.local/bin/agentforge"
install -m 0755 "$ROOT_DIR/bin/agentforge-console" "$HOME/.local/bin/agentforge-console"
echo "Installed: $HOME/.local/bin/agentforge"
echo "Installed: $HOME/.local/bin/agentforge-console"
echo "Add $HOME/.local/bin to PATH if needed."
