"""Pruebas de networks.py (P2)."""
import networkx as nx
import numpy as np
import pytest

from fakenews.networks import NETWORK_KINDS, build_network, degree_stats

N = 2000


@pytest.mark.parametrize("kind", ["er", "ba", "ws"])
def test_tamano_simple_y_grado_medio(kind):
    G = build_network(kind, n=N, seed=1)
    assert G.number_of_nodes() == N
    assert sorted(G.nodes) == list(range(N))
    assert not G.is_directed() and nx.number_of_selfloops(G) == 0
    assert abs(degree_stats(G)["k_mean"] - 10.0) / 10.0 < 0.05


def test_grafo_completo():
    G = build_network("complete", n=50)
    assert G.number_of_edges() == 50 * 49 // 2
    assert degree_stats(G)["k_mean"] == 49


def test_ba_tiene_hubs_y_ws_no():
    k_er = degree_stats(build_network("er", n=N, seed=1))["k_max"]
    k_ba = degree_stats(build_network("ba", n=N, seed=1))["k_max"]
    k_ws = degree_stats(build_network("ws", n=N, seed=1))["k_max"]
    assert k_ba > 2 * k_er
    assert k_ws < k_er


def test_determinismo_con_la_misma_semilla():
    a = build_network("ba", n=500, seed=7)
    b = build_network("ba", n=500, seed=7)
    c = build_network("ba", n=500, seed=8)
    assert sorted(a.edges) == sorted(b.edges)
    assert sorted(a.edges) != sorted(c.edges)


def test_degree_stats_formulas():
    G = nx.star_graph(4)  # centro con grado 4, cuatro hojas con grado 1 -> k = [4, 1, 1, 1, 1]
    st = degree_stats(G)
    assert st["k_mean"] == pytest.approx(8 / 5)
    assert st["k2_mean"] == pytest.approx((16 + 4) / 5)
    assert st["k_max"] == 4
    assert st["k2_mean"] >= st["k_mean"] ** 2


def test_tipo_desconocido():
    with pytest.raises(ValueError):
        build_network("xx")
    assert set(NETWORK_KINDS) == {"er", "ba", "ws", "complete"}
