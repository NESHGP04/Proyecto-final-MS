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
    """Elige round(frac * n) nodos sin reemplazo; desempata grados con rng.

    Se devuelven las etiquetas del grafo. Las redes del ABM usan enteros 0..n-1.
    Una selección vacía no consume números aleatorios: delta no cambia las semillas.
    """
    if not np.isfinite(frac) or not 0 <= frac <= 1:
        raise ValueError("frac debe estar entre 0 y 1")
    if targeting not in ("random", "degree"):
        raise ValueError("targeting debe ser 'random' o 'degree'")
    nodes = np.asarray(list(G.nodes()))
    count = round(frac * len(nodes))
    if count == 0:
        return np.array([], dtype=nodes.dtype if len(nodes) else int)
    if targeting == "random":
        return nodes[rng.choice(len(nodes), size=count, replace=False)]
    # Barajar antes de ordenar evita favorecer etiquetas pequeñas cuando hay empates.
    shuffled = rng.permutation(len(nodes))
    degrees = np.asarray([G.degree(node) for node in nodes])
    order = np.argsort(-degrees[shuffled], kind="stable")
    return nodes[shuffled[order[:count]]]


def plan(G: nx.Graph, intervention: Optional[Intervention], rng: np.random.Generator) -> InterventionPlan:
    """Convierte una Intervention en un InterventionPlan para el grafo G.

    Silencio y prebunking se seleccionan independientemente sobre el grafo original;
    pueden coincidir. El ABM decide qué seleccionados siguen susceptibles al aplicarlo.
    """
    if intervention is None:
        return InterventionPlan()
    if not np.isfinite(intervention.t_start) or intervention.t_start < 0:
        raise ValueError("t_start debe ser finito y no negativo")
    if not np.isfinite(intervention.delta) or intervention.delta < 0:
        raise ValueError("delta debe ser finito y no negativo")
    return InterventionPlan(
        t_start=int(np.ceil(intervention.t_start)),
        silence=select_nodes(G, intervention.silence_frac, intervention.targeting, rng),
        immunize=select_nodes(G, intervention.prebunk_frac, intervention.targeting, rng),
        delta=intervention.delta,
    )
