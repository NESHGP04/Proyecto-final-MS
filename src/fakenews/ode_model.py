"""Modelo determinista SEIR-D (mezcla homogénea). DUEÑA: Camila (P1).

Ecuaciones y reglas en docs/CONTRATO.md, sección 3. Devuelve SimResult con
t = 0..t_max (paso 1 h) y pasa SimResult.check().
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Optional

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

from .params import Intervention, ModelParams, SimResult, MEAN_DEGREE, T_MAX


def _rhs(t, y, b, sigma, p, gamma_eff, omega):
    """Lado derecho del SEIR-D (contrato 3.1). `gamma_eff` = gamma + delta(t) en el tramo."""
    S, E, I, R, _, _ = y
    inf = b * S * I          # nuevas exposiciones por hora
    dec = sigma * E          # decisiones por hora
    rec = gamma_eff * I      # I -> R por hora
    return [
        -inf + omega * R,
        inf - dec,
        p * dec - rec,
        (1 - p) * dec + rec - omega * R,
        inf,                 # alcance acumulado
        p * dec,             # creyentes acumulados
    ]


def _apply_jump(y: np.ndarray, iv: Intervention) -> np.ndarray:
    """Salto puntual en t_start (contrato 3.1). Orden elegido: prebunk y luego silencio.

    El contrato no fija el orden si ambos están activos; con prebunk primero, el silencio
    actúa sobre una S ya reducida. Los acumulados no cambian (son historia, no estado).
    """
    y = y.copy()
    if iv.prebunk_frac > 0:
        moved = iv.prebunk_frac * y[0]
        y[0] -= moved
        y[3] += moved
    if iv.silence_frac > 0:
        keep = 1.0 - iv.silence_frac
        removed = (1.0 - keep) * (y[0] + y[1] + y[2])
        y[0:3] *= keep
        y[3] += removed
    return y


def simulate_ode(
    params: ModelParams,
    intervention: Optional[Intervention] = None,
    mean_degree: float = MEAN_DEGREE,
    t_max: int = T_MAX,
) -> SimResult:
    """Integra el SEIR-D con scipy (solve_ivp) usando beta_ode = beta * mean_degree.

    Soporta delta, silence_frac y prebunk_frac con targeting="random".
    Con targeting="degree" lanza ValueError (el ODE no ve la topología).

    Convención (igual que el ABM): el estado registrado en t = t_start YA incluye el salto.
    Se integra por tramos porque delta(t) y los saltos son discontinuos en t_start.
    """
    iv = intervention or Intervention()
    if iv.targeting == "degree" and (iv.silence_frac > 0 or iv.prebunk_frac > 0):
        raise ValueError(
            "El ODE usa mezcla homogénea y no ve la topología: targeting='degree' solo se "
            "puede evaluar con el ABM (fakenews.abm). Usa targeting='random'."
        )
    if iv.targeting not in ("random", "degree"):
        raise ValueError(f"targeting desconocido: {iv.targeting!r}")

    b = params.beta_ode(mean_degree)
    args_base = (b, params.sigma, params.p_believe, params.omega)
    y0 = np.array([1 - params.i0, 0.0, params.i0, 0.0, params.i0, params.i0])
    ts = np.arange(t_max + 1, dtype=float)
    out = np.zeros((t_max + 1, 6))

    def integrate(y_ini, t0, t1, t_eval, gamma_eff):
        sol = solve_ivp(
            _rhs, (t0, t1), y_ini, t_eval=t_eval,
            args=args_base[:3] + (gamma_eff, params.omega),
            method="LSODA", rtol=1e-10, atol=1e-12,
        )
        if not sol.success:
            raise RuntimeError(f"solve_ivp falló: {sol.message}")
        return sol.y.T

    has_iv = iv.delta > 0 or iv.silence_frac > 0 or iv.prebunk_frac > 0
    ts_start = float(iv.t_start)
    if not has_iv or ts_start > t_max:
        out[:] = integrate(y0, 0.0, float(t_max), ts, params.gamma)
    elif ts_start <= 0:
        y_start = _apply_jump(y0, iv)
        out[:] = integrate(y_start, 0.0, float(t_max), ts, params.gamma + iv.delta)
    else:
        # Tramo 1: sin intervención, hasta t_start.
        pre = ts[ts < ts_start]
        ev1 = np.append(pre, ts_start)
        seg1 = integrate(y0, 0.0, ts_start, ev1, params.gamma)
        out[: len(pre)] = seg1[:-1]
        y_start = _apply_jump(seg1[-1], iv)
        # Tramo 2: desde t_start con delta activo; si t_start es entero, ese punto ya incluye el salto.
        post = ts[ts >= ts_start]
        ev2 = post if post.size and post[0] == ts_start else np.append(ts_start, post)
        seg2 = integrate(y_start, ts_start, float(t_max), ev2, params.gamma + iv.delta)
        out[len(pre):] = seg2 if ev2.size == post.size else seg2[1:]

    out[:, :4] = np.clip(out[:, :4], 0.0, 1.0)  # ruido numérico ~1e-16 puede dar negativos mínimos
    res = SimResult(
        t=ts, S=out[:, 0], E=out[:, 1], I=out[:, 2], R=out[:, 3],
        cum_exposed=out[:, 4], cum_believers=out[:, 5],
        meta={
            "model": "ode", "network": "mean_field", "mean_degree": mean_degree,
            "params": asdict(params), "intervention": asdict(iv) if has_iv else None,
        },
    )
    res.check()
    return res


def final_size(r0: float, i0: float = 0.0, p_believe: float = 1.0) -> float:
    """Tamaño final analítico s_inf = fracción que NUNCA ve la noticia (omega=0, sin intervención).

    Derivación (b = beta_ode, R0 = b·p/gamma). Integrando las ecuaciones entre 0 e infinito:
      - exposiciones: ∫b·S·I dt = (1 - i0) - s_inf  (E(0)=E(inf)=0  =>  ∫sigma·E = eso mismo)
      - creyentes:    Bel_inf = i0 + p·(1 - i0 - s_inf)
      - I(inf)=0:     gamma·∫I dt = Bel_inf
      - d ln S/dt = -b·I  =>  ln(s_inf/(1-i0)) = -(b/gamma)·Bel_inf
    Sustituyendo b/gamma = R0/p queda
      s_inf = (1-i0)·exp( -R0·(1 - s_inf) - R0·i0·(1-p)/p ),
    que con i0 -> 0 es la clásica s = exp(-R0(1-s)) y se resuelve con brentq.
    El alcance (reach del contrato) es 1 - s_inf.
    """
    if r0 < 0 or not (0 <= i0 < 1) or not (0 < p_believe <= 1):
        raise ValueError("Se requiere r0>=0, 0<=i0<1 y 0<p_believe<=1")
    c = r0 * i0 * (1.0 - p_believe) / p_believe

    def g(s: float) -> float:
        return s - (1.0 - i0) * np.exp(-r0 * (1.0 - s) - c)

    if i0 == 0.0:
        if r0 <= 1.0:
            return 1.0               # bajo el umbral no hay brote (la raíz s=1 es la única)
        return float(brentq(g, 0.0, 1.0 / r0, xtol=1e-14))  # s_inf < 1/R0: excluye la raíz trivial s=1
    return float(brentq(g, 0.0, 1.0 - i0, xtol=1e-14))     # g(0)<0 y g(1-i0)>0: la raíz está atrapada
