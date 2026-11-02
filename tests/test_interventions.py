"""Pruebas de selección P3 y de su integración real con el ABM."""
from __future__ import annotations

import networkx as nx
import numpy as np
import pytest

from fakenews.abm import simulate_abm
from fakenews.interventions import plan, select_nodes
from fakenews.params import Intervention, ModelParams


@pytest.mark.parametrize("targeting", ["random", "degree"])
@pytest.mark.parametrize("frac", [0, 0.01, 0.25, 0.5, 1])
def test_tamano_unicidad_y_determinismo(targeting, frac):
    graph = nx.star_graph(10)
    a = select_nodes(graph, frac, targeting, np.random.default_rng(2026))
    b = select_nodes(graph, frac, targeting, np.random.default_rng(2026))
    assert len(a) == round(frac * len(graph))
    assert len(set(a)) == len(a)
    assert set(a).issubset(graph)
    np.testing.assert_array_equal(a, b)


def test_grado_elige_realmente_los_hubs():
    graph = nx.barabasi_albert_graph(100, 3, seed=8)
    selected = select_nodes(graph, 0.12, "degree", np.random.default_rng(2))
    assert sorted(graph.degree(v) for v in selected) == sorted(dict(graph.degree()).values())[-12:]


def test_desempate_no_favorece_etiquetas():
    graph = nx.cycle_graph(20)
    selections = [tuple(select_nodes(graph, 0.2, "degree", np.random.default_rng(s))) for s in range(8)]
    assert len(set(selections)) > 1
    assert any(set(selected) != {0, 1, 2, 3} for selected in selections)


@pytest.mark.parametrize("targeting", ["random", "degree"])
def test_etiquetas_del_grafo_y_grafo_vacio(targeting):
    graph = nx.Graph([("centro", "a"), ("centro", "b"), ("centro", "c")])
    selected = select_nodes(graph, 0.25, targeting, np.random.default_rng(1))
    assert set(selected).issubset(graph)
    if targeting == "degree":
        assert selected.tolist() == ["centro"]
    assert select_nodes(nx.Graph(), 1, targeting, np.random.default_rng(1)).size == 0


@pytest.mark.parametrize("frac", [-0.1, 1.1, np.nan, np.inf])
def test_rechaza_fracciones_invalidas(frac):
    with pytest.raises(ValueError, match="frac"):
        select_nodes(nx.path_graph(10), frac, "random", np.random.default_rng(1))


def test_rechaza_targeting_invalido_incluso_con_fraccion_cero():
    with pytest.raises(ValueError, match="targeting"):
        select_nodes(nx.path_graph(10), 0, "otro", np.random.default_rng(1))


def test_plan_completo_redondea_tiempo_y_conserva_delta():
    graph = nx.star_graph(19)
    iv = Intervention(t_start=12.1, delta=0.123, silence_frac=0.1, prebunk_frac=0.25, targeting="degree")
    a, b = [plan(graph, iv, np.random.default_rng(9)) for _ in range(2)]
    assert a.t_start == 13 and a.delta == iv.delta
    assert len(a.silence) == 2 and len(a.immunize) == 5
    assert 0 in a.silence and 0 in a.immunize
    np.testing.assert_array_equal(a.silence, b.silence)
    np.testing.assert_array_equal(a.immunize, b.immunize)


def test_plan_vacio_y_delta_no_consumen_rng():
    for iv in (None, Intervention(), Intervention(delta=0.1)):
        rng, control = np.random.default_rng(3), np.random.default_rng(3)
        result = plan(nx.path_graph(10), iv, rng)
        assert result.silence.size == result.immunize.size == 0
        assert rng.random() == control.random()


@pytest.mark.parametrize("field,value", [("t_start", -1), ("t_start", np.nan), ("delta", -0.1), ("delta", np.inf)])
def test_plan_rechaza_tiempo_o_tasa_invalidos(field, value):
    with pytest.raises(ValueError):
        plan(nx.path_graph(10), Intervention(**{field: value}), np.random.default_rng(1))


@pytest.mark.parametrize("kind", ["silence_frac", "prebunk_frac"])
def test_intervencion_total_en_t0_sin_plan_inyectado(kind):
    result = simulate_abm(nx.path_graph(50), ModelParams(), Intervention(**{kind: 1}), seed=3, t_max=8)
    result.check()
    assert np.all(result.R == 1)
    assert np.all(result.cum_exposed == 0)


def test_silencio_tardio_con_plan_real_se_aplica_en_ceil():
    result = simulate_abm(nx.path_graph(50), ModelParams(),
                          Intervention(t_start=2.1, silence_frac=1), seed=3, t_max=8)
    result.check()
    assert result.R[2] < 1
    assert result.R[3] == 1
    assert np.all(result.I[3:] == 0)
