"""Pruebas del contrato (Checkpoint 0). Deben pasar siempre: pytest tests/test_contract.py"""
import numpy as np
import pandas as pd

from fakenews.interventions import plan
from fakenews.metrics import METRIC_NAMES, aggregate_curves, compute_metrics, metrics_table
from fakenews.mock import mock_result
from fakenews.params import Intervention, ModelParams


def test_mock_cumple_invariantes():
    for seed in range(5):
        mock_result(seed=seed).check()


def test_metricas_basicas():
    res = mock_result()
    m = compute_metrics(res)
    assert set(m) == set(METRIC_NAMES)
    assert 0 < m["peak_I"] < 1
    assert m["reach"] >= m["believers_total"] > 0
    assert 0 <= m["t_peak"] <= res.t[-1]


def test_factcheck_reduce_alcance_en_mock():
    base = compute_metrics(mock_result(seed=1))
    fc = compute_metrics(mock_result(seed=1, intervention=Intervention(name="fc", delta=0.3)))
    assert fc["reach"] < base["reach"]


def test_agregacion_formato():
    results = [mock_result(seed=s) for s in range(4)]
    curves = aggregate_curves(results, scenario="base", network="er")
    assert list(curves.columns) == ["scenario", "network", "t", "compartment", "mean", "lo", "hi"]
    assert set(curves["compartment"]) == {"S", "E", "I", "R", "cum_exposed", "cum_believers"}
    table = metrics_table(results, scenario="base", network="er")
    assert isinstance(table, pd.DataFrame) and len(table) == 4
    assert {"scenario", "network", "replicate", *METRIC_NAMES} <= set(table.columns)


def test_params_r0():
    p = ModelParams()
    assert np.isclose(p.beta_ode(10), 0.3)
    assert np.isclose(p.r0_ode(10), 1.8)


def test_plan_sin_intervencion_es_vacio():
    import networkx as nx

    pl = plan(nx.path_graph(5), None, np.random.default_rng(0))
    assert len(pl.silence) == 0 and len(pl.immunize) == 0 and pl.delta == 0.0
