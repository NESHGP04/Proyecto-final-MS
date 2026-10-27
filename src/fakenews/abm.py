"""Simulación basada en agentes sobre redes + Monte Carlo. DUEÑA: Marinés (P2).

Reglas de transición exactas en docs/CONTRATO.md, sección 3.2. Debe devolver SimResult.
"""
from __future__ import annotations

from typing import List, Optional

import networkx as nx

from .params import Intervention, ModelParams, SimResult, MEAN_DEGREE, N_DEFAULT, N_REP, SEED0, T_MAX


def simulate_abm(
    G: nx.Graph,
    params: ModelParams,
    intervention: Optional[Intervention] = None,
    seed: int = 0,
    t_max: int = T_MAX,
    seed_strategy: str = "random",
) -> SimResult:
    """Una corrida estocástica en tiempo discreto (dt = 1 h, actualización síncrona).

    seed_strategy: "random" (semillas al azar) | "hub" (semillas = nodos de mayor grado).
    La intervención se aplica con fakenews.interventions.plan(...) (ver contrato).
    """
    raise NotImplementedError("P2 (Marinés): implementar")


def run_replicates(
    kind: str,
    params: ModelParams,
    intervention: Optional[Intervention] = None,
    n: int = N_DEFAULT,
    mean_degree: float = MEAN_DEGREE,
    n_rep: int = N_REP,
    seed0: int = SEED0,
    t_max: int = T_MAX,
    seed_strategy: str = "random",
) -> List[SimResult]:
    """Monte Carlo: n_rep corridas; la réplica r usa red y dinámica con semilla seed0 + r."""
    raise NotImplementedError("P2 (Marinés): implementar")
