# 2. Análisis

## 2.1 El sistema

**Actores y variables.** El sistema está formado por usuarios conectados en una red. Cada usuario ocupa uno de cuatro estados: susceptible (S), si todavía no ha visto la noticia; expuesto (E), si ya la vio y está decidiendo; difusor (I), si cree en ella y la comparte; o removido (R), si no la comparte por escepticismo, desmentido, silenciamiento o pérdida de interés.

Las principales variables de salida son el alcance acumulado, el máximo de difusores simultáneos, la hora de ese pico y el tiempo de extinción. El alcance registra quiénes han visto la noticia alguna vez y no disminuye cuando una persona cambia de estado. Además, como R incluye personas silenciadas antes de exponerse, pertenecer a R no implica necesariamente haber visto la noticia.

**Supuestos y simplificaciones.**

- Se representa una sola noticia falsa, sin competencia con otras noticias o con su versión corregida.
- La población tiene tamaño fijo y las conexiones permanecen constantes.
- Todos los enlaces tienen la misma tasa de transmisión.
- Los parámetros permanecen constantes, excepto cuando se aplica una intervención.
- El ODE supone mezcla homogénea, mientras que el ABM permite contactos únicamente entre vecinos.
- La probabilidad de creer y compartir es fija; no depende del contenido, las emociones o las características personales.
- El tiempo se mide en horas y el ABM utiliza pasos de una hora con actualización síncrona.

## 2.2 Parámetros

Los siguientes valores son ilustrativos y no fueron estimados a partir de datos reales.

| Parámetro | Valor | Significado | Criterio de elección |
|---|---|---|---|
| β | 0.03 h⁻¹ | Tasa de transmisión por vecino difusor | Permite estudiar un escenario de propagación con el R0 de referencia mayor que 1. |
| σ | 0.5 h⁻¹ | Tasa de salida de E para decidir entre I y R | Representa un tiempo medio de decisión de 2 horas en tiempo continuo. |
| p | 0.6 | Probabilidad de creer y compartir al salir de E | Valor ilustrativo que se modifica en el análisis de sensibilidad E2. |
| γ | 0.1 h⁻¹ | Tasa de pérdida de interés | Representa una duración media de 10 horas como difusor en tiempo continuo. |
| ω | 0 h⁻¹ | Tasa de retorno de R a S por olvido | Se desactiva en los experimentos principales. |
| i₀ | 0.01 | Fracción inicial de difusores | La propagación comienza con un 1 % de semillas. |
| ⟨k⟩ | Aproximadamente 10 | Grado medio de la red | Se mantiene comparable entre las topologías para reducir diferencias debidas al número de conexiones. |

En la aproximación de mezcla homogénea, la tasa agregada de transmisión es b = β⟨k⟩. Por lo tanto:

$$
R_0=\frac{bp}{\gamma}
=\frac{\beta\langle k\rangle p}{\gamma}
=\frac{0.03(10)(0.6)}{0.1}
=1.8.
$$

Este valor sirve como referencia de campo medio; no determina por sí solo el umbral de cada red. Además, la actualización discreta puede introducir diferencias respecto al modelo continuo. Por ejemplo, si la probabilidad de abandonar I en cada paso es la siguiente:

$$
q=1-e^{-\gamma\Delta t},
$$

la duración media, con pasos de una hora, es:

$$
\frac{\Delta t}{q}
=
\frac{1}{1-e^{-0.1}}
\approx 10.5\ \text{horas}.
$$

Como los parámetros no están calibrados, el experimento E2 evalúa la sensibilidad de los resultados a sus cambios.

## 2.3 Comparación de enfoques y elección del modelo

| Enfoque | Qué aporta | Limitación para este proyecto |
|---|---|---|
| Modelos clásicos de rumores, como Daley–Kendall | Distinguen entre personas que desconocen el rumor, lo difunden y dejan de difundirlo. | Sus formulaciones básicas no incorporan explícitamente todos los mecanismos de decisión y moderación considerados aquí. |
| SEIZ | Incluye personas susceptibles, expuestas, difusoras y escépticas. Bettencourt et al. (2006) lo utilizaron para estudiar la difusión de ideas y Jin et al. (2013) lo aplicaron a noticias y rumores en Twitter. | Su formulación compartimental no identifica usuarios concretos para intervenir según sus conexiones. |
| Cascadas independientes y umbral lineal | Representan la difusión sobre grafos y permiten estudiar la selección de nodos influyentes. | Sus versiones básicas no incluyen conjuntamente las etapas de exposición, decisión y pérdida de interés utilizadas en este proyecto. |
| SIR en redes | Permite estudiar cómo la estructura de conexiones afecta el umbral y el tamaño de los brotes. | Su versión básica no contiene una etapa de decisión ni las intervenciones específicas del proyecto. |
| **SEIR-D mediante ODE y ABM** | Combina una referencia analítica con una representación explícita de usuarios, conexiones e intervenciones dirigidas. | Utiliza parámetros ilustrativos y redes estáticas, por lo que sus resultados no constituyen predicciones de una plataforma real. |

Los antecedentes de esta comparación corresponden a Daley y Kendall (1965), Bettencourt et al. (2006), Jin et al. (2013), Kempe et al. (2003) y Newman (2002).

**Por qué se complementa el ODE con el ABM.** El ODE facilita el análisis del número reproductivo, el umbral y el tamaño final bajo mezcla homogénea. Sin embargo, no representa que algunos usuarios tienen muchas más conexiones que otros. Pastor-Satorras y Vespignani (2001) mostraron la ausencia de un umbral positivo en el límite de redes libres de escala infinitas para el modelo SIS estudiado. Ese resultado no puede trasladarse directamente a nuestro modelo ni a redes finitas de 5 000 nodos. Aquí se evaluará si la heterogeneidad reduce el umbral, sin asumir que lo elimina.

El ABM permite representar esa estructura y aplicar intervenciones a usuarios específicos. También incorpora variaciones aleatorias entre réplicas. Aunque puede verificarse mediante otras pruebas, disponer del ODE aporta una referencia adicional para comprobar su comportamiento en condiciones comparables. Las pruebas V1 y V2 estudian esa concordancia, considerando las diferencias por discretización y tamaño finito.

## 2.4 Hipótesis a poner a prueba

Las siguientes hipótesis se evaluarán mediante los experimentos. No se presentan como resultados confirmados.

- **H1:** con grado medio y parámetros comparables, BA presenta un pico de difusores mayor y una propagación más rápida que ER y WS.
- **H2:** aumentar el retraso del fact-checking incrementa el alcance de manera no lineal.
- **H3:** silenciar al mismo porcentaje de usuarios según su mayor grado reduce más el alcance que seleccionarlos al azar en BA, pero no en ER.
- **H4:** el prebunking dirigido por grado reduce más el alcance por nodo intervenido que el aleatorio.
- **H5:** iniciar la propagación desde usuarios de alto grado produce un pico más temprano y elevado que seleccionar las semillas al azar, manteniendo igual su cantidad.

Las conclusiones se basarán en los CSV de resultados. Si los datos contradicen alguna hipótesis, se reportará esa diferencia y se analizarán sus posibles causas.

## 2.5 Fuera de alcance

El proyecto no incluye calibración con datos reales, contenido y emociones del mensaje, cambios en las conexiones, competencia entre noticias, bots como una clase distinta de agentes, comportamiento adaptativo ni algoritmos de recomendación.

Como extensión opcional, una vez terminados los experimentos principales, podría incorporarse una red real, como SNAP ego-Facebook, previa comprobación de su disponibilidad y condiciones de uso.