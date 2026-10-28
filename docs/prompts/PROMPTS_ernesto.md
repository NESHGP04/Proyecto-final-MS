# Bitácora de prompts — Ernesto Asencio

> Ficha por cada prompt relevante. Se usa para la sección "Herramientas aplicadas" del documento
> (el curso pide evaluación crítica del uso de IA).

**Herramienta(s) de IA usadas:** Claude Code (modelo Claude Opus 5.5)

---

### Prompt 1 — Dashboard CP1 y esqueleto del documento  (27 oct 2026, Claude Code / Claude Opus 5.5)
**Prompt:** "Implementa lo que está en mis instrucciones de P4" (archivo con el protocolo, el contrato y mis tareas CP1–CP4).
**Resultado:** La IA revisó el repo y propuso un plan: hacer CP1 completo y dejar listo lo que no depende de otros
(checklist, borradores de 04d y 07, referencias). Escribió `app/data.py`, `app/dashboard.py`, 10 pruebas en
`tests/test_dashboard_data.py` y los documentos. Dejó como pendiente lo que depende de resultados o slides de otros.
**Evaluación:** ✅ útil — verificado con `pytest` (16 pruebas pasan), con `streamlit.testing.AppTest` moviendo todos
los controles (sin excepciones) y contra el ABM real de Marinés (rama `p2-marines-abm`) en una copia temporal:
el simulador usó el ABM real, la pestaña de redes funcionó y se cargaron los CSV `V4_*`. Errores menores de la IA:
usó un parámetro de Streamlit obsoleto (`use_container_width`) y una ruta relativa equivocada en su script de prueba;
los corrigió al ejecutar. Una referencia (Plotly) no se pudo verificar y quedó marcada `[VERIFICAR]`.
**Corrección/Iteración:** [Ernesto: qué cambiaste o pediste después]
**Comprensión:** [Ernesto, con tus palabras: qué hace `simulate()` cuando el ABM no existe, por qué la llave de caché
de los CSV incluye la fecha de modificación y por qué el ODE no se dibuja con targeting = degree]

---

## Resumen para el documento (llenar en CP3)
- Prompts que funcionaron bien y por qué:
- Prompts con errores o respuestas inadecuadas y por qué ocurrió:
- Cómo validé las respuestas de la IA:
- Cómo contribuyó la IA a mi parte del trabajo (y qué hice yo):
