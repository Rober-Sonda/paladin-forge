#!/usr/bin/env bash
set -euo pipefail

PROJECT_PATH="${1:-/tmp/agentforge-demo}"
TXT_OUT="${2:-$(pwd)/docs/demo/console-demo-60s.txt}"
GIF_OUT="${3:-$(pwd)/docs/demo/console-demo-60s.gif}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -f "$ROOT_DIR/scripts/run_demo_60s.sh" ]]; then
  echo "ERROR: run_demo_60s.sh no encontrado"
  exit 1
fi

if [[ ! -f "$TXT_OUT" ]]; then
  "$ROOT_DIR/scripts/run_demo_60s.sh" "$PROJECT_PATH" "$TXT_OUT"
fi

python3 - "$TXT_OUT" "$GIF_OUT" <<'PY'
import re
import sys
from pathlib import Path

TXT_PATH = Path(sys.argv[1])
GIF_PATH = Path(sys.argv[2])

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    print("Pillow no encontrado. Instalando en usuario...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "Pillow"])
    from PIL import Image, ImageDraw, ImageFont

ansi_re = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
raw = TXT_PATH.read_text(encoding="utf-8", errors="ignore")
clean = ansi_re.sub("", raw).replace("\r", "")
lines = [ln.rstrip("\n") for ln in clean.splitlines()]

if not lines:
    raise SystemExit("No hay contenido para renderizar")

# Cortes por pantallas/secciones
break_points = [0]
for i, ln in enumerate(lines):
    if "AgentForge" in ln and i - break_points[-1] > 18:
        break_points.append(i)
    if "◆ Option:" in ln and i - break_points[-1] > 18:
        break_points.append(i)

break_points = sorted(set(break_points))
segments = []
for idx, start in enumerate(break_points):
    end = break_points[idx + 1] if idx + 1 < len(break_points) else len(lines)
    chunk = lines[start:end]
    if len(chunk) >= 8:
        segments.append(chunk[:60])

if not segments:
    segments = [lines[:60]]

# Config visual
W, H = 1400, 900
PAD_X, PAD_Y = 24, 24
BG = (11, 16, 32)
PANEL = (16, 24, 48)
TEXT = (222, 238, 255)
ACCENT = (124, 77, 255)
MUTED = (139, 163, 199)

font = ImageFont.load_default()
line_h = 14
max_chars = 180

frames = []
for seg in segments:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    d.rounded_rectangle((16, 16, W - 16, 84), radius=12, fill=PANEL, outline=ACCENT, width=2)
    d.text((32, 30), "AgentForge Console Demo", fill=TEXT, font=font)
    d.text((32, 52), "Auto-generated preview from terminal session", fill=MUTED, font=font)

    d.rounded_rectangle((16, 100, W - 16, H - 16), radius=12, fill=PANEL, outline=(77, 163, 255), width=2)

    y = 120
    for ln in seg:
        content = (ln[:max_chars]) if len(ln) > max_chars else ln
        if not content.strip():
            y += line_h
            continue
        color = TEXT
        if "FAIL" in content:
            color = (255, 132, 132)
        elif "OK" in content or "Pipeline finalizado" in content:
            color = (118, 255, 170)
        elif "INFO" in content:
            color = (125, 211, 252)
        elif "◆ Option:" in content:
            color = (255, 214, 102)
        d.text((PAD_X + 8, y), content, fill=color, font=font)
        y += line_h
        if y > H - 40:
            break

    frames.append(img)

# Duraciones: intro/pasos/outro
durations = []
for idx in range(len(frames)):
    if idx == 0:
        durations.append(900)
    elif idx == len(frames) - 1:
        durations.append(1100)
    else:
        durations.append(550)

GIF_PATH.parent.mkdir(parents=True, exist_ok=True)
frames[0].save(
    GIF_PATH,
    save_all=True,
    append_images=frames[1:],
    duration=durations,
    loop=0,
    optimize=True,
)

print(f"GIF generado: {GIF_PATH}")
print(f"Frames: {len(frames)}")
PY

echo "Done. GIF listo en: $GIF_OUT"
