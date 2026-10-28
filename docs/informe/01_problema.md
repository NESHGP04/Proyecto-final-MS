# 1. Descripción del problema

## 1.1 Contexto y relevancia

Las redes sociales facilitan que una noticia llegue a muchas personas en poco tiempo, sin importar si su contenido es verdadero o falso. Vosoughi, Roy y Aral (2018) analizaron aproximadamente 126 000 cascadas de rumores verificados en Twitter entre 2006 y 2017. Encontraron que las noticias falsas se difundían más rápido y llegaban más lejos que las verdaderas, especialmente cuando trataban temas políticos. También observaron que los bots aceleraban ambos tipos de noticias de manera similar. Esto sugiere que la diferencia estaba relacionada con la mayor disposición de las personas a compartir información falsa.

La difusión de desinformación representa un problema porque puede afectar las decisiones de las personas y tener consecuencias políticas, económicas y sociales. Por ello, resulta útil estudiar cómo se propaga y qué medidas podrían limitar su alcance.

La desinformación puede afectar la salud y las decisiones de las personas. Durante la pandemia de COVID-19, la Organización Mundial de la Salud (OMS, 2020) informó que cientos de personas murieron en Irán después de consumir metanol, tras circular mensajes en redes sociales que afirmaban falsamente que servía para curar la enfermedad. También señaló que los rumores sobre una posible escasez de alimentos llevaron a algunas personas a acumular productos, lo que contribuyó a generar desabastecimiento. Estos casos muestran que la información falsa puede provocar consecuencias fuera de las redes sociales y justifican estudiar cómo se propaga y cómo reducir su alcance.

## 1.2 Estudios que modelan estos fenómenos

La propagación de noticias y rumores se ha estudiado mediante modelos similares a los utilizados para describir epidemias. Jin et al. (2013), por ejemplo, aplicaron el modelo SEIZ, que distingue entre personas susceptibles, expuestas, infectadas y escépticas, a ocho eventos reales de Twitter. Según sus resultados, este modelo representaba los datos mejor que un modelo SIS simple.

Este trabajo respalda el uso de modelos de contagio para estudiar la difusión de información. Sin embargo, una representación homogénea de la población no describe las conexiones entre usuarios, lo que limita el análisis de intervenciones dirigidas a cuentas específicas. Por eso, este proyecto incorpora una simulación basada en agentes sobre distintas redes.

## 1.3 Actores afectados

- **Usuarios:** reciben la noticia y pueden creerla y compartirla.
- **Plataformas digitales:** deciden cómo y cuándo intervenir, considerando sus recursos disponibles.
- **Verificadores de datos y medios:** revisan la información y publican desmentidos.
- **Autoridades de salud y comunicación pública:** buscan reducir la difusión de rumores, especialmente durante una crisis.
- **Investigadores:** utilizan modelos para comparar estrategias sin intervenir directamente sobre usuarios reales.

## 1.4 Alcance

El proyecto consiste en un estudio de simulación con parámetros ilustrativos, sin calibración con datos reales. Se representa la propagación de una sola noticia falsa durante 240 horas en redes estáticas y sintéticas de tipo Erdős–Rényi, Barabási–Albert y Watts–Strogatz, con 5 000 nodos y grado medio de 10.

No se incluyen cambios en las conexiones, competencia entre noticias, características del contenido ni una descripción detallada del comportamiento de cada usuario. Por estas limitaciones, los resultados se interpretan como comparaciones relativas entre escenarios y no como predicciones de situaciones reales.

El silenciamiento se aplica a cuentas muy conectadas, identificadas por su alto grado, sin asumir que sean bots. Esta distinción es relevante porque el estudio de Vosoughi, Roy y Aral (2018) no atribuye a los bots la diferencia observada entre la difusión de noticias verdaderas y falsas.

## 1.5 Objetivo general

Comparar cómo la topología de la red, el origen de la noticia y el tipo y momento de intervención influyen en el alcance y la velocidad de propagación de una noticia falsa mediante modelación y simulación.

## 1.6 Objetivos específicos

1. Formular un modelo determinista SEIR-D y derivar su número reproductivo básico y la ecuación del tamaño final de la propagación.
2. Implementar un modelo basado en agentes sobre redes complejas y realizar réplicas Monte Carlo para cuantificar la variabilidad de los resultados.
3. Comprobar la concordancia entre el ODE, el ABM en condiciones de campo medio y el tamaño final analítico, además de contrastar cualitativamente los resultados con la literatura.
4. Analizar cómo la topología y el origen de la noticia afectan el pico y la velocidad de propagación, según las hipótesis H1 y H5.
5. Comparar el fact-checking con retraso, el silenciamiento y el prebunking, según las hipótesis H2, H3 y H4, incluyendo escenarios con igual presupuesto de nodos intervenidos.
6. Desarrollar un tablero interactivo para explorar los escenarios y sus resultados.

## 1.7 Pregunta de investigación

¿Cómo influyen la topología de la red, el origen de la noticia y el tipo y momento de intervención en el alcance y la velocidad de propagación de una noticia falsa, y qué estrategia logra reducir más el alcance por nodo intervenido?