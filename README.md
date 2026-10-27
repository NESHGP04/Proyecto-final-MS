# Propagación de Fake News — Proyecto Final de Modelación y Simulación (UVG)

Modelo compartimental **SEIR-D** (ODE) y **simulación basada en agentes** sobre redes complejas
(Erdős–Rényi, Barabási–Albert, Watts–Strogatz) con Monte Carlo, para estudiar cómo la topología, el origen
de la noticia y distintas intervenciones (fact-checking, silenciar hubs/bots, prebunking) afectan el alcance
de una noticia falsa.

**Grupo 4:** Camila Richter (23183) · Marinés García (23391) · Juan Francisco Martínez (23617) · Ernesto Asencio (23009)

> Estado: en desarrollo. El diseño completo y el reparto están en [`docs/CONTRATO.md`](docs/CONTRATO.md).

## Instalación

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
pytest
```

## Estructura

Ver `docs/CONTRATO.md`, sección 4. (La versión final de este README —uso, resultados, cómo reproducir
figuras y dashboard— la completa Marinés en el checkpoint CP4.)
