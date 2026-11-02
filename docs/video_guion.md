# Guion del video · Propagación de Fake News (Grupo 4)

> **Qué pide el curso:** un video que muestre el funcionamiento de la solución, su implementación y explique los principales hallazgos y puntos de la investigación. No fija duración: este guion está pensado para **≈ 7 minutos** (confirmar con el catedrático si hay un máximo).
> **Reparto:** los 4 hablan, cada quien sobre la parte que construyó y que presentará en clase (ver `docs/CONTRATO.md`, sección 6).
> **Cifras:** todas salen de `results/` (N = 5000, 30 réplicas) y coinciden con el informe. **No** uses cifras del dashboard con N = 1000 para hablar de resultados: ahí los números cambian un poco.

---

## Antes de grabar (15 minutos)

- [ ] `git pull` en `main` y `pytest` en verde (así lo muestras en el segmento 2).
- [ ] Entorno activo (`source .venv/bin/activate`) y `streamlit run app/dashboard.py` abierto en `http://localhost:8501`.
- [ ] En el dashboard, corre **una vez** cada simulación del segmento 4 para que quede en caché y no haya esperas en cámara.
- [ ] Abre en pestañas del navegador o del editor, en este orden: `figures/fig_E1_topologias.png`, `src/fakenews/abm.py`, `figures/fig_V1_campo_medio.png`, `figures/fig_E3_alcance_vs_retraso.png`, `figures/fig_E4_silencio.png`, `figures/fig_E5_prebunking.png`, `figures/fig_E7_reduccion_relativa.png`, el dashboard.
- [ ] Cierra notificaciones, pon la pantalla a 1080p y el zoom del navegador y del editor a un tamaño legible (fuente grande).
- [ ] Graba con QuickTime (Archivo → Nueva grabación de pantalla) o la herramienta del equipo, con micrófono; cada quien graba su segmento por separado y Ernesto/Juan Francisco los une.

---

## Segmento 1 · El problema y el modelo (Camila) · 0:00–1:45

**Pantalla:** portada del informe → `figures/fig_E1_topologias.png` (curvas por topología y ODE).

**Dice:**
> Hola, somos el Grupo 4. Nuestro proyecto estudia cómo se propaga una noticia falsa en una red social y cómo frenarla. No es un tema abstracto: según un estudio de Vosoughi, Roy y Aral publicado en *Science*, las noticias falsas llegan más lejos y más rápido que las verdaderas.
>
> Una plataforma no puede actuar sobre todos sus usuarios, así que la pregunta es: ¿cómo influyen la red, el origen de la noticia y el momento y tipo de intervención en el alcance y la velocidad, y qué estrategia reduce más el alcance por nodo intervenido?
>
> Para responderla tratamos la noticia como un contagio. Cada persona está en uno de cuatro estados: susceptible, expuesta, difusora o removida. A este modelo lo llamamos SEIR-D. En ecuaciones diferenciales, su número reproductivo es R cero igual a beta por grado medio por p, entre gamma, y vale 1.8 con nuestros parámetros. También derivamos una fórmula del tamaño final del brote.
>
> Pero ese modelo supone que todos se mezclan igual, y en una red social hay pocos usuarios con muchísimos contactos. Por eso construimos, además, una simulación basada en agentes sobre redes.

---

## Segmento 2 · Simulación en redes, validación y herramientas (Marinés) · 1:45–3:15

**Pantalla:** `src/fakenews/abm.py` (línea `m = A @ (state == I)`), terminal con `pytest`, `figures/fig_V1_campo_medio.png`.

**Dice:**
> En el simulador cada usuario es un nodo y solo lo contagian sus vecinos. Comparamos tres redes con el mismo número de nodos y el mismo grado medio: Erdős–Rényi, que no tiene estructura; Barabási–Albert, que tiene hubs; y Watts–Strogatz, con grupos cerrados.
>
> Cada hora, todos los nodos se actualizan a la vez. Esta línea es la clave: una multiplicación de matriz dispersa por el vector de quién está difundiendo nos da cuántos vecinos difusores tiene cada nodo, todos de una vez. Por eso 30 réplicas con cinco mil nodos tardan unos dos segundos.
>
> Como el modelo es aleatorio, cada escenario se repite 30 veces. Comprobamos que eran suficientes: con 30 réplicas el alcance queda estimado con una precisión cercana al 2 por ciento.
>
> Para validar, comparamos el simulador con las ecuaciones donde deberían coincidir: en un grafo completo. El error es muy pequeño, y la diferencia que queda la explica el paso de una hora y el azar. También verificamos la fórmula del tamaño final y que el umbral de las redes sigue el orden que predice la teoría.
>
> Usamos Python con NumPy, SciPy, NetworkX y pytest, y la IA como asistente: nos ayudó a avanzar rápido, pero se equivocó varias veces, y esos errores los encontramos ejecutando y comparando. Por ejemplo, un acumulado que contaba eventos y no personas pasaba de 1; lo detectó una prueba.

---

## Segmento 3 · Intervenciones y resultados (Juan Francisco) · 3:15–5:00

**Pantalla:** `fig_E3_alcance_vs_retraso.png` → `fig_E4_silencio.png` → `fig_E5_prebunking.png` → `fig_E7_reduccion_relativa.png`.

**Dice:**
> Evaluamos tres estrategias: fact-checking, que hace que los difusores dejen de compartir antes; silenciar cuentas; y prebunking, que inmuniza a usuarios antes de que vean la noticia.
>
> Primero, la topología. Con los mismos parámetros, la red con hubs tiene un pico de difusores de 0.077 y llega a la hora 36; en la red sin estructura el pico es 0.040 y llega a la hora 70. El alcance final es casi igual: los hubs aceleran la propagación, no cambian cuánta gente la ve.
>
> Segundo, el momento. En la red con hubs, un fact-checking de intensidad media desde el inicio reduce el alcance 76 por ciento; si esperamos 24 horas, 43; si esperamos 48 horas, solo 12. Cada hora de retraso cuesta más que la anterior.
>
> Tercero, a quién intervenir. Silenciar al 5 por ciento de los usuarios de mayor grado reduce el alcance 62 por ciento; silenciar a ese mismo porcentaje al azar, solo 9. Con prebunking pasa algo parecido, y es mucho mejor si es preventivo: 80 por ciento desde el inicio, 43 si se hace a las 12 horas.
>
> Dos de nuestras hipótesis no salieron como esperábamos y las reportamos: apuntar a los hubs también ayuda en la red sin hubs, aunque menos; y la red con grupos cerrados tiene su pico antes que la red con hubs, pero solo porque apenas despega: su brote es pequeño.

---

## Segmento 4 · Dashboard, conclusiones y límites (Ernesto) · 5:00–7:00

**Pantalla:** dashboard, pestaña **Simulador**. Sigue este orden exacto:

1. Topología **Barabási–Albert**, N = 1000, 10 réplicas, sin intervención → *Simular*. Muestra la curva roja de I, la banda y el ODE discontinuo, y las tarjetas (pico, hora del pico, alcance, R0).
2. Misma red, **fact-checking** con inicio en 12 h y δ = 0.2 → *Simular*. Se ve la curva aplanarse.
3. Misma red, intervención **silenciar** 5 % **por mayor grado** a las 12 h → *Simular*. Compara con silenciar al azar.
4. Pestaña **Comparar escenarios** → experimento E4 → muestra las barras con IC 95 %.
5. Pestaña **Estructura de la red** → histograma de grados de BA contra ER (se ven los hubs).

**Dice:**
> Para explorar todo esto sin escribir código hicimos un dashboard con Streamlit. Aquí elegimos una red con hubs y corremos la simulación: la banda son 10 réplicas y la línea discontinua es el modelo de ecuaciones. Ahora activamos un fact-checking a las 12 horas: la curva se aplana. Y ahora silenciamos al 5 por ciento de los usuarios más conectados: la propagación cae muchísimo más que si elegimos al azar.
>
> Las pestañas de comparación leen los mismos archivos de resultados que usamos en el informe, y la de estructura muestra por qué todo esto ocurre: en esta red hay unos pocos nodos con cientos de contactos.
>
> En conclusión: la estructura de la red decide la velocidad, el momento decide cuánto se puede lograr, y apuntar a los usuarios más conectados es mucho más eficiente que repartir la intervención al azar. De cinco hipótesis, tres se confirmaron en lo esencial y dos de forma parcial, y lo reportamos con honestidad.
>
> Sobre los límites: los parámetros son ilustrativos, no calibrados con datos reales, las redes son sintéticas y estáticas, y no modelamos el contenido ni los algoritmos de recomendación. Por eso leemos los resultados como comparaciones entre escenarios, no como predicciones. Todo el código y el informe están en el repositorio. Gracias.

---

## Después de grabar

- [ ] Revisar que se oiga bien y que ninguna cifra contradiga el informe.
- [ ] Subir el video (YouTube como **no listado** o Google Drive con enlace para cualquiera con el vínculo) y **probar el enlace en una ventana privada**.
- [ ] Pegar el enlace en tres lugares: la portada del informe (línea resaltada en amarillo), el `README.md` (sección Video) y la entrega de Canvas.

## Plan B si algo falla en vivo

- Si el dashboard tarda, usa los resultados ya cargados en **Comparar escenarios** (no recalcula).
- Si una simulación da un número distinto al del guion, no lo menciones: habla de la forma de la curva y usa las cifras de las figuras del informe.
