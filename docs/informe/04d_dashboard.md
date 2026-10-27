# 4d. Dashboard interactivo

> Borrador CP1 (Ernesto). Faltan las capturas con los datos finales (CP3).

## Objetivo

El dashboard permite explorar el modelo SEIR-D sin escribir código. Sirve para tres cosas: ver cómo cambian
las curvas al mover un parámetro o una intervención, comparar los escenarios de los experimentos guardados
en `results/`, y mostrar la estructura de las redes sobre las que corre el ABM. También es la demo de la
slide 10 y del video.

## Cómo ejecutarlo

```bash
source .venv/bin/activate          # entorno del proyecto (ver README)
streamlit run app/dashboard.py     # abre http://localhost:8501
```

El código está en `app/dashboard.py` (interfaz) y `app/data.py` (carga de CSV y simulación). Las pruebas
de la capa de datos están en `tests/test_dashboard_data.py`.

## Pestañas

**Simulador.** La barra lateral define la topología (ER, BA, WS), N (500–5000; 1000 por defecto), el número
de réplicas (5–30), el origen de la noticia (`seed_strategy`), los parámetros `beta`, `sigma`, `p_believe`,
`gamma`, `i0` y una intervención (ninguna, fact-checking, silenciar o prebunking, con `t_start`, intensidad y
`targeting`). Al pulsar *Simular* se corren las réplicas del ABM y el ODE. La gráfica muestra S, E, I y R:
la media del ABM con la banda del 95 % de las réplicas y el ODE en línea discontinua. Las tarjetas muestran
el pico de difusores, la hora del pico, el alcance y el R0 de campo medio (`ModelParams.r0_ode`).

*[Captura: `figures/dashboard_simulador.png` — CP3]*

**Comparar escenarios.** Se elige un experimento de `results/` (E1…E7, V1…V4), las redes, los escenarios y
el compartimento. Se ven las curvas con sus bandas y un gráfico de barras del alcance medio por escenario
con su intervalo de confianza del 95 %, más una tabla con los valores.

*[Captura: `figures/dashboard_comparar.png` — CP3]*

**Estructura de la red.** Para ER, BA y WS se muestra el histograma de grados de una red de tamaño N con
⟨k⟩, ⟨k²⟩ y k_max (`degree_stats`), y el dibujo de una red pequeña (N ≤ 200) con el tamaño del nodo
proporcional a su grado. Así se ve por qué BA tiene hubs y ER/WS no.

*[Captura: `figures/dashboard_red.png` — CP3]*

## Decisiones de diseño

- **Separar datos e interfaz.** `app/data.py` no dibuja nada; así se prueba con `pytest` sin abrir Streamlit.
- **Formato único.** El simulador convierte sus corridas con `aggregate_curves` y `metrics_table`, las mismas
  funciones del contrato que generan `results/`. Las dos pestañas leen el mismo formato.
- **Caché.** Las simulaciones y los CSV se guardan con `st.cache_data`: repetir una configuración es
  instantáneo. Riesgo: mostrar datos viejos. Por eso la llave de caché de cada CSV incluye su fecha de
  modificación (si P3 regenera un archivo, se relee), y la de la simulación incluye todos los parámetros.
- **Formulario con botón *Simular*.** Una corrida de 30 réplicas con N = 5000 tarda varios segundos; con el
  formulario no se recalcula en cada movimiento de un control. N = 1000 por defecto por la misma razón.
- **Datos de demostración.** Mientras el ABM o el ODE reales no estén en `main`, el dashboard usa
  `fakenews.mock` y lo avisa con un banner ("datos de demostración"). El interruptor `USE_MOCK` lo fuerza.
  Cuando los módulos reales existen se usan solos; el mock queda solo como respaldo.
- **Intervalos.** La banda de las curvas es el percentil 2.5–97.5 de las réplicas (dispersión, contrato 4.5).
  Las barras de alcance usan el IC 95 % de la media, media ± 1.96·EE (aproximación normal; con 30 réplicas es
  razonable). El ODE es determinista: no tiene banda.
- **ODE y targeting por grado.** El ODE no ve la topología; con `targeting = degree` no se superpone.
- **Colores.** S azul, E amarillo, I rojo, R gris, como en todas las figuras del proyecto.

## Limitaciones

- No muestra el estado de cada nodo en el tiempo: `SimResult` solo guarda fracciones agregadas y no se cambió
  el contrato para eso.
- Con N = 5000 y 30 réplicas la espera es de varios segundos; el valor por defecto es menor.
- El ODE se calcula con ⟨k⟩ = 10 (`MEAN_DEGREE`), no con el ⟨k⟩ medido de cada red.
- Es una herramienta de exploración local: no está desplegada en un servidor.
