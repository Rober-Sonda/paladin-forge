# AgentForge Orchestrator

Motor central de AgentForge para resolver delegación, composición de prompts y ejecución de pipelines.

## Comandos
- `agentforge init <project_path>`
- `agentforge compose-agent --agent <name> --subagent <name> [--skill <skill> ...]`
- `agentforge run <project_path> [--dry-run] [--from <stage>] [--to <stage>]`
- `agentforge vscode-link <project_path>`
- `agentforge-console --project <project_path>`

## Flujo recomendado (proyecto real)
1. Inicializar pipeline del proyecto:
   - `agentforge init /ruta/proyecto`
2. Editar `/ruta/proyecto/.agent-team.json`:
   - configurar stages y comandos (`flutter pub get`, `flutter analyze`, `flutter test`, deploy, etc.)
3. Probar pipeline sin ejecutar comandos:
   - `agentforge run /ruta/proyecto --dry-run`
4. Ejecutar pipeline real:
   - `agentforge run /ruta/proyecto`

## Ejemplo de stages con comandos
Dentro de `.agent-team.json`:
- plan: sin comandos (solo composición de prompt)
- implement: comandos de build/cambio
- validate: `flutter analyze` + `flutter test`
- deploy: `azd up` / `firebase deploy` / `kubectl apply ...`

## Integración VS Code (opcional)
- `agentforge vscode-link /ruta/proyecto`
Esto crea tasks para correr pipeline desde VS Code.

## Privacidad
- Todo vive en `~/.rcsonda-devteam` y `~/.local/bin`
- Ignorado global de Git en `~/.config/git/ignore`
- No contamina repos a menos que vos ejecutes `vscode-link` o `init` dentro de un proyecto.
