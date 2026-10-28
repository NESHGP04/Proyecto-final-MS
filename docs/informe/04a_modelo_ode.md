# 4a. Modelo ODE: SEIR-D (BORRADOR CP1)
## Ecuaciones y supuestos

Con $b = \beta\langle k\rangle$ (campo medio) y la tasa de fact-checking

$$
\delta(t)=\begin{cases}\delta & t \ge t_{\text{start}}\\ 0 & t < t_{\text{start}}\end{cases}
$$

el modelo SEIR-D es

$$
\begin{aligned}
\frac{dS}{dt} &= -b\,S\,I + \omega R \\
\frac{dE}{dt} &= b\,S\,I - \sigma E \\
\frac{dI}{dt} &= p\,\sigma E - \big(\gamma + \delta(t)\big) I \\
\frac{dR}{dt} &= (1-p)\,\sigma E + \big(\gamma + \delta(t)\big) I - \omega R \\
\frac{d\,\mathrm{CumExp}}{dt} &= b\,S\,I \\
\frac{d\,\mathrm{CumBel}}{dt} &= p\,\sigma E
\end{aligned}
$$

con condiciones iniciales

$$
S(0)=1-i_0,\quad E(0)=0,\quad I(0)=i_0,\quad R(0)=0,\quad \mathrm{CumExp}(0)=\mathrm{CumBel}(0)=i_0,
$$

y la conservación $S+E+I+R=1$.

**Supuestos:** mezcla homogénea (sin topología), población cerrada, parámetros constantes en el tiempo, unidad de tiempo de 1 hora.

## Derivación del R0 (matriz de siguiente generación)

Se toman los estados infectados x = (E, I) en el equilibrio libre de noticia (S = 1, ω = 0), con b = β⟨k⟩.

- Nuevas "infecciones" (entradas a E): solo por contacto con I → F = [[0, b], [0, 0]]
- Transiciones entre estados infectados:
  - E sale a tasa σ; I recibe una fracción p de esas salidas y sale a tasa γ
  - V = [[σ, 0], [−pσ, γ]]

Inversa:
$$
F=\begin{pmatrix}0 & b\\ 0 & 0\end{pmatrix},\qquad
V=\begin{pmatrix}\sigma & 0\\ -p\sigma & \gamma\end{pmatrix},\qquad
V^{-1}=\frac{1}{\sigma\gamma}\begin{pmatrix}\gamma & 0\\ p\sigma & \sigma\end{pmatrix}
$$

Matriz de siguiente generación:
$$
F\,V^{-1}=\begin{pmatrix}\dfrac{b\,p}{\gamma} & \dfrac{b}{\gamma}\\ 0 & 0\end{pmatrix}
\quad\Longrightarrow\quad
R_0=\frac{b\,p}{\gamma}
$$

Es triangular: sus valores propios son b·p/γ y 0, y el radio espectral es

**R0 = b·p / γ**

que coincide con el contrato 3.1 y con `ModelParams.r0_ode()`.

### Lectura intuitiva (para la pregunta "¿por qué b·p/γ y no b/γ?")
Un difusor contagia a tasa b mientras dure su fase activa, en promedio 1/γ horas: genera b/γ expuestos. Pero solo una fracción p de los expuestos cree y se vuelve difusor; los demás pasan a R. Por eso la "descendencia" en difusores es (b/γ)·p. El tiempo de decisión 1/σ no entra en R0: retrasa la propagación (afecta la velocidad), no cuántos difusores nuevos produce cada uno.

### Con fact-checking
Con `delta` activo, la salida de I es γ + δ, así que R0(t ≥ t_start) = b·p/(γ+δ). [VERIFICAR contra el ODE: el umbral con δ debería estar en b·p = γ+δ.]

## Tamaño final
Ecuación (ω = 0, sin intervención):

$$
s_\infty=(1-i_0)\exp\!\Big(-R_0(1-s_\infty)-R_0\,i_0\,\frac{1-p}{p}\Big),
\qquad \text{alcance}=1-s_\infty
$$

Con i0 → 0 y p = 1 se reduce a la clásica s∞ = exp(−R0(1 − s∞)).
Alcance = 1 − s∞. Verificado contra el ODE en `tests/test_ode.py`.
Hallazgo: cerca de R0 = 1 el horizonte de 240 h es corto (con R0 = 1.2 el ODE a 240 h queda 0.27 por debajo del analítico).

La derivación se realiza sin intervención, con ω = 0 y sin un término adicional de salida de I asociado a δ. Se consideran las siguientes condiciones iniciales y finales:

$$
S(0)=1-i_0,\qquad E(0)=0,\qquad I(0)=i_0,
\qquad E(\infty)=I(\infty)=0.
$$

Como el grupo de expuestos comienza y termina vacío, todas las personas que ingresan a E terminan saliendo para tomar una decisión. Al integrar su ecuación:

$$
E'=bSI-\sigma E,
$$

se obtiene:

$$
E(\infty)-E(0)
=
\int_0^\infty bSI\,dt-\int_0^\infty \sigma E\,dt
=
0.
$$

Por lo tanto:

$$
\int_0^\infty \sigma E\,dt
=
\int_0^\infty bSI\,dt.
$$

Además, como no hay olvido ni intervención, las personas que ingresan a E son las mismas que salen de S. Integrando la ecuación de susceptibles:

$$
S'=-bSI,
$$

resulta:

$$
\int_0^\infty bSI\,dt
=
S(0)-S(\infty)
=
(1-i_0)-s_\infty.
$$

Así, el total de personas que pasan por la decisión es:

$$
\int_0^\infty \sigma E\,dt
=
1-i_0-s_\infty.
$$

Una proporción p de estas personas se convierte en creyente. Al sumar los creyentes iniciales, el total acumulado es:

$$
\mathrm{CumBel}_\infty
=
i_0+p(1-i_0-s_\infty).
$$

Esta igualdad permite relacionar los creyentes acumulados con la proporción final de susceptibles. Luego, al integrar:

$$
I'=p\sigma E-\gamma I,
$$

usando las condiciones inicial y final de I, se obtiene:

$$
-i_0
=
p\int_0^\infty \sigma E\,dt
-
\gamma\int_0^\infty I\,dt.
$$

Al reorganizar:

$$
\gamma\int_0^\infty I\,dt
=
i_0+p\int_0^\infty \sigma E\,dt
=
\mathrm{CumBel}_\infty.
$$

Por otra parte, la ecuación de S permite escribir:

$$
\frac{d\ln S}{dt}=-bI.
$$

Al integrar y sustituir la relación anterior:

$$
\ln\left(\frac{s_\infty}{1-i_0}\right)
=
-b\int_0^\infty I\,dt
=
-\frac{b}{\gamma}\,\mathrm{CumBel}_\infty.
$$

Como el número reproductivo se define mediante:

$$
R_0=\frac{bp}{\gamma},
$$

para p > 0 se tiene:

$$
\frac{b}{\gamma}=\frac{R_0}{p}.
$$

Sustituyendo la expresión de los creyentes acumulados y distribuyendo los términos:

$$
\begin{aligned}
\ln\left(\frac{s_\infty}{1-i_0}\right)
&=-\frac{R_0}{p}\left[i_0+p(1-i_0-s_\infty)\right]\\
&=-\frac{R_0i_0}{p}-R_0(1-i_0-s_\infty)\\
&=-R_0(1-s_\infty)+R_0i_0-\frac{R_0i_0}{p}\\
&=-R_0(1-s_\infty)-R_0i_0\frac{1-p}{p}.
\end{aligned}
$$

Finalmente, al aplicar la exponencial y multiplicar por la proporción inicial de susceptibles, se obtiene:

$$
\boxed{
s_\infty
=
(1-i_0)\exp\left[
-R_0(1-s_\infty)
-R_0i_0\frac{1-p}{p}
\right]
}
$$

Esta ecuación es implícita porque la proporción final de susceptibles aparece en ambos lados. Para resolverla numéricamente, se puede buscar la raíz de la siguiente función mediante `scipy.optimize.brentq`:

$$
f(s)
=
s-(1-i_0)\exp\left[
-R_0(1-s)-R_0i_0\frac{1-p}{p}
\right].
$$

[VERIFICAR] Confirmar cómo aparece δ en las ecuaciones del ODE, que `final_size` utiliza `scipy.optimize.brentq` y que `tests/test_ode.py` comprueba la concordancia entre la solución numérica del ODE y esta ecuación.
