#!/usr/bin/env python3
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(os.environ.get("AGENTFORGE_HOME", Path(__file__).resolve().parents[1])).expanduser().resolve()
ORCH = BASE / "orchestrator" / "agent_team.py"
CATALOG = BASE / "orchestrator" / "agent_catalog.json"
RUNNER = BASE / "scripts" / "agent-run.sh"
CONFIG = ".agent-team.json"
MODEL_PRICING_FILE = BASE / "config" / "model_pricing.json"
APP_NAME = "AgentForge"
APP_SUBTITLE = "Epic multi-agent terminal cockpit"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


class ANSI:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_RED = "\033[41m"
    BG_BRIGHT_BLACK = "\033[100m"


STATUS_STYLES = {
    "idle": ("○", ANSI.BRIGHT_BLACK),
    "pending": ("◌", ANSI.BRIGHT_BLACK),
    "running": ("◉", ANSI.BRIGHT_CYAN),
    "done": ("✓", ANSI.BRIGHT_GREEN),
    "failed": ("✖", ANSI.BRIGHT_RED),
    "skipped": ("↷", ANSI.BRIGHT_YELLOW),
}

MENU_ITEMS = [
    ("1", "Set project path", "Change current workspace target"),
    ("2", "Init project config", "Generate full-delivery pipeline"),
    ("3", "List agents/subagents/models", "Inspect the full roster"),
    ("4", "Reassign stage agent/subagent", "Delegate each stage precisely"),
    ("5", "Manage stage skills", "Tune role capabilities"),
    ("6", "Compose prompt for stage", "Preview delegated prompt"),
    ("7", "Run pipeline (dry-run)", "Simulate the full mission"),
    ("8", "Run pipeline (real)", "Execute the active mission"),
    ("9", "Git dashboard", "Review branch and pending changes"),
    ("10", "View git diff", "Inspect current diff"),
    ("11", "Preview edited code", "Quick file-focused diff view"),
    ("12", "Link VS Code tasks", "Create optional project tasks"),
    ("13", "Help center", "Guided usage and troubleshooting"),
    ("14", "Token & cost dashboard", "Model usage, cost and estimates"),
    ("15", "Model pricing settings", "Configure USD/token estimations"),
    ("16", "Agent catalog manager", "Create and customize team agents"),
    ("0", "Exit", "Leave the cockpit"),
]


def run(cmd, cwd=None, capture=False):
    if capture:
        p = subprocess.run(cmd, shell=True, cwd=cwd, text=True, capture_output=True)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    return subprocess.run(cmd, shell=True, cwd=cwd).returncode


def compose_prompt(prompt_name, skills):
    cmd = [str(RUNNER), "--prompt", prompt_name]
    for skill in skills:
        cmd += ["--skill", skill]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or res.stdout.strip())
    return res.stdout


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def estimate_tokens(text):
    normalized = str(text or "")
    return max(1, (len(normalized) + 3) // 4)


def ensure_model_pricing(catalog):
    if MODEL_PRICING_FILE.exists():
        pricing = load_json(MODEL_PRICING_FILE)
    else:
        pricing = {"models": {}}

    pricing.setdefault("models", {})
    for _, meta in catalog.items():
        model = meta.get("model", "gpt-5.3-codex")
        pricing["models"].setdefault(
            model,
            {
                "input_per_million_usd": 0.0,
                "output_per_million_usd": 0.0,
                "output_ratio": 0.35,
            },
        )
        for _, submeta in meta.get("subagents", {}).items():
            submodel = submeta.get("model", model)
            pricing["models"].setdefault(
                submodel,
                {
                    "input_per_million_usd": 0.0,
                    "output_per_million_usd": 0.0,
                    "output_ratio": 0.35,
                },
            )
    save_json(MODEL_PRICING_FILE, pricing)
    return pricing


def get_model_pricing(model, pricing):
    return pricing.get("models", {}).get(
        model,
        {
            "input_per_million_usd": 0.0,
            "output_per_million_usd": 0.0,
            "output_ratio": 0.35,
        },
    )


def compute_cost_usd(model, input_tokens, output_tokens, pricing):
    model_pricing = get_model_pricing(model, pricing)
    in_rate = float(model_pricing.get("input_per_million_usd", 0.0))
    out_rate = float(model_pricing.get("output_per_million_usd", 0.0))
    return (input_tokens / 1_000_000.0) * in_rate + (output_tokens / 1_000_000.0) * out_rate


def track_usage(state, *, model, agent, subagent, input_tokens, output_tokens, cost_usd):
    usage = state["usage"]
    usage["session_input_tokens"] += input_tokens
    usage["session_output_tokens"] += output_tokens
    usage["session_cost_usd"] += cost_usd

    model_bucket = usage["by_model"].setdefault(
        model,
        {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0},
    )
    model_bucket["input_tokens"] += input_tokens
    model_bucket["output_tokens"] += output_tokens
    model_bucket["cost_usd"] += cost_usd

    agent_key = f"{agent}/{subagent or '-'}"
    agent_bucket = usage["by_agent"].setdefault(
        agent_key,
        {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "model": model},
    )
    agent_bucket["input_tokens"] += input_tokens
    agent_bucket["output_tokens"] += output_tokens
    agent_bucket["cost_usd"] += cost_usd


def dedup(seq):
    out = []
    seen = set()
    for item in seq:
        if item and item not in seen:
            out.append(item)
            seen.add(item)
    return out


def resolve_agent(catalog, agent, subagent=None):
    if agent not in catalog:
        raise KeyError(f"Agente no existe: {agent}")
    meta = catalog[agent]
    prompt = meta.get("prompt", "migrator")
    base_model = meta.get("model", "gpt-5.3-codex")
    skills = list(meta.get("skills", []))
    chosen_sub = None
    sub_model = None

    if subagent:
        sub_meta = meta.get("subagents", {}).get(subagent)
        if sub_meta is None:
            raise KeyError(f"Subagente no existe: {agent}/{subagent}")
        chosen_sub = subagent
        sub_model = sub_meta.get("model", base_model)
        skills.extend(sub_meta.get("skills", []))

    return {
        "agent": agent,
        "subagent": chosen_sub,
        "prompt": prompt,
        "model": sub_model or base_model,
        "skills": dedup(skills),
    }


def term_width():
    return max(96, shutil.get_terminal_size((120, 32)).columns)


def clear_screen():
    print("\033[2J\033[H", end="")


def style(text, *codes):
    return "".join(codes) + str(text) + ANSI.RESET


def pill(text, fg=ANSI.WHITE, bg=ANSI.BG_BRIGHT_BLACK):
    return f"{bg}{fg}{ANSI.BOLD} {text} {ANSI.RESET}"


def divider(char="═", color=ANSI.BRIGHT_BLUE):
    print(style(char * term_width(), color))


def visible_len(text):
    return len(ANSI_RE.sub("", str(text)))


def fit_visible(text, width):
    raw = str(text)
    clean = ANSI_RE.sub("", raw)
    if len(clean) <= width:
        return raw + (" " * (width - len(clean)))
    truncated = clean[: max(0, width - 1)] + "…"
    return truncated


def wrap_pills(items, width):
    if not items:
        return []
    lines = []
    current = []
    current_len = 0
    for item in items:
        item_len = visible_len(item)
        sep = 1 if current else 0
        if current and current_len + sep + item_len > width:
            lines.append(" ".join(current))
            current = [item]
            current_len = item_len
        else:
            current.append(item)
            current_len += sep + item_len
    if current:
        lines.append(" ".join(current))
    return lines


def box(title, lines, accent=ANSI.BRIGHT_CYAN):
    width = term_width()
    content_width = max(40, width - 4)
    top = style("╔" + "═" * (content_width + 2) + "╗", accent)
    mid = style("║", accent)
    bottom = style("╚" + "═" * (content_width + 2) + "╝", accent)

    print(top)
    title_text = f" {title} "
    print(f"{mid} {style(title_text.ljust(content_width), ANSI.BOLD, ANSI.WHITE)} {mid}")
    print(f"{mid} {style('─' * content_width, ANSI.BRIGHT_BLACK)} {mid}")
    for line in lines:
        print(f"{mid} {fit_visible(line, content_width)} {mid}")
    print(bottom)


def input_default(prompt, default=""):
    value = input(f"{style('➜', ANSI.BRIGHT_MAGENTA, ANSI.BOLD)} {prompt} [{default}]: ").strip()
    return value or default


def build_state(project):
    return {
        "project": str(Path(project).expanduser().resolve()),
        "pipeline": [],
        "active_stage": None,
        "active_agent": None,
        "last_action": "Console ready",
        "last_prompt": None,
        "usage": {
            "session_input_tokens": 0,
            "session_output_tokens": 0,
            "session_cost_usd": 0.0,
            "by_model": {},
            "by_agent": {},
        },
    }


def ensure_project_config(project):
    cfg = Path(project) / CONFIG
    if not cfg.exists():
        print(style(f"No existe {cfg}. Ejecutando init full-delivery...", ANSI.BRIGHT_YELLOW))
        rc = run(f'python3 "{ORCH}" init "{project}" --template full-delivery')
        if rc != 0:
            raise RuntimeError("No se pudo inicializar .agent-team.json")
    return cfg


def sync_pipeline_state(state, preserve_status=False):
    cfg = Path(state["project"]) / CONFIG
    if not cfg.exists():
        state["pipeline"] = []
        return

    existing = {item["stage"]: item for item in state.get("pipeline", [])} if preserve_status else {}
    catalog = load_json(CATALOG)
    pipeline = []
    for step in load_json(cfg).get("pipeline", []):
        meta = resolve_agent(catalog, step.get("agent", "migrator"), step.get("subagent"))
        previous = existing.get(step.get("stage"), {})
        pipeline.append(
            {
                "stage": step.get("stage", "unknown"),
                "agent": step.get("agent", "migrator"),
                "subagent": step.get("subagent") or "-",
                "model": meta["model"],
                "enabled": step.get("enabled", True),
                "status": previous.get("status", "pending" if step.get("enabled", True) else "skipped"),
            }
        )
    state["pipeline"] = pipeline


def render_header(state, subtitle=None):
    width = term_width()
    divider("═", ANSI.BRIGHT_MAGENTA)
    title = f" {APP_NAME} ".center(width)
    print(style(title, ANSI.BOLD, ANSI.BRIGHT_WHITE))
    print(style(APP_SUBTITLE.center(width), ANSI.BRIGHT_CYAN))
    project_line = f"Project · {state['project']}"
    if subtitle:
        project_line += f"   |   {subtitle}"
    print(style(project_line.center(width), ANSI.BRIGHT_BLACK))
    divider("═", ANSI.BRIGHT_MAGENTA)


def render_footer(state):
    if state.get("pipeline"):
        chips = []
        for item in state["pipeline"]:
            symbol, color = STATUS_STYLES.get(item.get("status", "idle"), STATUS_STYLES["idle"])
            label = f"{symbol} {item['stage']}·{item['agent']}/{item['subagent']}"
            bg = ANSI.BG_CYAN if item.get("status") == "running" else ANSI.BG_BRIGHT_BLACK
            fg = ANSI.BLACK if item.get("status") == "running" else color
            chips.append(pill(label, fg=fg, bg=bg))
        chips_lines = wrap_pills(chips, term_width() - 8)
    else:
        chips_lines = [pill("No pipeline loaded", fg=ANSI.BRIGHT_BLACK)]

    lines = [
        f"{style('Delegation Bus', ANSI.BOLD, ANSI.BRIGHT_CYAN)}",
        *chips_lines,
        f"{style('Last action', ANSI.BOLD, ANSI.BRIGHT_MAGENTA)} · {state.get('last_action', '-')}",
    ]
    if state.get("active_agent"):
        lines.append(f"{style('Active handoff', ANSI.BOLD, ANSI.BRIGHT_YELLOW)} · {state['active_agent']}")
    if state.get("last_prompt"):
        lines.append(f"{style('Latest prompt', ANSI.BOLD, ANSI.BRIGHT_GREEN)} · {state['last_prompt']}")
    done = len([item for item in state.get("pipeline", []) if item.get("status") == "done"])
    running = len([item for item in state.get("pipeline", []) if item.get("status") == "running"])
    failed = len([item for item in state.get("pipeline", []) if item.get("status") == "failed"])
    pending = len([item for item in state.get("pipeline", []) if item.get("status") == "pending"])
    lines.append(
        f"{style('Pipeline status', ANSI.BOLD, ANSI.BRIGHT_WHITE)} · done={done} running={running} pending={pending} failed={failed}"
    )
    usage = state.get("usage", {})
    lines.append(
        f"{style('Token usage', ANSI.BOLD, ANSI.BRIGHT_WHITE)} · in={usage.get('session_input_tokens', 0)} out={usage.get('session_output_tokens', 0)} cost≈${usage.get('session_cost_usd', 0.0):.6f}"
    )
    box("Mission Telemetry", lines, accent=ANSI.BRIGHT_BLUE)


def render_menu(state):
    clear_screen()
    sync_pipeline_state(state, preserve_status=True)
    render_header(state, subtitle="community-ready console")
    menu_lines = []
    for key, label, desc in MENU_ITEMS:
        menu_lines.append(
            f"{style(key.rjust(2), ANSI.BOLD, ANSI.BRIGHT_YELLOW)}  {style(label, ANSI.BRIGHT_WHITE)}  {style('· ' + desc, ANSI.BRIGHT_BLACK)}"
        )
    box("Command Deck", menu_lines, accent=ANSI.BRIGHT_MAGENTA)
    render_footer(state)


def print_notice(message, level="info"):
    colors = {
        "info": ANSI.BRIGHT_CYAN,
        "success": ANSI.BRIGHT_GREEN,
        "warn": ANSI.BRIGHT_YELLOW,
        "error": ANSI.BRIGHT_RED,
    }
    tag = {
        "info": "INFO",
        "success": "OK",
        "warn": "WARN",
        "error": "FAIL",
    }[level]
    print(f"{pill(tag, fg=ANSI.BLACK if level != 'error' else ANSI.WHITE, bg={
        'info': ANSI.BG_CYAN,
        'success': ANSI.BG_GREEN,
        'warn': ANSI.BG_YELLOW,
        'error': ANSI.BG_RED,
    }[level])} {style(message, colors[level])}")


def show_git_dashboard(project, state):
    clear_screen()
    render_header(state, subtitle="git dashboard")
    if run("git rev-parse --is-inside-work-tree >/dev/null 2>&1", cwd=project) != 0:
        print_notice("No es un repo git.", "warn")
        return

    rc, out, _ = run("git status --short", cwd=project, capture=True)
    rc, branch, _ = run("git branch --show-current", cwd=project, capture=True)
    lines = [
        f"Branch · {branch or '(detached)'}",
        "",
        style("Cambios locales:", ANSI.BOLD, ANSI.BRIGHT_WHITE),
    ]
    lines.extend((out or "(sin cambios)").splitlines())

    rc, upstream, _ = run("git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null", cwd=project, capture=True)
    if rc == 0 and upstream:
        rc, ahead_behind, _ = run("git rev-list --left-right --count @{u}...HEAD", cwd=project, capture=True)
        if ahead_behind:
            behind, ahead = ahead_behind.split()
            lines.extend([
                "",
                f"Upstream · {upstream}",
                f"Ahead/Behind · {ahead}/{behind}",
            ])
            if int(ahead) > 0:
                rc, commits, _ = run("git --no-pager log --oneline @{u}..HEAD", cwd=project, capture=True)
                lines.extend(["", style("Commits para push:", ANSI.BOLD, ANSI.BRIGHT_WHITE)])
                lines.extend((commits or "(none)").splitlines())
    else:
        lines.extend(["", "Upstream · no configurado"])

    box("Git Command Center", lines, accent=ANSI.BRIGHT_GREEN)


def show_diff(project, state):
    clear_screen()
    render_header(state, subtitle="diff viewer")
    if run("git rev-parse --is-inside-work-tree >/dev/null 2>&1", cwd=project) != 0:
        print_notice("No es un repo git.", "warn")
        return

    rc, files, _ = run("git diff --name-only", cwd=project, capture=True)
    changed = [f for f in files.splitlines() if f.strip()]
    if not changed:
        print_notice("No hay archivos modificados.", "warn")
        return

    lines = [f"{i}. {f}" for i, f in enumerate(changed, 1)]
    box("Files with changes", lines, accent=ANSI.BRIGHT_YELLOW)
    sel = input_default("Elegí número de archivo (0 para diff completo)", "0")
    if sel == "0":
        run("git --no-pager diff", cwd=project)
        return
    try:
        idx = int(sel) - 1
        if idx < 0 or idx >= len(changed):
            raise ValueError
    except ValueError:
        print_notice("Selección inválida", "error")
        return
    run(f'git --no-pager diff -- "{changed[idx]}"', cwd=project)


def edit_stage_skills(project, state):
    clear_screen()
    render_header(state, subtitle="stage skills manager")
    cfg_path = ensure_project_config(project)
    cfg = load_json(cfg_path)
    stages = cfg.get("pipeline", [])
    if not stages:
        print_notice("Pipeline vacío", "warn")
        return

    lines = []
    for i, step in enumerate(stages, 1):
        skills = step.get("skills", [])
        lines.append(f"{i}. {step.get('stage')} | {step.get('agent')}/{step.get('subagent','-')} | skills={skills}")
    box("Current stage skills", lines, accent=ANSI.BRIGHT_CYAN)

    sel = input_default("Elegí stage", "1")
    try:
        idx = int(sel) - 1
        stage = stages[idx]
    except Exception:
        print_notice("Selección inválida", "error")
        return

    print(style(f"Skills actuales: {stage.get('skills', [])}", ANSI.BRIGHT_WHITE))
    action = input_default("Acción: add/remove/replace", "add")
    values = input(f"{style('➜', ANSI.BRIGHT_MAGENTA, ANSI.BOLD)} Ingresá skills separadas por coma: ").strip()
    new_skills = [value.strip() for value in values.split(",") if value.strip()]
    current = stage.get("skills", [])

    if action == "add":
        stage["skills"] = dedup(current + new_skills)
    elif action == "remove":
        stage["skills"] = [item for item in current if item not in set(new_skills)]
    elif action == "replace":
        stage["skills"] = new_skills
    else:
        print_notice("Acción inválida", "error")
        return

    save_json(cfg_path, cfg)
    state["last_action"] = f"Skills updated for stage {stage.get('stage')}"
    sync_pipeline_state(state, preserve_status=True)
    print_notice("Skills actualizadas.", "success")


def reassign_stage_agent(project, state):
    clear_screen()
    render_header(state, subtitle="stage delegation manager")
    cfg_path = ensure_project_config(project)
    cfg = load_json(cfg_path)
    cat = load_json(CATALOG)
    stages = cfg.get("pipeline", [])

    lines = [f"{i}. {step.get('stage')} -> {step.get('agent')}/{step.get('subagent','-')}" for i, step in enumerate(stages, 1)]
    box("Current delegation map", lines, accent=ANSI.BRIGHT_MAGENTA)

    sel = input_default("Elegí stage", "1")
    try:
        stage = stages[int(sel) - 1]
    except Exception:
        print_notice("Selección inválida", "error")
        return

    box("Available agents", [f"- {name}" for name in cat.keys()], accent=ANSI.BRIGHT_GREEN)
    agent = input(f"{style('➜', ANSI.BRIGHT_MAGENTA, ANSI.BOLD)} Nuevo agente: ").strip()
    if agent not in cat:
        print_notice("Agente inválido", "error")
        return

    subs = cat[agent].get("subagents", {})
    box("Available subagents", [f"- {name}" for name in subs.keys()] or ["- (none)"], accent=ANSI.BRIGHT_CYAN)
    sub = input_default("Nuevo subagente", next(iter(subs.keys()), ""))
    if sub and sub not in subs:
        print_notice("Subagente inválido", "error")
        return

    stage["agent"] = agent
    stage["subagent"] = sub
    save_json(cfg_path, cfg)
    state["last_action"] = f"Delegated {stage.get('stage')} -> {agent}/{sub or '-'}"
    state["active_agent"] = f"{stage.get('stage')} → {agent}/{sub or '-'}"
    sync_pipeline_state(state, preserve_status=True)
    print_notice("Stage actualizado.", "success")


def compose_subagent_prompt(project, state):
    clear_screen()
    render_header(state, subtitle="compose delegated prompt")
    cfg_path = ensure_project_config(project)
    cfg = load_json(cfg_path)

    lines = []
    for i, step in enumerate(cfg.get("pipeline", []), 1):
        lines.append(f"{i}. {step.get('stage')} -> {step.get('agent')}/{step.get('subagent','-')} | skills={step.get('skills', [])}")
    box("Pipeline prompt map", lines, accent=ANSI.BRIGHT_BLUE)

    sel = input_default("Elegí stage", "1")
    try:
        step = cfg["pipeline"][int(sel) - 1]
    except Exception:
        print_notice("Selección inválida", "error")
        return

    catalog = load_json(CATALOG)
    pricing = ensure_model_pricing(catalog)
    meta = resolve_agent(catalog, step["agent"], step.get("subagent"))
    skills = dedup(meta["skills"] + step.get("skills", []))
    out = BASE / "logs" / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{step['stage']}-manual.prompt.md"
    composed = compose_prompt(meta["prompt"], skills)
    header = [
        "# ===== AGENT SUBTEAM PROMPT =====",
        f"# agent: {meta['agent']}",
        f"# subagent: {meta['subagent'] or '(none)'}",
        f"# model: {meta['model']}",
        f"# prompt: {meta['prompt']}",
        f"# skills: {' '.join(skills) if skills else '(none)'}",
        "",
    ]
    out.write_text("\n".join(header) + composed, encoding="utf-8")
    input_tokens = estimate_tokens(composed)
    output_ratio = float(get_model_pricing(meta["model"], pricing).get("output_ratio", 0.35))
    output_tokens = max(1, int(input_tokens * output_ratio))
    cost_usd = compute_cost_usd(meta["model"], input_tokens, output_tokens, pricing)
    track_usage(
        state,
        model=meta["model"],
        agent=meta["agent"],
        subagent=meta["subagent"],
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
    )
    state["last_prompt"] = str(out)
    state["last_action"] = f"Prompt composed for {step['stage']}"
    state["active_agent"] = f"{step['stage']} → {meta['agent']}/{meta['subagent'] or '-'}"
    print_notice(f"Prompt guardado en: {out}", "success")


def run_pipeline(project, state, dry_run=False):
    cfg_path = ensure_project_config(project)
    config = load_json(cfg_path)
    catalog = load_json(CATALOG)
    pricing = ensure_model_pricing(catalog)
    pipeline = [step for step in config.get("pipeline", []) if step.get("enabled", True)]
    if not pipeline:
        print_notice("No hay stages habilitados.", "warn")
        return

    sync_pipeline_state(state, preserve_status=False)
    logs_dir = BASE / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    state["last_action"] = f"Pipeline {'dry-run' if dry_run else 'real'} started"

    for item in state["pipeline"]:
        item["status"] = "pending" if item.get("enabled", True) else "skipped"

    for step in pipeline:
        stage = step.get("stage", "unknown")
        agent = step.get("agent", "migrator")
        subagent = step.get("subagent")
        commands = step.get("commands", [])
        meta = resolve_agent(catalog, agent, subagent)
        skills = dedup(meta["skills"] + step.get("skills", []))

        for item in state["pipeline"]:
            if item["stage"] == stage:
                item["status"] = "running"
        state["active_stage"] = stage
        state["active_agent"] = f"{stage} → {agent}/{subagent or '-'} | {meta['model']}"
        clear_screen()
        render_header(state, subtitle=f"executing stage: {stage}")
        box(
            "Live Stage Delegation",
            [
                f"Stage · {stage}",
                f"Agent · {agent}",
                f"Subagent · {subagent or '-'}",
                f"Model · {meta['model']}",
                f"Prompt · {meta['prompt']}",
                f"Skills · {', '.join(skills) if skills else '(none)'}",
                f"Mode · {'dry-run' if dry_run else 'real execution'}",
            ],
            accent=ANSI.BRIGHT_CYAN,
        )
        render_footer(state)

        composed = compose_prompt(meta["prompt"], skills)
        prompt_file = logs_dir / f"{ts}-{stage}.prompt.md"
        prompt_file.write_text(
            "\n".join(
                [
                    "# ===== STAGE PROMPT =====",
                    f"# stage: {stage}",
                    f"# agent: {agent}",
                    f"# subagent: {subagent or '(none)'}",
                    f"# model: {meta['model']}",
                    f"# prompt: {meta['prompt']}",
                    f"# skills: {' '.join(skills) if skills else '(none)'}",
                    "",
                ]
            ) + composed,
            encoding="utf-8",
        )
        state["last_prompt"] = str(prompt_file)
        input_tokens = estimate_tokens(composed)
        output_ratio = float(get_model_pricing(meta["model"], pricing).get("output_ratio", 0.35))
        output_tokens = max(1, int(input_tokens * output_ratio))
        cost_usd = compute_cost_usd(meta["model"], input_tokens, output_tokens, pricing)
        track_usage(
            state,
            model=meta["model"],
            agent=agent,
            subagent=subagent,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )
        print_notice(f"Prompt stage guardado: {prompt_file}", "success")
        print_notice(f"Estimated tokens in/out: {input_tokens}/{output_tokens} | cost≈${cost_usd:.6f}", "info")

        for command in commands:
            print(style(f"$ {command}", ANSI.BRIGHT_YELLOW))
            if dry_run:
                continue
            rc = subprocess.run(command, shell=True, cwd=str(project)).returncode
            if rc != 0:
                for item in state["pipeline"]:
                    if item["stage"] == stage:
                        item["status"] = "failed"
                state["last_action"] = f"Pipeline failed at {stage} (rc={rc})"
                clear_screen()
                render_header(state, subtitle="pipeline failed")
                render_footer(state)
                print_notice(f"ERROR: comando falló en stage {stage} (rc={rc})", "error")
                return

        for item in state["pipeline"]:
            if item["stage"] == stage:
                item["status"] = "done"
        state["last_action"] = f"Stage completed: {stage}"

    state["active_stage"] = None
    state["active_agent"] = None
    state["last_action"] = f"Pipeline {'dry-run' if dry_run else 'real'} finished"
    clear_screen()
    render_header(state, subtitle="pipeline complete")
    box("Mission Result", [style("Pipeline finalizado con éxito.", ANSI.BOLD, ANSI.BRIGHT_GREEN)], accent=ANSI.BRIGHT_GREEN)
    render_footer(state)


def vscode_link(project, state):
    clear_screen()
    render_header(state, subtitle="vscode integration")
    rc = run(f'python3 "{ORCH}" vscode-link "{project}"')
    if rc == 0:
        state["last_action"] = "VS Code tasks linked"
        print_notice("Tasks creadas o actualizadas.", "success")


def list_agents(state):
    clear_screen()
    render_header(state, subtitle="agent roster")
    catalog = load_json(CATALOG)
    lines = []
    for agent_name, agent_meta in catalog.items():
        lines.append(style(f"- {agent_name}", ANSI.BOLD, ANSI.BRIGHT_WHITE) + f" | model={agent_meta.get('model', 'n/a')} | prompt={agent_meta.get('prompt', 'migrator')}")
        for sub_name, sub_meta in agent_meta.get("subagents", {}).items():
            lines.append(f"    ↳ {sub_name} | model={sub_meta.get('model', agent_meta.get('model', 'n/a'))}")
    box("Team Roster", lines, accent=ANSI.BRIGHT_MAGENTA)


def show_help_center(state):
    clear_screen()
    render_header(state, subtitle="help center")
    lines = [
        style("Quick workflow", ANSI.BOLD, ANSI.BRIGHT_WHITE),
        "1) Init config -> option 2",
        "2) Reassign stage agents -> option 4",
        "3) Tune skills -> option 5",
        "4) Dry-run pipeline -> option 7",
        "5) Real execution -> option 8",
        "",
        style("Telemetry indicators", ANSI.BOLD, ANSI.BRIGHT_WHITE),
        "◌ pending | ◉ running | ✓ done | ↷ skipped | ✖ failed",
        "Delegation Bus shows current stage ownership in real time.",
        "Token usage and estimated costs are session-based in footer/dashboard.",
        "",
        style("Troubleshooting", ANSI.BOLD, ANSI.BRIGHT_WHITE),
        "- If stage fails: check command output and fix project command/tooling.",
        "- If cost stays 0: set model prices in option 15.",
        "- If agent missing: create/update it in option 16.",
    ]
    box("Operator Guide", lines, accent=ANSI.BRIGHT_GREEN)


def show_token_cost_dashboard(state):
    clear_screen()
    render_header(state, subtitle="token and cost dashboard")
    usage = state.get("usage", {})
    catalog = load_json(CATALOG)
    pricing = ensure_model_pricing(catalog)

    summary = [
        f"Session input tokens · {usage.get('session_input_tokens', 0)}",
        f"Session output tokens · {usage.get('session_output_tokens', 0)}",
        f"Estimated session cost (USD) · ${usage.get('session_cost_usd', 0.0):.6f}",
        "",
        style("Cost model", ANSI.BOLD, ANSI.BRIGHT_WHITE) + " · estimates based on composed prompts",
    ]
    box("Session totals", summary, accent=ANSI.BRIGHT_CYAN)

    model_lines = []
    for model, data in sorted(usage.get("by_model", {}).items()):
        p = get_model_pricing(model, pricing)
        model_lines.append(
            f"{model} | in={data['input_tokens']} out={data['output_tokens']} cost≈${data['cost_usd']:.6f} | rates in/out=${p.get('input_per_million_usd', 0.0)}/{p.get('output_per_million_usd', 0.0)} per 1M"
        )
    if not model_lines:
        model_lines = ["No model usage in this session yet."]
    box("Usage by model", model_lines, accent=ANSI.BRIGHT_MAGENTA)

    agent_lines = []
    for agent_key, data in sorted(usage.get("by_agent", {}).items()):
        agent_lines.append(
            f"{agent_key} | model={data.get('model', 'n/a')} | in={data['input_tokens']} out={data['output_tokens']} cost≈${data['cost_usd']:.6f}"
        )
    if not agent_lines:
        agent_lines = ["No agent usage in this session yet."]
    box("Usage by agent", agent_lines, accent=ANSI.BRIGHT_YELLOW)


def manage_model_pricing(state):
    clear_screen()
    render_header(state, subtitle="model pricing settings")
    catalog = load_json(CATALOG)
    pricing = ensure_model_pricing(catalog)
    models = sorted(pricing.get("models", {}).keys())
    if not models:
        print_notice("No hay modelos detectados aún.", "warn")
        return

    lines = []
    for i, model in enumerate(models, 1):
        data = pricing["models"][model]
        lines.append(
            f"{i}. {model} | input_per_1M=${float(data.get('input_per_million_usd', 0.0)):.4f} | output_per_1M=${float(data.get('output_per_million_usd', 0.0)):.4f} | output_ratio={float(data.get('output_ratio', 0.35)):.2f}"
        )
    box("Editable model rates", lines, accent=ANSI.BRIGHT_BLUE)

    sel = input_default("Elegí modelo por número", "1")
    try:
        model = models[int(sel) - 1]
    except Exception:
        print_notice("Selección inválida", "error")
        return

    cfg = pricing["models"][model]
    in_rate = input_default("Input USD por 1M tokens", str(cfg.get("input_per_million_usd", 0.0)))
    out_rate = input_default("Output USD por 1M tokens", str(cfg.get("output_per_million_usd", 0.0)))
    out_ratio = input_default("Output ratio estimado (0..2)", str(cfg.get("output_ratio", 0.35)))
    try:
        cfg["input_per_million_usd"] = float(in_rate)
        cfg["output_per_million_usd"] = float(out_rate)
        cfg["output_ratio"] = max(0.0, min(2.0, float(out_ratio)))
    except ValueError:
        print_notice("Valores inválidos", "error")
        return

    save_json(MODEL_PRICING_FILE, pricing)
    state["last_action"] = f"Pricing updated for model {model}"
    print_notice("Pricing guardado.", "success")


def manage_agent_catalog(state):
    catalog = load_json(CATALOG)
    while True:
        clear_screen()
        render_header(state, subtitle="agent catalog manager")
        lines = [
            "1) Create new agent",
            "2) Edit existing agent",
            "3) Add or update subagent",
            "4) Remove subagent",
            "5) Remove agent",
            "6) Back",
            "",
            style("Current agents", ANSI.BOLD, ANSI.BRIGHT_WHITE),
        ]
        lines.extend([f"- {name}" for name in sorted(catalog.keys())] or ["- (none)"])
        box("Catalog operations", lines, accent=ANSI.BRIGHT_CYAN)

        choice = input_default("Choose action", "6")
        if choice == "1":
            agent = input(f"{style('➜', ANSI.BRIGHT_MAGENTA, ANSI.BOLD)} Agent name: ").strip()
            if not agent:
                print_notice("Nombre inválido", "error")
                wait_for_enter()
                continue
            if agent in catalog:
                print_notice("Ese agente ya existe", "warn")
                wait_for_enter()
                continue
            model = input_default("Default model", "gpt-5.3-codex")
            prompt = input_default("Prompt base", "migrator")
            skills = input_default("Skills (coma separada)", "")
            catalog[agent] = {
                "model": model,
                "prompt": prompt,
                "skills": [s.strip() for s in skills.split(",") if s.strip()],
                "subagents": {},
            }
            save_json(CATALOG, catalog)
            ensure_model_pricing(catalog)
            state["last_action"] = f"Agent created: {agent}"
            print_notice("Agente creado.", "success")
            wait_for_enter()
        elif choice == "2":
            agent = input(f"{style('➜', ANSI.BRIGHT_MAGENTA, ANSI.BOLD)} Agent to edit: ").strip()
            if agent not in catalog:
                print_notice("Agente no existe", "error")
                wait_for_enter()
                continue
            entry = catalog[agent]
            entry["model"] = input_default("Model", entry.get("model", "gpt-5.3-codex"))
            entry["prompt"] = input_default("Prompt", entry.get("prompt", "migrator"))
            current_skills = ",".join(entry.get("skills", []))
            skills = input_default("Skills (coma separada)", current_skills)
            entry["skills"] = [s.strip() for s in skills.split(",") if s.strip()]
            save_json(CATALOG, catalog)
            ensure_model_pricing(catalog)
            state["last_action"] = f"Agent updated: {agent}"
            print_notice("Agente actualizado.", "success")
            wait_for_enter()
        elif choice == "3":
            agent = input(f"{style('➜', ANSI.BRIGHT_MAGENTA, ANSI.BOLD)} Parent agent: ").strip()
            if agent not in catalog:
                print_notice("Agente no existe", "error")
                wait_for_enter()
                continue
            sub = input(f"{style('➜', ANSI.BRIGHT_MAGENTA, ANSI.BOLD)} Subagent name: ").strip()
            if not sub:
                print_notice("Nombre inválido", "error")
                wait_for_enter()
                continue
            subs = catalog[agent].setdefault("subagents", {})
            current = subs.get(sub, {})
            model = input_default("Model", current.get("model", catalog[agent].get("model", "gpt-5.3-codex")))
            skills = input_default("Skills (coma separada)", ",".join(current.get("skills", [])))
            subs[sub] = {"model": model, "skills": [s.strip() for s in skills.split(",") if s.strip()]}
            save_json(CATALOG, catalog)
            ensure_model_pricing(catalog)
            state["last_action"] = f"Subagent upsert: {agent}/{sub}"
            print_notice("Subagente guardado.", "success")
            wait_for_enter()
        elif choice == "4":
            agent = input(f"{style('➜', ANSI.BRIGHT_MAGENTA, ANSI.BOLD)} Parent agent: ").strip()
            sub = input(f"{style('➜', ANSI.BRIGHT_MAGENTA, ANSI.BOLD)} Subagent to remove: ").strip()
            if agent in catalog and sub in catalog.get(agent, {}).get("subagents", {}):
                del catalog[agent]["subagents"][sub]
                save_json(CATALOG, catalog)
                state["last_action"] = f"Subagent removed: {agent}/{sub}"
                print_notice("Subagente eliminado.", "success")
            else:
                print_notice("No existe ese subagente", "error")
            wait_for_enter()
        elif choice == "5":
            agent = input(f"{style('➜', ANSI.BRIGHT_MAGENTA, ANSI.BOLD)} Agent to remove: ").strip()
            if agent in catalog:
                del catalog[agent]
                save_json(CATALOG, catalog)
                state["last_action"] = f"Agent removed: {agent}"
                print_notice("Agente eliminado.", "success")
            else:
                print_notice("No existe ese agente", "error")
            wait_for_enter()
        elif choice == "6":
            break
        else:
            print_notice("Opción inválida", "error")
            wait_for_enter()


def open_file_preview(project, state):
    clear_screen()
    render_header(state, subtitle="code preview")
    rc, files, _ = run("git diff --name-only", cwd=project, capture=True)
    changed = [f for f in files.splitlines() if f.strip()]
    if not changed:
        print_notice("No hay archivos cambiados.", "warn")
        return
    box("Changed files", [f"{i}. {f}" for i, f in enumerate(changed, 1)], accent=ANSI.BRIGHT_BLUE)
    sel = input_default("Elegí archivo", "1")
    try:
        path = changed[int(sel) - 1]
    except Exception:
        print_notice("Selección inválida", "error")
        return
    run(f'git --no-pager diff -- "{path}" | sed -n "1,220p"', cwd=project)


def wait_for_enter():
    input(f"\n{style('Presioná Enter para continuar...', ANSI.DIM, ANSI.BRIGHT_WHITE)}")


def main_menu(project):
    state = build_state(project)
    sync_pipeline_state(state)
    while True:
        render_menu(state)
        option = input(f"\n{style('◆', ANSI.BRIGHT_CYAN, ANSI.BOLD)} Option: ").strip()
        if option == "1":
            p = input(f"{style('➜', ANSI.BRIGHT_MAGENTA, ANSI.BOLD)} Project path: ").strip()
            if p:
                state["project"] = str(Path(p).expanduser().resolve())
                sync_pipeline_state(state)
                state["last_action"] = f"Project changed to {state['project']}"
        elif option == "2":
            rc = run(f'python3 "{ORCH}" init "{state["project"]}" --template full-delivery --force')
            if rc == 0:
                sync_pipeline_state(state)
                state["last_action"] = "Project config initialized"
                print_notice("Pipeline full-delivery inicializado.", "success")
            wait_for_enter()
        elif option == "3":
            list_agents(state)
            wait_for_enter()
        elif option == "4":
            reassign_stage_agent(state["project"], state)
            wait_for_enter()
        elif option == "5":
            edit_stage_skills(state["project"], state)
            wait_for_enter()
        elif option == "6":
            compose_subagent_prompt(state["project"], state)
            wait_for_enter()
        elif option == "7":
            run_pipeline(state["project"], state, dry_run=True)
            wait_for_enter()
        elif option == "8":
            run_pipeline(state["project"], state, dry_run=False)
            wait_for_enter()
        elif option == "9":
            show_git_dashboard(state["project"], state)
            wait_for_enter()
        elif option == "10":
            show_diff(state["project"], state)
            wait_for_enter()
        elif option == "11":
            open_file_preview(state["project"], state)
            wait_for_enter()
        elif option == "12":
            vscode_link(state["project"], state)
            wait_for_enter()
        elif option == "13":
            show_help_center(state)
            wait_for_enter()
        elif option == "14":
            show_token_cost_dashboard(state)
            wait_for_enter()
        elif option == "15":
            manage_model_pricing(state)
            wait_for_enter()
        elif option == "16":
            manage_agent_catalog(state)
            sync_pipeline_state(state, preserve_status=True)
        elif option == "0":
            clear_screen()
            print(style(f"{APP_NAME} signing off. Bye.", ANSI.BOLD, ANSI.BRIGHT_MAGENTA))
            return
        else:
            print_notice("Opción inválida", "error")
            wait_for_enter()


def main():
    project = str(Path.cwd())
    if len(sys.argv) > 1 and sys.argv[1] == "--project":
        if len(sys.argv) < 3:
            print("Uso: agentforge-console --project /ruta/proyecto")
            sys.exit(1)
        project = str(Path(sys.argv[2]).expanduser().resolve())
    main_menu(project)


if __name__ == "__main__":
    main()
