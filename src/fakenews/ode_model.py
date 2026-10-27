"""Modelo determinista SEIR-D (mezcla homogénea). DUEÑA: Camila (P1).

Ecuaciones y reglas en docs/CONTRATO.md, sección 3. Debe devolver SimResult con
t = 0..t_max (paso 1 h) y pasar SimResult.check().
"""
from __future__ import annotations

from typing import Optional

from .params import Intervention, ModelParams, SimResult, MEAN_DEGREE, T_MAX


def simulate_ode(
    params: ModelParams,
    intervention: Optional[Intervention] = None,
    mean_degree: float = MEAN_DEGREE,
    t_max: int = T_MAX,
) -> SimResult:
    """Integra el SEIR-D con scipy (solve_ivp) usando beta_ode = beta * mean_degree.

    Soporta delta, silence_frac y prebunk_frac con targeting="random".
    Con targeting="degree" debe lanzar ValueError (el ODE no ve la topología).
    """
    raise NotImplementedError("P1 (Camila): implementar")


def final_size(r0: float, i0: float = 0.0, p_believe: float = 1.0) -> float:
    """Tamaño final analítico s_inf (fracción que nunca ve la noticia). P1: derivar y verificar."""
    raise NotImplementedError("P1 (Camila): implementar")
