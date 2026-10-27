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

### Prompt 3 — V4 convergencia Monte Carlo y borrador de 04b  (2026-10-27, Claude Code)
**Prompt:** "Ya commiteé los cambios, sigamos" (siguiente paso de mi parte tras CP1).
**Resultado:** `convergence.py` (ancho del IC vs nº de réplicas y variabilidad vs N), 4 CSV, 2 figuras, tests y un borrador de `04b_abm_redes.md`.
**Evaluación:** ✅ útil, con verificación — los números escritos en el borrador se compararon contra `results/V4_*.csv` y coinciden
(alcance: semiancho del IC ≈ 6 % con 5 réplicas, ≈ 2 % con 30, ≈ 1 % con 100). ⚠️ Un detalle: en la primera figura la etiqueta del eje y
del panel derecho se encimaba con el panel izquierdo; se corrigió ampliando la figura y el espaciado. ⚠️ El borrador del documento es texto de la IA:
hay que reescribirlo con mis palabras.
**Corrección/Iteración:** el pico de difusores queda menos preciso (≈ 4–6 % con 30 réplicas) que el alcance; se dice así en el documento, sin maquillarlo.
**Comprensión:** (Marinés: ¿qué significa que el IC se estreche como 1/√réplicas y por qué 30 réplicas alcanzan?)

### Prompt 4 — Verificación de referencias  (2026-10-27, Claude Code)
**Prompt:** "¿Puedes hacer tú las secciones de verificar?"
**Resultado:** la IA buscó en la web cada referencia marcada `[VERIFICAR]` (ER, BA, WS, Wilensky & Rand, Newman, NetworkX, NumPy, SciPy, Matplotlib, pandas)
y generó `refs_marines.md` en APA 7.
**Evaluación:** ✅ todas las referencias coincidieron con registros bibliográficos o editoriales (DOI, volumen, páginas). ⚠️ Límites que la IA declaró:
las páginas de McKinney (2010) salen de un solo registro, los editores de ese volumen no se verificaron y las listas de autores de NumPy/SciPy están abreviadas.
Una fuente web (BibBase) traía un error en el campo de páginas de Erdős & Rényi; se descartó al contrastarla con las demás.
**Corrección/Iteración:** completar autores de NumPy/SciPy al unificar la bibliografía.
**Comprensión:** (Marinés: ¿por qué no basta con que la IA "recuerde" una cita, y cómo se comprueba una referencia?)

---

## Resumen para el documento (llenar en CP3)
- Prompts que funcionaron bien y por qué:
- Prompts con errores o respuestas inadecuadas y por qué ocurrió:
- Cómo validé las respuestas de la IA:
- Cómo contribuyó la IA a mi parte del trabajo (y qué hice yo):
