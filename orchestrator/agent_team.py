#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(os.environ.get("AGENTFORGE_HOME", Path(__file__).resolve().parents[1])).expanduser().resolve()
RUNNER = BASE / "scripts" / "agent-run.sh"
CATALOG_FILE = BASE / "orchestrator" / "agent_catalog.json"
TEMPLATES_DIR = BASE / "orchestrator" / "templates"
CONFIG_FILE = ".agent-team.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def compose_prompt(prompt_name: str, skills: list[str]):
    if not RUNNER.exists():
        raise FileNotFoundError(f"No existe runner: {RUNNER}")
    cmd = [str(RUNNER), "--prompt", prompt_name]
    for skill in skills:
        cmd += ["--skill", skill]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or res.stdout.strip())
    return res.stdout


def dedup(seq):
    out, seen = [], set()
    for x in seq:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def resolve_agent(catalog: dict, agent: str, subagent: str | None):
    if agent not in catalog:
        raise KeyError(f"Agente no existe: {agent}")
    a = catalog[agent]
    prompt = a.get("prompt", "migrator")
    base_model = a.get("model", "gpt-5.3-codex")
    skills = list(a.get("skills", []))

    chosen_sub = None
    sub_model = None
    if subagent:
      s = a.get("subagents", {}).get(subagent)
      if s is None:
        raise KeyError(f"Subagente no existe: {agent}/{subagent}")
      chosen_sub = subagent
      sub_model = s.get("model", base_model)
      skills.extend(s.get("skills", []))

    model = sub_model or base_model
    return {
        "agent": agent,
        "subagent": chosen_sub,
        "prompt": prompt,
        "model": model,
        "skills": dedup(skills)
    }


def cmd_list_agents(_args):
    catalog = load_json(CATALOG_FILE)
    print("Agentes disponibles:\n")
    for aname, aval in catalog.items():
        print(f"- {aname} (model: {aval.get('model','n/a')}, prompt: {aval.get('prompt','migrator')})")
        subs = aval.get("subagents", {})
        for sname, sval in subs.items():
            print(f"  - {aname}/{sname} (model: {sval.get('model', aval.get('model'))})")
    return 0


def cmd_init(args):
    project = Path(args.project).expanduser().resolve()
    project.mkdir(parents=True, exist_ok=True)
    config_path = project / CONFIG_FILE
    if config_path.exists() and not args.force:
        print(f"Ya existe {config_path}. Usá --force.")
        return 1

    template_name = args.template or "standard"
    template_file = TEMPLATES_DIR / f"{template_name}.json"
    if not template_file.exists():
        raise FileNotFoundError(f"Template no existe: {template_file}")

    data = load_json(template_file)
    save_json(config_path, data)
    print(f"Creado: {config_path} (template={template_name})")
    return 0


def cmd_compose_agent(args):
    catalog = load_json(CATALOG_FILE)
    meta = resolve_agent(catalog, args.agent, args.subagent)

    extra_skills = args.skill or []
    skills = dedup(meta["skills"] + extra_skills)
    composed = compose_prompt(meta["prompt"], skills)

    header = [
        "# ===== AGENT SUBTEAM PROMPT =====",
        f"# agent: {meta['agent']}",
        f"# subagent: {meta['subagent'] or '(none)'}",
        f"# model: {meta['model']}",
        f"# prompt: {meta['prompt']}",
        f"# skills: {' '.join(skills) if skills else '(none)'}",
        ""
    ]
    out = "\n".join(header) + composed

    if args.out:
        Path(args.out).expanduser().write_text(out, encoding="utf-8")
        print(f"Prompt guardado en: {args.out}")
    else:
        print(out)
    return 0


def cmd_run(args):
    project = Path(args.project).expanduser().resolve()
    config_path = project / CONFIG_FILE
    if not config_path.exists():
        raise FileNotFoundError(f"No existe {config_path}. Ejecutá: agentforge init {project}")

    config = load_json(config_path)
    catalog = load_json(CATALOG_FILE)
    pipeline = [p for p in config.get("pipeline", []) if p.get("enabled", True)]

    if args.from_stage or args.to_stage:
        names = [p["stage"] for p in pipeline]
        i = names.index(args.from_stage) if args.from_stage else 0
        j = names.index(args.to_stage) if args.to_stage else len(names)-1
        if i > j:
            raise ValueError("--from no puede estar después de --to")
        pipeline = pipeline[i:j+1]

    logs_dir = BASE / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    print(f"Proyecto: {project}")
    print(f"Config: {config_path}")

    for step in pipeline:
        stage = step.get("stage", "unknown")
        agent = step.get("agent", "migrator")
        subagent = step.get("subagent")
        commands = step.get("commands", [])

        meta = resolve_agent(catalog, agent, subagent)
        stage_skills = step.get("skills", [])
        skills = dedup(meta["skills"] + stage_skills)

        print(f"\n=== Stage: {stage} ===")
        print(f"agent/subagent: {agent}/{subagent or '-'} | model: {meta['model']} | skills: {skills}")

        composed = compose_prompt(meta["prompt"], skills)
        prompt_file = logs_dir / f"{ts}-{stage}.prompt.md"
        prompt_file.write_text(
            "\n".join([
                "# ===== STAGE PROMPT =====",
                f"# stage: {stage}",
                f"# agent: {agent}",
                f"# subagent: {subagent or '(none)'}",
                f"# model: {meta['model']}",
                f"# prompt: {meta['prompt']}",
                f"# skills: {' '.join(skills) if skills else '(none)'}",
                "",
            ]) + composed,
            encoding="utf-8"
        )
        print(f"Prompt stage guardado: {prompt_file}")

        for cmd in commands:
            print(f"$ {cmd}")
            if args.dry_run:
                continue
            rc = subprocess.run(cmd, shell=True, cwd=str(project)).returncode
            if rc != 0:
                print(f"ERROR: comando falló en stage {stage} (rc={rc})")
                return rc

    print("\nPipeline finalizado.")
    return 0


def cmd_vscode_link(args):
    project = Path(args.project).expanduser().resolve()
    vscode_dir = project / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    tasks_path = vscode_dir / "tasks.json"

    if tasks_path.exists() and not args.force:
        print(f"Ya existe {tasks_path}. Usá --force para sobrescribir.")
        return 1

    tasks = {
        "version": "2.0.0",
        "tasks": [
            {
                "label": "AgentForge: Init (full-delivery)",
                "type": "shell",
                "command": "agentforge init . --template full-delivery"
            },
            {
                "label": "AgentForge: Dry Run Pipeline",
                "type": "shell",
                "command": "agentforge run . --dry-run"
            },
            {
                "label": "AgentForge: Run Full Pipeline",
                "type": "shell",
                "command": "agentforge run ."
            },
            {
                "label": "AgentForge: List Agents",
                "type": "shell",
                "command": "agentforge list-agents"
            }
        ]
    }

    save_json(tasks_path, tasks)
    print(f"Creado: {tasks_path}")
    print("Nota: esto sí modifica el proyecto (opcional).")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="agentforge", description="Orquestador local de team dev con subagentes/modelos")
    sub = p.add_subparsers(dest="cmd", required=True)

    s_list = sub.add_parser("list-agents", help="Lista agentes/subagentes y modelos")
    s_list.set_defaults(func=cmd_list_agents)

    s_init = sub.add_parser("init", help="Inicializa .agent-team.json")
    s_init.add_argument("project")
    s_init.add_argument("--template", default="standard", choices=["standard", "full-delivery"])
    s_init.add_argument("--force", action="store_true")
    s_init.set_defaults(func=cmd_init)

    s_comp = sub.add_parser("compose-agent", help="Compone prompt por agente/subagente")
    s_comp.add_argument("--agent", required=True)
    s_comp.add_argument("--subagent")
    s_comp.add_argument("--skill", action="append")
    s_comp.add_argument("--out")
    s_comp.set_defaults(func=cmd_compose_agent)

    s_run = sub.add_parser("run", help="Ejecuta pipeline")
    s_run.add_argument("project")
    s_run.add_argument("--from", dest="from_stage")
    s_run.add_argument("--to", dest="to_stage")
    s_run.add_argument("--dry-run", action="store_true")
    s_run.set_defaults(func=cmd_run)

    s_vs = sub.add_parser("vscode-link", help="Crea tasks VS Code para el team")
    s_vs.add_argument("project")
    s_vs.add_argument("--force", action="store_true")
    s_vs.set_defaults(func=cmd_vscode_link)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        sys.exit(args.func(args))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
