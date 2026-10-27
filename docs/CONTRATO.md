# CONTRATO DEL PROYECTO — Grupo 4 · Propagación de Fake News

> Fuente de verdad del proyecto. Todos los módulos se programan contra este contrato para poder
> trabajar **en paralelo**. Si algo de tu tarea contradice este documento, gana este documento.
> Cambios: ver sección 9.

Curso: Modelación y Simulación (UVG) · Equipo: Camila Richter (23183), Marinés García (23391),
Juan Francisco Martínez (23617), Ernesto Asencio (23009).

---

## 1. El proyecto en una página

**Tema:** propagación de noticias falsas (fake news) en redes sociales.

**Problema real:** la desinformación se propaga más rápido y más lejos que la información
verificada (Vosoughi, Roy & Aral, 2018) y afecta salud pública, elecciones y gestión de crisis.
Las plataformas necesitan saber *cuándo* y *a quién* intervenir (verificación de datos, bloqueo
de cuentas/bots, alfabetización mediática) con recursos limitados.
**Aplicación:** moderación de contenido en plataformas, comunicación de salud pública, ciencia
de redes y epidemiología computacional (academia e industria).

**Pregunta de investigación:** ¿cómo influyen la topología de la red, el origen de la noticia y
el tipo/momento de la intervención en el alcance y la velocidad de una noticia falsa, y qué
estrategia reduce más el alcance por nodo intervenido?

**Técnica y justificación (esto se defiende en el documento y la presentación):**

1. La difusión de una noticia es análoga a un contagio: contacto, etapa de decisión (latencia),
   pérdida de interés/escepticismo (recuperación/inmunidad). Por eso usamos un **modelo
   compartimental de la familia SIR** (visto en clase), al que llamamos **SEIR-D** (D = difusión).
   El ODE da una vista determinista, el R0 y el umbral de propagación de forma analítica.
2. La mezcla homogénea del ODE es irreal: las redes sociales son heterogéneas (pocos hubs, muchos
   nodos de grado bajo). En redes con hubs el umbral epidémico puede desaparecer (Pastor-Satorras
   & Vespignani, 2001). Por eso añadimos una **simulación basada en agentes (ABM) sobre redes
   complejas** (Erdős–Rényi, Barabási–Albert, Watts–Strogatz).
3. El ABM es estocástico → usamos **Monte Carlo** (30 réplicas) para intervalos de confianza.
4. Las intervenciones dirigidas (silenciar hubs, prebunking a nodos influyentes) **solo se pueden
   evaluar con topología**; esa es la razón de ser del ABM y justifica no quedarnos con el ODE.
5. ODE vs ABM es nuestra **validación** principal (límite de campo medio, tamaño final analítico,
   contrastes cualitativos con la literatura).

**Hipótesis a poner a prueba (no son resultados; se confirman o se refutan con datos):**

- H1: a igual ⟨k⟩ y parámetros, la red BA (hubs) tiene mayor pico y mayor velocidad que ER y WS.
- H2: cada retraso adicional en el fact-checking aumenta el alcance de forma no lineal.
- H3: silenciar al X % de mayor grado reduce más el alcance que silenciar X % al azar en BA,
  pero no en ER.
- H4: el prebunking dirigido (por grado) es más eficiente que el aleatorio.
- H5: sembrar la noticia desde un hub produce un pico más temprano y alto que sembrarla al azar.

**Honestidad metodológica:** los parámetros por defecto son *ilustrativos* (no calibrados con datos
reales). Lo compensamos con análisis de sensibilidad (E2) y lo declaramos como limitación.
Nada de inventar datos ni citas: toda referencia debe verificarse antes de ponerla.

---

## 2. Requisitos del curso (Proyecto Final, 30 pts)

| Entregable | Pts | Fecha |
|---|---|---|
| Aprobación del tema + entrega parcial en Canvas (descripción del proyecto + captura del correo de aprobación) | 3 | **vie 30 oct** |
| Documento (descripción del problema, análisis, propuesta de solución, descripción de la solución, herramientas aplicadas [incluye prompts de IA, su evolución y comprensión], resultados/métricas, conclusión, bibliografía) | 5 | **lun 2 nov** |
| Repositorio público con TODO el código | 1 | lun 2 nov |
| Video demostrando la solución, implementación y hallazgos | 1 | lun 2 nov |
| Slides (máx. 10) | 5 | lun 2 nov |
| Presentación en clase | 10 | según catedrático |
| Calidad de la solución | 5 | lun 2 nov |

Entrega en Canvas: **PDF del documento + link al repo** y **PDF de la presentación**.
La IA se puede usar, pero hay que usarla de forma **responsable y crítica**: el documento debe incluir
el historial de prompts más relevantes, cuáles funcionaron, cuáles fallaron y por qué, cómo evaluamos
las respuestas y cómo contribuyó la IA. **No se tolera copia**: escribe con tus palabras y entiende
cada línea que subas.

---

## 3. El modelo SEIR-D

### 3.1 Estados y ecuaciones (fracciones de la población, mezcla homogénea)

| Estado | Significado |
|---|---|
| **S** Susceptible | aún no ha visto la noticia |
| **E** Expuesto | vio la noticia y está decidiendo |
| **I** Difusor | cree la noticia y la comparte |
| **R** Removido | escéptico, desmentido, silenciado o sin interés; no difunde |

Unidad de tiempo = **1 hora**. Con `b = beta * <k>` (campo medio) y `delta(t) = delta` si `t >= t_start`, si no 0:

```
dS/dt = -b·S·I + ω·R
dE/dt =  b·S·I - σ·E
dI/dt =  p·σ·E - (γ + delta(t))·I
dR/dt = (1-p)·σ·E + (γ + delta(t))·I - ω·R
dCumExp/dt = b·S·I            (alcance acumulado; empieza en i0)
dCumBel/dt = p·σ·E            (creyentes acumulados; empieza en i0)
```

Condición inicial: `S = 1-i0, E = 0, I = i0, R = 0`. Se conserva S+E+I+R = 1.

Parámetros por defecto (`ModelParams`): `beta=0.03, sigma=0.5, p_believe=0.6, gamma=0.1, omega=0, i0=0.01`
(ilustrativos). Con ⟨k⟩=10: `b=0.3` y **R0 = b·p/γ = 1.8** (sin intervención, ω=0).
(La derivación formal con la matriz de siguiente generación la hace Camila; verificar.)

Intervenciones en el ODE (Camila): `delta` (tasa extra I→R desde t_start); `prebunk_frac` con
`targeting="random"`: en t_start `R += prebunk_frac·S` y `S *= (1-prebunk_frac)`; `silence_frac` con
`targeting="random"`: en t_start cada S, E, I se multiplica por `(1-silence_frac)` y R suma lo quitado.
`targeting="degree"` → `ValueError` (el ODE no ve topología; para eso existe el ABM).

### 3.2 Reglas exactas del ABM (Marinés)

Estados por nodo: `S=0, E=1, I=2, R=3` (int8, constantes en `params.py`). Tiempo discreto, **dt = 1 h,
actualización síncrona** (todas las transiciones de un paso se calculan con el estado al inicio del paso).
Con `q = 1 - exp(-beta·dt)`, `m_v` = número de vecinos en I del nodo v:

| Transición | Probabilidad en el paso |
|---|---|
| S → E | `1 - (1-q)^m_v` |
| E → decide | `1 - exp(-sigma·dt)`; al decidir: → I con prob. `p_believe`, → R en caso contrario |
| I → R | `1 - exp(-(gamma + delta_t)·dt)`, `delta_t = delta` si `t >= t_start` |
| R → S | `1 - exp(-omega·dt)` (solo si omega > 0) |

Semillas: `max(1, round(i0·N))` nodos en I en t=0, elegidos al azar (`seed_strategy="random"`) o los
de mayor grado (`"hub"`), **entre nodos no silenciados**. Intervención en el paso `t == plan.t_start`:
antes de las transiciones, `silence` → R (cualquier estado) e `immunize` → R (solo los que están en S).
Si `t_start = 0`, la intervención se aplica **antes** de elegir las semillas.
Se registra el estado en t = 0, 1, …, t_max (t_max+1 puntos). `cum_exposed` suma S→E (más semillas);
`cum_believers` suma E→I (más semillas). Todo con `np.random.default_rng(seed)`.
Implementar **vectorizado** (matriz de adyacencia `scipy.sparse` × vector de infectados) para que 30
réplicas con N=5000 y 240 pasos corran en segundos.

---

## 4. Arquitectura del repo y contrato técnico

```
Proyecto-final-MS/
├── README.md
├── pyproject.toml · requirements.txt · .gitignore
├── docs/
│   ├── CONTRATO.md                  ← este archivo
│   ├── informe/                     ← secciones del documento (markdown) + refs_<nombre>.md
│   └── prompts/PROMPTS_<nombre>.md  ← bitácora de prompts de cada integrante
├── src/fakenews/
│   ├── params.py      CONTRATO  (ModelParams, Intervention, SimResult, constantes)
│   ├── metrics.py     CONTRATO  (compute_metrics, metrics_table, aggregate_curves)
│   ├── mock.py        datos de prueba (NO usar en resultados finales)
│   ├── ode_model.py   P1 Camila
│   ├── sensitivity.py P1 Camila (E2)
│   ├── validation.py  P1 Camila (V1-V3)
│   ├── networks.py    P2 Marinés
│   ├── abm.py         P2 Marinés
│   ├── interventions.py  P3 Juan Francisco
│   ├── experiments.py    P3 Juan Francisco (E1, E3-E7)
│   └── figures.py        P3 Juan Francisco (figuras de resultados)
├── app/dashboard.py   P4 Ernesto (Streamlit)
├── tests/             cada dueño agrega test_<modulo>.py
├── results/           CSV generados por los experimentos (SE COMMITEAN, son chicos)
├── figures/           PNG finales (dpi 200, etiquetas en español)
└── notebooks/         exploración (opcional)
```

Entorno: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && pip install -e .`
Pruebas: `pytest`. Compatible con **Python 3.9+** (usar `from __future__ import annotations`).

### 4.1 Constantes (en `params.py`)
`SEED0=2026, N_DEFAULT=5000, MEAN_DEGREE=10.0, T_MAX=240, N_REP=30`. No uses números mágicos: impórtalas.

### 4.2 Tipos (en `params.py`) — léelos, ya están implementados
`ModelParams`, `Intervention(name, t_start, delta, silence_frac, prebunk_frac, targeting)`,
`SimResult(t, S, E, I, R, cum_exposed, cum_believers, meta)` + `SimResult.check()`.
Las series son **fracciones de N** con `t = 0..t_max` (paso 1 h). `check()` valida invariantes.

### 4.3 Firmas públicas (los otros módulos dependen de ellas; no las cambies)

```python
# ode_model.py (P1)
simulate_ode(params, intervention=None, mean_degree=MEAN_DEGREE, t_max=T_MAX) -> SimResult
final_size(r0, i0=0.0, p_believe=1.0) -> float
# networks.py (P2)
build_network(kind, n=N_DEFAULT, mean_degree=MEAN_DEGREE, seed=0) -> nx.Graph   # kind: er|ba|ws|complete
degree_stats(G) -> dict(k_mean, k2_mean, k_max)
# abm.py (P2)
simulate_abm(G, params, intervention=None, seed=0, t_max=T_MAX, seed_strategy="random") -> SimResult
run_replicates(kind, params, intervention=None, n=N_DEFAULT, mean_degree=MEAN_DEGREE,
               n_rep=N_REP, seed0=SEED0, t_max=T_MAX, seed_strategy="random") -> list[SimResult]
# interventions.py (P3)
select_nodes(G, frac, targeting, rng) -> np.ndarray
plan(G, intervention, rng) -> InterventionPlan(t_start, silence, immunize, delta)
# experiments.py (P3)
run_experiment(exp_id, quick=False) -> None      # CLI: python -m fakenews.experiments --exp E3
# metrics.py (contrato, ya implementado)
compute_metrics(res) -> dict ; metrics_table(results, **meta) ; aggregate_curves(results, **meta)
```

### 4.4 Acople ABM ↔ intervenciones
El ABM crea `rng`, llama `interventions.plan(G, intervention, rng)` **una vez por corrida** y aplica el
`InterventionPlan` según 3.2. En el Checkpoint 0 `plan()` ya existe en versión mínima (solo `delta`); Juan
Francisco la completa en CP1 (silence/immunize). Marinés puede programar el ABM contra esa versión mínima.

### 4.5 Formato de resultados en disco (lo lee el dashboard y las figuras)

Para cada experimento `<EXP>` (E1…E7, V1…V4) se escriben **dos CSV** en `results/`:

- `<EXP>_metrics.csv` — una fila por réplica: `exp_id, scenario, network, model, [params...], replicate, peak_I, t_peak, reach, believers_total, t_extinct, auc_I`
  (usar `metrics_table(results, exp_id=..., scenario=..., network=..., model="abm"|"ode", **extras)`).
- `<EXP>_curves.csv` — curvas agregadas: `exp_id, scenario, network, model, t, compartment, mean, lo, hi`
  (usar `aggregate_curves(...)`; lo/hi = percentiles 2.5 y 97.5). Para el ODE: `lo = hi = mean`.

`scenario` es un texto corto legible, p. ej. `"sin_intervencion"`, `"factcheck_t12_d0.2"`, `"silencio_deg_5pct"`.
`network` ∈ `er|ba|ws|complete|mean_field` (el ODE usa `mean_field`). Columnas extra de parámetros se
agregan a la derecha **sin cambiar el orden de las columnas anteriores**.

### 4.6 Métricas (definiciones fijas en `metrics.py`)
`peak_I` (máx. de I), `t_peak` (hora del pico), `reach` (= `cum_exposed` final), `believers_total`
(= `cum_believers` final), `t_extinct` (primera hora tras el pico con I ≤ 0.1 %; NaN si no ocurre), `auc_I`
(∫I dt). Métrica derivada para intervenciones: **reducción relativa del alcance =
1 − reach_intervención / reach_base** (con IC 95 % sobre réplicas).

---

## 5. Catálogo de experimentos y validaciones

| ID | Qué | Quién | Detalle |
|---|---|---|---|
| E1 | Línea base por topología | P3 | ER, BA, WS (N=5000, ⟨k⟩=10) + ODE `mean_field`; 30 réplicas |
| E2 | Sensibilidad | P1 | ODE: β∈[0.005,0.06] × γ∈[0.03,0.3] → R0, alcance, pico (mapas de calor); p_believe∈{0.2,…,0.9}; ABM en rejilla 3×3 sobre ER y BA |
| E3 | Fact-checking | P3 | `t_start`∈{0,6,12,24,48} h × `delta`∈{0.05,0.1,0.2,0.4}; redes ER y BA (+ODE) |
| E4 | Silenciar hubs/bots | P3 | `silence_frac`∈{1,2,5,10 %} × targeting `random` vs `degree`; t_start=12 h; ER, BA, WS |
| E5 | Prebunking | P3 | `prebunk_frac`∈{5,10,20,40 %} × targeting; t_start=0 y 12 h; ER, BA |
| E6 | Origen de la noticia | P3 | `seed_strategy` random vs hub, sin intervención; ER, BA, WS |
| E7 | Estrategias a igual presupuesto | P3 | silencio vs prebunk con 5 % de nodos + mejor fact-checking; reducción relativa del alcance |
| V1 | Límite de campo medio | P1 (+P2) | ABM en grafo completo (N=1000) con `beta = beta_ode/(N-1)` vs ODE: RMSE de I(t), error de pico y t_peak |
| V2 | Tamaño final analítico | P1 | alcance vs R0 (0.5…4): fórmula `s_inf = exp(-R0(1-s_inf))` (verificar/derivar), ODE y ABM; umbral en R0=1 |
| V3 | Contrastes cualitativos con la literatura | P1 | (a) BA tiene umbral de β menor que ER (Pastor-Satorras & Vespignani); (b) noticia "falsa" (β, p mayores) vs "verdadera" se propaga más lejos/rápido (Vosoughi et al.). Es consistencia cualitativa, NO calibración |
| V4 | Convergencia Monte Carlo | P2 | ancho del IC vs nº de réplicas (5…100) y varianza vs N (1000…10000) |

Se entregan resultados con **IC 95 %**, comparaciones clave con prueba estadística (Mann–Whitney o Welch,
`scipy.stats`) y se dicen los tamaños de efecto. **Extras opcionales (solo si todo lo demás está en CP4):**
red real (p. ej. SNAP ego-Facebook, verificar disponibilidad y licencia) y calibración cualitativa con una cascada pública.

---

## 6. Reparto de trabajo (≈17-19 h por persona; el reparto es por carga, nadie hace solo "programar" o solo "redactar")

| | **P1 · Camila** | **P2 · Marinés** | **P3 · Juan Francisco** | **P4 · Ernesto** |
|---|---|---|---|---|
| Rol | Modelo matemático y validación | Simulación en redes (ABM) y repo | Intervenciones, experimentos y resultados | Dashboard, integración del documento y slides |
| Código | `ode_model`, `sensitivity` (E2), `validation` (V1-V3) | `networks`, `abm`, V4, tests, README | `interventions`, `experiments` (E1,E3-E7), `figures` | `app/dashboard.py` (+ tests de carga de CSV) |
| Documento | 1 Problema · 2 Análisis · 4a Modelo ODE · 6b Validación | 4b ABM y redes · 5 Herramientas (+ compilar prompts de los 4) | 3 Propuesta (y justificación de la técnica) · 4c Intervenciones · 6a Resultados | 4d Dashboard · 7 Conclusión · 8 Bibliografía · **ensamblar PDF final** |
| Entregable | **Entrega parcial** (vie 30) | **Repositorio público** (1 pt) | **Video** (1 pt) | **Slides** (5 pts) y coordinar ensayo |
| Slides | 2, 4, 6 | 5, 7 | 3, 8, 9 | 1, 10 |

Cada quien presenta en clase **las slides que le tocan** (los 4 deben dominar todo el proyecto).
Revisión cruzada de PRs: **P1 ↔ P2** y **P3 ↔ P4**.

Slides (10): 1 Portada + problema · 2 Análisis, pregunta, hipótesis · 3 Propuesta y por qué SEIR-D + ABM ·
4 Modelo SEIR-D y R0 · 5 ABM sobre redes + Monte Carlo · 6 Validación ODE vs ABM · 7 Herramientas y uso crítico
de IA · 8 Resultados: topología y origen (E1, E6) · 9 Resultados: intervenciones (E3–E5, E7) ·
10 Demo del dashboard, conclusiones y limitaciones.

### Dependencias (quién necesita qué de quién)

```
Contrato (listo en CP0) ──► todos arrancan con mock.py
P2 ABM (CP1 versión simple) ──► P1 validación V1/V2, P3 experimentos, P4 dashboard
P3 plan() completo (CP1)    ──► P2 integra silence/immunize
P1 ODE (CP1)                ──► P3 curvas mean_field en E1/E3, P4 dashboard
```
**El camino crítico es el ABM de Marinés: primero una versión simple que funcione (sin intervenciones
complejas) el miércoles; refinar después.**

---

## 7. Calendario y checkpoints (hoy es mar 27 oct)

| Checkpoint | Cuándo | Qué debe estar |
|---|---|---|
| **CP0** | mar 27 (noche) | Marinés sube este esqueleto a `main`. Todos: `git pull`, crear su rama, entorno listo, `pytest` pasa, leer contrato, abrir su `docs/prompts/PROMPTS_<nombre>.md` |
| **CP1** | mié 28 (noche) | Cada módulo núcleo cumple su firma con una **primera versión funcional + tests**. Push a la rama propia, aviso al grupo |
| **CP2** | jue 29 (mediodía) | Integración 1: ramas P1+P2+P3 mergeadas a `main` por PR; P3 y P4 cambian de `mock` a datos reales. **Entrega parcial lista** (Camila) y subida a Canvas el **jue 29** (límite vie 30) |
| **CP3** | sáb 31 (noche) | Experimentos finales corridos (N=5000, 30 réplicas), `results/*.csv` y `figures/*.png` comiteados, dashboard con datos reales, borradores de TODAS las secciones del documento |
| **CP4** | dom 1 nov (tarde) | Documento final ensamblado, slides terminadas, video grabado, repo limpio y **público**, README completo. **Congelamiento dom 22:00** |
| Entrega | lun 2 nov | PDF documento + link repo + PDF slides en Canvas (confirmar hora límite en Canvas) |

(El 1 de noviembre es feriado en Guatemala: contar con ese día como buffer, no como día de trabajo pesado.)

---

## 8. Reglas de Git y de checkpoints

- Ramas: `p1-camila-ode`, `p2-marines-abm`, `p3-juanfran-experimentos`, `p4-ernesto-dashboard-docs`. **Nunca commits a `main`** directos; se entra por Pull Request revisado por la pareja de revisión.
- Cada quien edita **solo los archivos de su propiedad** (sección 6). Si necesitas tocar algo ajeno, pídelo por el chat del grupo.
- Mensajes de commit: `tipo(area): CPn descripción corta` con tipo ∈ `feat|fix|test|docs|contract|chore`. Ej.: `feat(abm): CP1 simulate_abm vectorizado con semillas hub/random`.
- Commits pequeños y frecuentes **solo en checkpoints**: antes de cada commit se corre `pytest` y se verifica lo que diga el checkpoint.
- Archivos pesados no van al repo (no `.venv`, no datos >5 MB). Los `results/*.csv` finales sí.
- Semillas fijas (`SEED0`) para que todo sea reproducible; los scripts deben poder correrse desde cero.
- Figuras: matplotlib, etiquetas y título en español, ejes con unidades (horas, fracción de la población), leyenda, `dpi=200`, nombre `fig_<exp>_<descripcion>.png`, paleta consistente (misma convención de color por compartimento: S azul, E amarillo, I rojo, R gris/verde).

## 9. Cambios al contrato
Si necesitas cambiar un tipo, firma, formato de CSV o regla del modelo: (1) escríbelo en el chat del grupo,
(2) espera el "ok" de los afectados, (3) haz un commit separado `contract(...)` que solo toque eso, (4) todos
hacen `git merge main` a su rama. Sin acuerdo previo, **no se cambia**.

## 10. Uso de IA (obligatorio documentarlo)

Cada integrante mantiene `docs/prompts/PROMPTS_<nombre>.md` con **cada prompt relevante** y esta ficha:

```
### Prompt N — <título corto>  (fecha, herramienta/modelo)
**Prompt:** <texto literal o resumen fiel>
**Resultado:** <qué devolvió la IA, en 2-3 líneas>
**Evaluación:** ✅ útil / ⚠️ parcial / ❌ erróneo — <por qué; cómo lo verificaste (tests, cálculo a mano, comparación con literatura)>
**Corrección/Iteración:** <qué cambiaste o pediste después>
**Comprensión:** <explica en tus palabras qué hace el código/idea y por qué funciona>
```
