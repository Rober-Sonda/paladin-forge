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
- indicadores de progreso por pipeline (`done/running/pending/failed`)
- centro de ayuda integrado en consola (Help Center)
- dashboard de tokens y costo estimado por sesión/modelo/agente
- configuración editable de pricing por modelo (`USD por 1M` + ratio output)
- gestor de catálogo para crear/editar agentes y subagentes
- modo de pantalla duplicada para no perder contexto (mirror command deck)
- editor de código en consola para catálogos/configs (`$EDITOR`/`nano`/`vi`)
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

Por defecto abre en **modo chat-first** (sin menú numérico).
- para forzar menú clásico: `agentforge-console --menu --project .`

### 3.1 Funciones avanzadas en consola
- `13` Help center
- `14` Token & cost dashboard
- `15` Model pricing settings
- `16` Agent catalog manager
- `17` Console code editor
- `18` Duplicate screen mode
- `19` Chat assistant (modo conversacional)
- `20` Agent memory manager (skills/comportamientos persistentes)
- `21` Project code workspace (crear/mejorar código en proyecto)

### Modo Chat (nuevo)
Desde la consola, abre `19` y hablá con AgentForge en lenguaje natural.

Ahora también puedes abrir directamente en chat al iniciar el comando:
- `agentforge-console --chat --project .`
- `agentforge-console --project .` (chat-first por defecto)

Comandos útiles en chat:
- `/help`
- `/status`
- `/agents`
- `/run dry`
- `/run real`
- `/compose <stage>`
- `/pricing`
- `/catalog`
- `/memory`
- `/code` o `/code <ruta/archivo>`
- `/mcp`
- `/mcp connect <servicio>`
- `/mcp disconnect <servicio>`
- `/mirror on|off`
- `/project <path>`
- `/menu` o `/exit`

En cada tarea del chat se muestra la delegación activa (`Chat delegation`) con agente/subagente/modelo para que se vea qué está ejecutando AgentForge en tiempo real.

### Memoria por agente
Cada agente y subagente tiene memoria persistente para:
- `skills_memory`
- `behaviors`
- `notes`

Esa memoria se inyecta automáticamente al componer prompts y ejecutar pipeline.

### Desarrollo de código desde la herramienta
Con `21` (o `/code`) puedes:
- editar archivos existentes del proyecto
- crear archivos nuevos desde cero
- agregar snippets rápidos
- generar un scaffold inicial básico

También puedes pedirlo en lenguaje natural:
- `editar "lib/feature/new_screen.dart"`
- `abrir pubspec.yaml`

### Servicios MCP desde chat
Sin salir del chat puedes gestionar conexiones a servicios externos tipo MCP:
- ver estado: `/mcp`
- conectar: `/mcp connect <name>`
- desconectar: `/mcp disconnect <name>`

Configura servicios en `config/mcp_services.json` (se genera automáticamente al primer uso).

## Console walkthrough (capturas)

### Dashboard principal + telemetría + mirror mode
![AgentForge Dashboard](docs/screenshots/01-dashboard.svg)

### Help center (guía operativa)
![AgentForge Help Center](docs/screenshots/02-help-center.svg)

### Token & cost dashboard
![AgentForge Token Cost](docs/screenshots/03-token-cost.svg)

## Demo rápida (60s)
- Guion y pasos: [docs/demo/DEMO_60S.md](docs/demo/DEMO_60S.md)
- Script automático de sesión: `scripts/run_demo_60s.sh`
- Generador automático de GIF: `scripts/make_demo_gif.sh`
- Guía GIF: [docs/demo/GIF_GUIDE.md](docs/demo/GIF_GUIDE.md)
- Pack de publicación (X/LinkedIn): [docs/demo/SOCIAL_KIT.md](docs/demo/SOCIAL_KIT.md)

### Preview GIF
![AgentForge Console Demo GIF](docs/demo/console-demo-60s.gif)

Ejecutar demo automática:
- `chmod +x scripts/run_demo_60s.sh`
- `./scripts/run_demo_60s.sh`

Generar GIF de demo:
- `chmod +x scripts/make_demo_gif.sh`
- `./scripts/make_demo_gif.sh`

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

## Observabilidad y costos
- Los costos son estimados en base a prompts compuestos.
- Tokens estimados con aproximación por longitud de texto.
- Para costos reales, configura tus tarifas en consola (opción `15`).

## UX de consola (elegante y práctica)
- Indicadores de estado en todo momento para evitar pérdida de contexto.
- Mirror mode para pantallas duplicadas cuando necesitas comparar secciones.
- Edición directa en terminal de archivos clave como en un flujo tipo editor.

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
