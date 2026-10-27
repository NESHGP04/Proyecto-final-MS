"""Generadores de redes sociales sintéticas. DUEÑA: Marinés (P2).

Todas las redes comparten N y grado medio <k> (MEAN_DEGREE) para una comparación justa.
"""
from __future__ import annotations

from typing import Dict

import networkx as nx

from .params import MEAN_DEGREE, N_DEFAULT

NETWORK_KINDS = ("er", "ba", "ws", "complete")  # Erdős-Rényi, Barabási-Albert, Watts-Strogatz, completa


def build_network(
    kind: str,
    n: int = N_DEFAULT,
    mean_degree: float = MEAN_DEGREE,
    seed: int = 0,
) -> nx.Graph:
    """Devuelve un grafo no dirigido, simple, con n nodos etiquetados 0..n-1.

    er: G(n, p) con p = mean_degree/(n-1) | ba: m = round(mean_degree/2)
    ws: k = round(mean_degree) (par), rewiring p = 0.1 | complete: grafo completo (solo n pequeños)
    """
    raise NotImplementedError("P2 (Marinés): implementar")


def degree_stats(G: nx.Graph) -> Dict[str, float]:
    """{'k_mean', 'k2_mean', 'k_max'}: usado por Camila para R0 en redes."""
    raise NotImplementedError("P2 (Marinés): implementar")
