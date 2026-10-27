"""Intervenciones contra la desinformación. DUEÑO: Juan Francisco (P3).

El ABM (Marinés) llama a plan() y aplica el resultado; esta función es el punto de
acople entre ambos módulos (ver docs/CONTRATO.md, sección 4.4).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import networkx as nx
import numpy as np

from .params import Intervention


@dataclass
class InterventionPlan:
    """Qué hacer en el ABM. Índices de nodos 0..n-1.

    t_start   paso (entero, horas) en el que se aplican silence/immunize
    silence   nodos que pasan a R en t_start sin importar su estado (cuentas baneadas/bots)
    immunize  nodos que pasan a R en t_start SOLO si están en S (prebunking)
    delta     tasa extra I -> R (1/h) a partir de t_start (fact-checking)
    """

    t_start: int = 0
    silence: np.ndarray = field(default_factory=lambda: np.array([], dtype=int))
    immunize: np.ndarray = field(default_factory=lambda: np.array([], dtype=int))
    delta: float = 0.0


def select_nodes(G: nx.Graph, frac: float, targeting: str, rng: np.random.Generator) -> np.ndarray:
    """Elige round(frac * n) nodos: al azar ("random") o los de mayor grado ("degree")."""
    raise NotImplementedError("P3 (Juan Francisco): implementar")


def plan(G: nx.Graph, intervention: Optional[Intervention], rng: np.random.Generator) -> InterventionPlan:
    """Convierte una Intervention en un InterventionPlan para el grafo G.

    Versión mínima (Checkpoint 0): sin intervención -> plan vacío; con delta -> solo delta.
    P3 debe completar silence_frac / prebunk_frac con select_nodes.
    """
    if intervention is None:
        return InterventionPlan()
    return InterventionPlan(t_start=int(np.ceil(intervention.t_start)), delta=intervention.delta)
