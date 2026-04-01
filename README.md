# AgentForge

Epic multi-agent terminal cockpit para coordinar planning, implementación, validación, documentación y release desde una consola visual.

AgentForge combina:
- catálogo de agentes y subagentes
- composición de prompts por skills
- pipelines por stage
- consola ANSI con telemetría de delegación
- utilidades para diff, git y tareas de VS Code

## Highlights
- UI de terminal con paneles y colores
- barra inferior `Delegation Bus` con estado por agente
- `Active handoff` para ver la delegación viva durante el pipeline
- prompts versionables por rol y skills
- instalación simple sin dependencias externas pesadas

## Quick start

### 1. Instalar comandos
Desde la raíz del repo:

- `chmod +x install.sh bin/agentforge bin/agentforge-console`
- `./install.sh`

### 2. Ver catálogo
- `agentforge list-agents`

### 3. Abrir consola
- `agentforge-console --project .`

### 4. Inicializar un proyecto
- `agentforge init . --template full-delivery`

### 5. Probar pipeline
- `agentforge run . --dry-run`

## Estructura
- `bin/`: launchers públicos
- `orchestrator/`: motor del pipeline y consola interactiva
- `prompts/`: prompts base
- `skills/`: capacidades incrementales
- `profiles/`: combinaciones reutilizables
- `scripts/`: utilidades internas
- `templates/`: plantillas de apoyo

## Comandos principales
- `agentforge list-agents`
- `agentforge init <project> --template full-delivery`
- `agentforge compose-agent --agent planner --subagent task-breakdown`
- `agentforge run <project> --dry-run`
- `agentforge vscode-link <project>`
- `agentforge-console --project <project>`

## Casos de uso
- Migraciones Flutter y UI refactors
- Pipelines locales de validación
- Coordinación multi-stage para repos personales
- Demos de delegación de tareas con agentes especializados

## Publicación en GitHub
Este repo ya quedó listo para compartirse:
- licencia MIT
- `CONTRIBUTING.md`
- launchers públicos `agentforge`
- estructura portable sin depender de rutas privadas

## Roadmap sugerido
- temas de color configurables
- export de sesiones a Markdown
- soporte para plantillas de proyecto por stack
- dashboard TUI con navegación por teclas

## Licencia
MIT
