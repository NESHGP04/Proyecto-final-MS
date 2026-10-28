### Prompt 1 — Implementar simulate_ode y final_size (CP1)  (27 oct 2026, Claude)
**Prompt:** Instrucciones del proyecto (protocolo + contrato + tareas de P1); la IA implementó
el ODE, final_size y tests.
**Resultado:** simulate_ode por tramos con solve_ivp (LSODA), final_size con brentq,
14 pruebas nuevas; pytest completo en verde (64).
**Evaluación:** ⚠️ parcial — el código y los tests pasan y final_size coincide con el ODE
(alcance 0.74333 vs 0.74337 con parámetros por defecto). Pero la IA afirmó sin verificar que
RK45 daba errores mayores y que t_max=2000 hacía falta; al revisarlo, RK45 da el mismo error
y el horizonte largo sí es necesario cerca de R0=1 (error 0.27 con 240 h y R0=1.2).
**Corrección/Iteración:** la IA corrigió ambas afirmaciones. La fórmula del contrato
exp(-R0(1-s)) solo vale con i0→0 y p=1; se derivó la versión completa y se verificó
contra el ODE. Falló un primer pytest por falta de entorno (venv), no del código.
**Comprensión:** 
1. Como E empieza y termina en cero, todas las personas que entraron a ese grupo terminaron saliendo para tomar una decisión. Además, sin retorno a S, quienes entraron a E son quienes dejaron de ser susceptibles. De esas personas, una proporción (p) se vuelve creyente. Al sumar los creyentes iniciales, obtenemos (i_0+p(1-i_0-s_\infty)). Esto permite calcular los creyentes acumulados a partir de la cantidad de susceptibles que queda al final.

2. Justo en (t=12), se retira el 10 % de cada grupo S, E e I, cada uno queda con el 90 % de su valor anterior. Las personas retiradas pasan a R y la población total se conserva. El alcance acumulado no disminuye porque registra las exposiciones que ya ocurrieron, silenciar a alguien no borra que antes haya visto la noticia. La intervención puede evitar nuevas exposiciones desde ese momento.

3. Al bajar (R_0) de 1 a 0.5, espero que la noticia se propague menos y que una mayor proporción de personas permanezca sin exponerse. Si final_size devuelve (s_\infty), su valor se acerca a 1. Con semillas iniciales positivas, el alcance puede ser pequeño, pero no es cero. La raíz (s=1) representa que nadie llega a exponerse y siempre existe cuando (i_0=0), si no hay nadie difundiendo la noticia, la propagación no comienza.

### Prompt 2 — V1 y V2 de validación (CP2)  (28 oct 2026, Claude)
**Prompt:** Seguir el CP2 de las instrucciones del proyecto: implementar V1 (ABM en grafo
completo vs ODE) y V2 (alcance vs R0), sin ajustar parámetros.
**Resultado:** validation.py con run_v1, run_v2, un mapa discreto como diagnóstico, figuras
y CSV en el formato del contrato; 5 pruebas nuevas; pytest completo en verde (69).
**Evaluación:** ⚠️ parcial — el código funciona y los resultados se reprodujeron
[confirma con tu corrida local]. Errores de la IA que se corrigieron: (1) las barras de las
figuras decían "IC 95 %" pero eran percentiles 2.5–97.5 % entre réplicas; (2) una primera
corrida en segundo plano murió sin guardar nada; (3) la IA dijo que sin las réplicas
apagadas la media quedaba cerca del ODE, pero solo se cumple en R0 = 1.2.
**Corrección/Iteración:** etiquetas corregidas; la hipótesis de discretización se probó con
el R0 efectivo 1/(1−e^−γ) (alcance analítico 0.7738 vs mapa discreto 0.7743); la hipótesis
de extinción estocástica se probó contando réplicas sin brote por R0.
**Comprensión:** 
1. El mapa discreto no cambia los parámetros para hacer coincidir los resultados, sino que representa las mismas reglas mediante pasos de tiempo, como el ABM. Esta diferencia tiene un efecto concreto: con pasos de una hora, un difusor permanece activo en promedio aproximadamente 10.5 horas, en lugar de las 10 horas del modelo continuo. Eso aumenta el R0 efectivo de 1.80 a aproximadamente 1.89. Por eso, que el ABM quede más cerca del mapa indica que la discretización explica parte de su diferencia con el ODE. Además, el ABM presenta variaciones aleatorias por trabajar con una población finita.

2. Con `i0 = 0.01`, el modelo comienza con un 1 % de difusores que pueden generar exposiciones incluso cuando R0 es menor que 1. Por eso, el cambio alrededor del umbral se observa gradual. Con menos semillas, el azar influye más: algunas réplicas se apagan pronto y otras alcanzan a más personas. Cerca del umbral esperaría mayor variabilidad relativa y, un poco por encima de 1, una banda de percentiles más amplia si aparecen tanto extinciones tempranas como brotes grandes.

Los datos muestran dos efectos opuestos: la extinción temprana reduce la media del ABM, mientras que la discretización puede aumentar el alcance de los brotes que logran desarrollarse. Al considerar solo las réplicas con alcance de al menos 0.1, la media supera al ODE para R0 = 1.0 y 1.1, pero queda ligeramente por debajo para R0 = 1.2. Esta separación sirve como diagnóstico para R0 ≥ 1; como el filtro selecciona los resultados de mayor alcance, la media filtrada no sustituye a la media de todas las réplicas.

3. Si se dejara `beta = beta_ode`, cada difusor podría transmitir a sus N − 1 vecinos sin compensar el número de conexiones. Con los parámetros utilizados, el R0 nominal sería aproximadamente 1800, en lugar de 1.8. Esto provocaría una propagación mucho más rápida, con un pico más temprano y una exposición de casi toda la población. El alcance seguiría limitado a 1, porque no puede exponerse más del 100 % de las personas. Dividir beta entre N − 1 permite mantener una intensidad de transmisión comparable con la del ODE.