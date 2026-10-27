"""Datos de prueba (MOCK) para desarrollar en paralelo antes de que existan ODE/ABM reales.

NO usar en resultados, figuras ni documento finales. Sirve para que el dashboard,
los experimentos y las figuras puedan programarse desde el día 1 contra el contrato.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from .params import Intervention, ModelParams, SimResult, T_MAX


def mock_result(
    params: Optional[ModelParams] = None,
    intervention: Optional[Intervention] = None,
    seed: int = 0,
    t_max: int = T_MAX,
    mean_degree: float = 10.0,
) -> SimResult:
    """Euler grueso del SEIR-D con ruido multiplicativo. Cumple SimResult.check()."""
    params = params or ModelParams()
    rng = np.random.default_rng(seed)
    b = params.beta_ode(mean_degree) * rng.uniform(0.9, 1.1)
    s, e, i, r = 1 - params.i0, 0.0, params.i0, 0.0
    cum_e, cum_b = params.i0, params.i0
    out = {k: [] for k in ("S", "E", "I", "R", "cum_exposed", "cum_believers")}
    dt = 0.1
    for step in range(t_max * 10 + 1):
        t = step * dt
        if step % 10 == 0:
            for k, v in zip(out, (s, e, i, r, cum_e, cum_b)):
                out[k].append(v)
        delta = 0.0
        if intervention and t >= intervention.t_start:
            delta = intervention.delta
        new_e = b * s * i * dt
        dec = params.sigma * e * dt
        rec = (params.gamma + delta) * i * dt
        s, e, i, r = s - new_e, e + new_e - dec, i + params.p_believe * dec - rec, r + (1 - params.p_believe) * dec + rec
        cum_e += new_e
        cum_b += params.p_believe * dec
    res = SimResult(
        t=np.arange(t_max + 1, dtype=float),
        **{k: np.clip(np.array(v), 0, 1) for k, v in out.items()},
        meta={"model": "mock", "seed": seed},
    )
    return res
