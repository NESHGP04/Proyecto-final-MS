<!-- BORRADOR DE LA IA para las slides 5 y 7 de Marinés. Poco texto por slide; el resto se dice en voz alta. Ernesto lo pasa al deck. -->

# Slide 5 — Simulación basada en agentes sobre redes

**Título sugerido:** "De la población homogénea a la red social"

- **Por qué un ABM:** el ODE supone que todos se mezclan igual; en redes reales hay hubs y las intervenciones dirigidas necesitan saber *a quién*.
- **3 redes, mismo ⟨k⟩ ≈ 10:** Erdős–Rényi (sin estructura), Barabási–Albert (hubs), Watts–Strogatz (círculos cerrados).
- **Cada persona:** S → E → I → R; transiciones por hora, síncronas (misma "foto" para todos).
- **Monte Carlo:** 30 réplicas por escenario → bandas del 95 %.
- **Convergencia (V4):** con 30 réplicas el IC del alcance es ≈ 2 % de la media; N = 5000 reduce la variabilidad de redes chicas.

**Figura:** `figures/fig_V4_ic_vs_replicas.png`. Si Juan Francisco ya entregó E1 (curvas I(t) de ER/BA/WS con bandas), usar esa y mover V4 a una esquina.

**Notas para hablar (~2 min):** empieza con la pregunta "¿qué pasa si el contagio depende de *con quién* te conectas?"; explica en una frase por qué 1 − (1−q)^m
(cada amigo difusor es una oportunidad independiente de contagio); cierra con V4: "no elegimos 30 réplicas por intuición, lo medimos".

---

# Slide 7 — Herramientas y uso crítico de IA

**Título sugerido:** "La IA propone, nosotros verificamos"

- **Stack:** Python · NumPy · SciPy (sparse, ODE) · NetworkX · pandas · Matplotlib · Streamlit · pytest · Git/GitHub.
- **Cómo usamos la IA:** bitácora de prompts por persona + 3 preguntas de comprensión al cierre de cada checkpoint.
- **Qué falló (y lo detectamos):** un test mal escrito por la IA; un acumulado que contaba eventos y no personas (pasaba de 1 con ω > 0); una cita con páginas erróneas en un sitio web.
- **Cómo verificamos:** pruebas automáticas · prototipo independiente · cifras contra los CSV · fuentes contra DOI.
- **Aporte real de la IA:** velocidad para armar el código base y los tests; el criterio y la validación fueron nuestros. [PENDIENTE: ajustar con las 4 bitácoras]

**Figura sugerida:** tabla de 3 filas "qué falló / por qué / cómo lo detectamos" (de `05_herramientas.md`, sección 5.3).

**Notas para hablar (~1.5 min):** insistir en que mostrar los errores es parte de la nota; elegir *un* ejemplo y contarlo bien (el acumulado mayor que 1: qué esperábamos, qué pasó, cómo lo encontramos).
