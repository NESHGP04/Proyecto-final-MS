"""Generadores de redes sociales sintéticas. DUEÑA: Marinés (P2).

Todas las redes comparten N y grado medio <k> (MEAN_DEGREE) para una comparación justa.
"""
from __future__ import annotations

from typing import Dict

import networkx as nx
import numpy as np

from .params import MEAN_DEGREE, N_DEFAULT

NETWORK_KINDS = ("er", "ba", "ws", "complete")  # Erdős-Rényi, Barabási-Albert, Watts-Strogatz, completa

WS_REWIRING = 0.1  # probabilidad de recableado de Watts-Strogatz (mundo pequeño con agrupamiento alto)


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
    if kind == "er":
        # G(n, p): cada arista existe con prob. p; <k> = p·(n-1)
        return nx.fast_gnp_random_graph(n, mean_degree / (n - 1), seed=seed)
    if kind == "ba":
        # cada nodo nuevo se une a m nodos por conexión preferencial; <k> ≈ 2m
        return nx.barabasi_albert_graph(n, max(1, round(mean_degree / 2)), seed=seed)
    if kind == "ws":
        # anillo con k vecinos (k par) y recableado con prob. WS_REWIRING; <k> = k exacto
        k = 2 * max(1, round(mean_degree / 2))
        return nx.watts_strogatz_graph(n, k, WS_REWIRING, seed=seed)
    if kind == "complete":
        return nx.complete_graph(n)
    raise ValueError(f"Tipo de red desconocido: {kind!r}. Opciones: {NETWORK_KINDS}")


def degree_stats(G: nx.Graph) -> Dict[str, float]:
    """{'k_mean', 'k2_mean', 'k_max'}: usado por Camila para R0 en redes."""
    k = np.fromiter((d for _, d in G.degree()), dtype=float, count=G.number_of_nodes())
    return {
        "k_mean": float(k.mean()),
        "k2_mean": float((k**2).mean()),
        "k_max": float(k.max()),
    }
