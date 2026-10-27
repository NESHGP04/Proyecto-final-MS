"""Contrato compartido: parámetros del modelo SEIR-D y estructuras de resultados.

Este archivo es del CONTRATO. No lo modifiques sin avisar al grupo
(ver docs/CONTRATO.md, sección "Cambios al contrato").

Unidad de tiempo: 1 hora. Todas las tasas están en 1/hora.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

import numpy as np

# Constantes globales del proyecto (usar siempre estas, no números sueltos)
SEED0 = 2026          # semilla base reproducible
N_DEFAULT = 5000      # nodos por red
MEAN_DEGREE = 10.0    # grado medio <k> de todas las redes (comparación justa)
T_MAX = 240           # horizonte de simulación (10 días)
N_REP = 30            # réplicas Monte Carlo por escenario

# Índices de estado en el ABM (arreglo int8)
S, E, I, R = 0, 1, 2, 3


@dataclass(frozen=True)
class ModelParams:
    """Parámetros del modelo SEIR-D (valores por defecto: ilustrativos, a calibrar)."""

    beta: float = 0.03    # prob. (tasa) por hora de que un vecino difusor exponga a un susceptible
    sigma: float = 0.5    # tasa de decisión E -> (I o R); decisión media = 1/sigma horas
    p_believe: float = 0.6  # prob. de que el expuesto crea y comparta (E -> I); si no, E -> R
    gamma: float = 0.1    # tasa de pérdida de interés I -> R
    omega: float = 0.0    # tasa de olvido R -> S (0 en los experimentos principales)
    i0: float = 0.01      # fracción inicial de difusores (semillas)

    def beta_ode(self, mean_degree: float = MEAN_DEGREE) -> float:
        """Tasa de contagio de campo medio: beta_ode = beta * <k>."""
        return self.beta * mean_degree

    def r0_ode(self, mean_degree: float = MEAN_DEGREE) -> float:
        """R0 de mezcla homogénea (omega=0, sin intervención): beta_ode * p / gamma."""
        return self.beta_ode(mean_degree) * self.p_believe / self.gamma


@dataclass(frozen=True)
class Intervention:
    """Intervención contra la desinformación. Todos los campos en 0 = sin intervención."""

    name: str = "sin_intervencion"
    t_start: float = 0.0        # hora a partir de la cual se activa
    delta: float = 0.0          # fact-checking: tasa extra I -> R (1/h) desde t_start
    silence_frac: float = 0.0   # fracción de nodos silenciados (pasan a R) en t_start
    prebunk_frac: float = 0.0   # fracción de nodos inmunizados (S -> R) en t_start
    targeting: str = "random"   # "random" | "degree" (aplica a silence y prebunk)


@dataclass
class SimResult:
    """Resultado de UNA corrida (ODE o ABM). Todas las series tienen igual longitud.

    t = 0, 1, ..., T_MAX (horas, paso de 1h). Las series son FRACCIONES de la
    población total N en [0, 1].
    """

    t: np.ndarray
    S: np.ndarray
    E: np.ndarray
    I: np.ndarray
    R: np.ndarray
    cum_exposed: np.ndarray    # fracción acumulada que alguna vez fue expuesta (incluye semillas)
    cum_believers: np.ndarray  # fracción acumulada que alguna vez fue difusora (incluye semillas)
    meta: Dict = field(default_factory=dict)  # modelo ("ode"/"abm"), red, escenario, semilla, params...

    def check(self, atol: float = 1e-6) -> None:
        """Valida invariantes del contrato. Lanza AssertionError si se rompen."""
        n = len(self.t)
        for name in ("S", "E", "I", "R", "cum_exposed", "cum_believers"):
            arr = getattr(self, name)
            assert len(arr) == n, f"{name}: longitud {len(arr)} != {n}"
            assert np.all(arr >= -atol) and np.all(arr <= 1 + atol), f"{name} fuera de [0,1]"
        total = self.S + self.E + self.I + self.R
        assert np.allclose(total, 1.0, atol=1e-6), "S+E+I+R debe ser 1 en todo t"
        assert np.all(np.diff(self.cum_exposed) >= -atol), "cum_exposed debe ser no decreciente"
        assert np.all(np.diff(self.cum_believers) >= -atol), "cum_believers debe ser no decreciente"
