# 7. Conclusión

> Esqueleto CP1 (Ernesto). Los veredictos y los números se llenan en CP3 con base en `06a_resultados.md`,
> `06b_validacion.md` y `results/*.csv`. No escribir ningún número que no salga de un CSV.

## 7.1 Respuesta a la pregunta de investigación

*¿Cómo influyen la topología de la red, el origen de la noticia y el tipo/momento de la intervención en el
alcance y la velocidad de una noticia falsa, y qué estrategia reduce más el alcance por nodo intervenido?*

[PENDIENTE CP3: un párrafo por factor (topología, origen, intervención) y la estrategia ganadora de E7, con la
reducción relativa del alcance y su IC 95 %.]

## 7.2 Evaluación de las hipótesis

| Hipótesis | Evidencia (experimento, archivo) | Qué decide el veredicto | Veredicto |
|---|---|---|---|
| H1: a igual ⟨k⟩, BA tiene mayor pico y mayor velocidad que ER y WS | E1, `results/E1_metrics.csv` | `peak_I` mayor y `t_peak` menor en BA; prueba de Mann–Whitney o Welch | PENDIENTE |
| H2: cada retraso del fact-checking aumenta el alcance de forma no lineal | E3, `results/E3_metrics.csv` | forma de `reach` contra `t_start` (incrementos crecientes entre 0, 6, 12, 24 y 48 h) | PENDIENTE |
| H3: silenciar el X % de mayor grado reduce más que al azar en BA, pero no en ER | E4, `results/E4_metrics.csv` | diferencia degree − random de la reducción relativa del alcance, en BA y en ER | PENDIENTE |
| H4: el prebunking por grado es más eficiente que el aleatorio | E5, `results/E5_metrics.csv` | reducción relativa del alcance por fracción inmunizada, degree contra random | PENDIENTE |
| H5: sembrar desde un hub da un pico más temprano y más alto | E6, `results/E6_metrics.csv` | `t_peak` menor y `peak_I` mayor con `seed_strategy = hub` | PENDIENTE |

Veredictos posibles: confirmada, refutada o parcial. Si un resultado contradice una hipótesis, se reporta tal cual.

## 7.3 Validación

[PENDIENTE CP3: resumen de 06b en 3–4 líneas: V1 límite de campo medio (RMSE de I(t), error de pico),
V2 tamaño final analítico y umbral en R0 = 1, V3 contrastes cualitativos con la literatura, V4 convergencia
Monte Carlo.]

## 7.4 Limitaciones

- **Parámetros no calibrados.** Los valores por defecto son ilustrativos, no estimados con datos reales. El
  análisis de sensibilidad (E2) muestra cuánto dependen las conclusiones de ellos, pero no sustituye una
  calibración.
- **Redes sintéticas y estáticas.** ER, BA y WS capturan rasgos generales (hubs, agrupamiento), no una red
  social real. Las conexiones no cambian durante la simulación, aunque en la realidad se siguen y dejan de
  seguir cuentas.
- **Contenido homogéneo y sin algoritmos de recomendación.** Todas las noticias y todos los usuarios usan los
  mismos parámetros. No se modela el feed, que decide qué ve cada persona.
- **ODE con mezcla homogénea.** El ODE supone que todos pueden contactar a todos; por eso no ve la topología
  ni puede evaluar intervenciones dirigidas. Se usa como referencia y validación, no como modelo final.

## 7.5 Trabajo futuro

- Calibrar `beta`, `sigma`, `p_believe` y `gamma` con cascadas reales de difusión (por ejemplo, datos públicos
  de retuits).
- Usar redes dinámicas o redes reales (por ejemplo, SNAP ego-Facebook, verificando disponibilidad y licencia).
- Modelar bots y cuentas coordinadas como nodos con reglas propias, en lugar de solo silenciarlos.

## 7.6 Reflexión sobre el uso crítico de la IA

[PENDIENTE: Ernesto, con sus palabras, a partir del "Resumen para el documento" de su bitácora
(`docs/prompts/PROMPTS_ernesto.md`): qué propuso la IA, qué se verificó y cómo, qué falló y qué decidió el equipo.]
