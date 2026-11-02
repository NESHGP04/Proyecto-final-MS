# Propagación de Fake News

**Proyecto Final de Modelación y Simulación · Universidad del Valle de Guatemala · Grupo 4**

Camila Richter (23183) · Marinés García (23391) · Juan Francisco Martínez (23617) · Ernesto Asencio (23009)

Estudiamos cómo se propaga una noticia falsa en una red social y qué intervenciones la frenan mejor. La difusión se modela como un contagio con cuatro estados (**S**usceptible, **E**xpuesto, **D**ifusor —I—, **R**emovido), el modelo **SEIR-D**, en dos versiones que se validan entre sí:

1. **Ecuaciones diferenciales (ODE)** de mezcla homogénea: da el número reproductivo R0, el umbral y el tamaño final del brote.
2. **Simulación basada en agentes (ABM)** sobre redes complejas (Erdős–Rényi, Barabási–Albert y Watts–Strogatz) con Monte Carlo (30 réplicas por escenario), para evaluar a qué usuarios intervenir.

Sobre el ABM se comparan tres estrategias —**fact-checking**, **silenciamiento de cuentas** y **prebunking**— según el momento, la intensidad y el criterio de selección (al azar o por mayor grado).

> **Entregables:** informe en `docs/Informe_Grupo4_FakeNews.docx` (secciones fuente en [`docs/informe_final/`](docs/informe_final/)) · video: **(pendiente: enlace al video)** · guion en [`docs/video_guion.md`](docs/video_guion.md).

## Qué encontramos

Resultados con N = 5000 nodos, grado medio 10, 240 horas y 30 réplicas (parámetros ilustrativos, **no calibrados con datos reales**; detalle e intervalos de confianza en el informe, sección 6):

| Pregunta | Resultado |
|---|---|
| ¿Importa la topología? | Sí, en la **velocidad**: con hubs (BA) el pico de difusores es ≈ 0.077 y llega a la hora ≈ 36; en ER es ≈ 0.040 y llega a la hora ≈ 70. El alcance final es casi igual (≈ 0.57). |
| ¿Importa el momento de actuar? | Mucho. En BA, un fact-checking de intensidad media (δ = 0.2) desde el inicio reduce el alcance ≈ 76 %; a las 24 h, ≈ 43 %; a las 48 h, ≈ 12 %. |
| ¿A quién intervenir? | A los usuarios de **mayor grado**. En BA, silenciar al 5 % de mayor grado reduce el alcance ≈ 62 %; al 5 % al azar, ≈ 9 %. Con prebunking, ≈ 80 % desde el inicio (por grado) frente a ≈ 43 % a las 12 h. |
| ¿Importa el origen? | Sí: sembrar desde hubs adelanta (hora ≈ 19 contra ≈ 36 en BA) e intensifica el pico. |

**Hipótesis:** H1 parcial · H2 confirmada (aumento) y parcial (no linealidad) · H3 parcial · H4 confirmada · H5 confirmada. Dos resultados contradijeron lo que esperábamos y se reportan como tales (informe, sección 7.2).

**Validación:** el ODE reproduce la fórmula analítica del tamaño final; el ABM reproduce al ODE en el límite de campo medio; el umbral de propagación sigue el orden que predice la teoría (BA < ER < WS); con 30 réplicas el alcance se estima con una precisión cercana al 2 %.

## Instalación

Requiere Python 3.9 o superior.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
pytest
```

## Cómo reproducir los resultados

Todo es reproducible: las corridas usan semillas fijas (`SEED0 = 2026`; la réplica r usa `SEED0 + r`).

| Qué | Comando | Produce |
|---|---|---|
| Experimentos E1, E3–E7 (topología, fact-checking, silenciamiento, prebunking, origen, estrategias) | `python -m fakenews.experiments --exp all --figures` | `results/E*_*.csv`, `figures/fig_E*.png` |
| E2 (sensibilidad de parámetros) | `python -m fakenews.sensitivity` | `results/E2_*.csv`, `figures/fig_E2_*.png` |
| V1–V3 (validaciones) | `python -c "from fakenews.validation import run_validation; run_validation()"` | `results/V1_*`, `V2_*`, `V3_*`, `figures/fig_V*.png` |
| V4 (convergencia Monte Carlo) | `python -m fakenews.convergence` | `results/V4_*.csv`, `figures/fig_V4_*.png` |
| Dashboard | `streamlit run app/dashboard.py` | aplicación en `http://localhost:8501` |
| Informe (.docx) | `pip install python-docx && python scripts/build_informe.py` | `docs/Informe_Grupo4_FakeNews.docx` |

Cada experimento escribe `<EXP>_metrics.csv` (una fila por réplica) y `<EXP>_curves.csv` (curvas agregadas con media y percentiles 2.5 y 97.5). Las opciones `--quick` usan redes y réplicas pequeñas para depurar y no sobrescriben los resultados finales. Con N = 5000, E2, V3 y V4 tardan alrededor de 30–40 segundos cada uno en un portátil.

## Dashboard

```bash
streamlit run app/dashboard.py
```

Tres pestañas: **Simulador** (ABM + ODE con los controles de la barra lateral; pulsar *Simular*), **Comparar escenarios** (lee `results/`) y **Estructura de la red** (histogramas de grado y dibujo de una red pequeña). Detalles en la sección 4.4 del informe.

## Estructura del repositorio

```
Proyecto-final-MS/
├── src/fakenews/        código: params, metrics, ode_model, networks, abm, interventions,
│                        experiments, figures, sensitivity (E2), validation (V1–V3), convergence (V4)
├── app/                 dashboard (Streamlit)
├── tests/               pruebas automáticas (pytest)
├── results/             CSV de todos los experimentos y validaciones
├── figures/             figuras del informe
├── scripts/             generación del informe (.docx) a partir de results/
└── docs/
    ├── CONTRATO.md      diseño, contrato técnico y reparto del trabajo
    ├── informe_final/   secciones del informe (fuente del .docx)
    ├── informe/         borradores de cada integrante
    ├── prompts/         bitácoras de uso de IA de cada integrante
    └── video_guion.md   guion del video
```

## Ideas clave del diseño

- **Contrato compartido** (`params.py`, `metrics.py`): todos los módulos usan los mismos tipos (`ModelParams`, `Intervention`, `SimResult`) y las mismas seis métricas (pico, hora del pico, alcance, creyentes, hora de extinción, difusores·hora), de modo que los resultados de ODE y ABM son comparables.
- **ABM vectorizado:** el número de vecinos difusores de todos los nodos sale de una sola multiplicación de matriz dispersa por vector; 30 réplicas con N = 5000 tardan ≈ 2 s por topología.
- **Las cifras del informe no se teclean a mano:** `scripts/informe_valores.py` las calcula desde `results/`.

## Limitaciones

Parámetros ilustrativos sin calibrar con datos reales; redes sintéticas y estáticas; todos los usuarios y noticias comparten parámetros; no se modelan algoritmos de recomendación ni la competencia entre una noticia y su desmentido. Los resultados deben leerse como comparaciones entre escenarios, no como predicciones. Ver informe, sección 7.4.

## Uso de IA

Se usó IA generativa (Claude Code) con una bitácora de prompts por integrante en [`docs/prompts/`](docs/prompts/) y una evaluación crítica de cada respuesta; el informe documenta qué funcionó, qué falló y cómo se verificó (sección 5).

## Referencias principales

Vosoughi, Roy y Aral (2018), *Science* · Jin et al. (2013), SNAKDD · Pastor-Satorras y Vespignani (2001), *PRL* · Newman (2002), *PRE* · Barabási y Albert (1999), *Science* · Watts y Strogatz (1998), *Nature*. Lista completa en la sección 8 del informe.
