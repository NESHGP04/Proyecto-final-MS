# Bitácora de prompts — Marinés García

**Herramienta(s) de IA usadas:** Claude Code (Sonnet 5.5)

> Borrador generado por la IA al cierre de CP1. Marinés debe leerlo, corregirlo y completar la sección
> "Comprensión" con sus propias palabras antes de commitearlo.

---

### Prompt 1 — Diseño del reparto y contrato del proyecto  (2026-10-27, Claude Code)
**Prompt:** Pasé el PDF del proyecto final y pedí dividir las tareas entre 4 personas, trabajando en paralelo, con
un .md por persona para que cada quien se lo dé a su IA, con contexto completo y checkpoints para commits.
**Resultado:** La IA preguntó datos faltantes (técnicas del curso, fechas, stack, repo), diseñó el modelo SEIR-D + ABM
sobre redes, un contrato en código (`params.py`, `metrics.py`, `mock.py`) y 4 archivos de tareas.
**Evaluación:** ✅ útil — pero hay que verificarlo, no creerlo. Antes de entregar, la IA corrió un prototipo del ABM y del
ODE con los parámetros por defecto para comprobar que producían brotes distintos por red.
**Corrección/Iteración:** (completar si algo del contrato se ajusta)
**Comprensión:** (Marinés: explica con tus palabras por qué hace falta un contrato común para trabajar en paralelo)

### Prompt 2 — Implementar `networks.py` y `abm.py` (CP1)  (2026-10-27, Claude Code)
**Prompt:** "¿Podemos empezar con mi parte?" (partiendo de las instrucciones de la sección C del .md de P2).
**Resultado:** Generadores ER/BA/WS/completa, `degree_stats`, `simulate_abm` vectorizado (matriz dispersa × vector de
difusores, actualización síncrona), `run_replicates`, 34 tests.
**Evaluación:** ⚠️ parcial en el primer intento — 2 de 34 tests fallaron y ambos fueron informativos:
1. *Error del test (mío, no del código):* esperaba que "inmunizar a todos en `t_start=0`" dejara las semillas; el contrato dice que
   la intervención se aplica *antes* de elegir semillas, así que no queda ninguna. Se corrigió el test y se añadió otro con `t_start=1`.
2. *Error real del ABM:* con `omega>0` una persona re-expuesta se contaba varias veces y `cum_exposed` pasaba de 1. El contrato la
   define como "fracción que alguna vez fue expuesta"; se corrigió contando nodos únicos (máscaras booleanas `ever_exposed/ever_believer`).
Verificación: 34 tests en verde; 30 réplicas con N=5000 en ≈2 s por topología; BA con pico más alto y más temprano que ER, y semillas `hub` más rápidas que `random`.
**Corrección/Iteración:** el defecto 2 también afecta al ODE del contrato cuando `omega>0` (la ecuación de `dCumExp/dt` cuenta eventos, no personas): hay que avisar a Camila.
**Comprensión:** (Marinés: explica con tus palabras cómo `A @ (estado == I)` da los vecinos infectados de todos los nodos de una vez, y por qué la actualización es síncrona)
