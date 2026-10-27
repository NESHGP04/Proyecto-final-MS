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