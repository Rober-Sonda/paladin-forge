# GIF Demo Guide

## Generar GIF automático de la demo

```bash
chmod +x scripts/make_demo_gif.sh
./scripts/make_demo_gif.sh
```

Salida por defecto:
- texto demo: `docs/demo/console-demo-60s.txt`
- gif demo: `docs/demo/console-demo-60s.gif`

## Parámetros opcionales

```bash
./scripts/make_demo_gif.sh <project_path> <txt_out> <gif_out>
```

Ejemplo:

```bash
./scripts/make_demo_gif.sh /tmp/agentforge-demo docs/demo/session.txt docs/demo/session.gif
```

## Publicación recomendada
- Usa el GIF en README y en release notes para mostrar flujo real de consola.
- Mantén GIF entre 10 y 30 MB para carga rápida en GitHub.
