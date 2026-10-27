"""Pruebas de la capa de datos del dashboard (app/data.py). DUEÑO: Ernesto (P4).

Los CSV se inventan en tmp_path con mock_result: solo prueban el cargador, no son resultados.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import data  # noqa: E402
from fakenews.metrics import aggregate_curves, metrics_table  # noqa: E402
from fakenews.mock import mock_result  # noqa: E402
from fakenews.params import ModelParams  # noqa: E402


def _write_exp(d: Path, exp_id: str, scenario: str = "sin_intervencion", n_rep: int = 3) -> None:
    res = [mock_result(seed=s) for s in range(n_rep)]
    meta = dict(exp_id=exp_id, scenario=scenario, network="er", model="abm")
    metrics_table(res, **meta).to_csv(d / f"{exp_id}_metrics.csv", index=False)
    aggregate_curves(res, **meta).to_csv(d / f"{exp_id}_curves.csv", index=False)


def test_cargadores_formato_contrato(tmp_path):
    _write_exp(tmp_path, "E1")
    m = data.load_metrics("E1", tmp_path)
    c = data.load_curves("E1", tmp_path)
    assert set(data.METRICS_COLS) <= set(m.columns) and len(m) == 3
    assert list(c.columns) == data.CURVES_COLS
    assert set(c["compartment"]) == {"S", "E", "I", "R", "cum_exposed", "cum_believers"}


def test_list_experiments_exige_ambos_csv(tmp_path):
    _write_exp(tmp_path, "E1")
    _write_exp(tmp_path, "E3")
    (tmp_path / "E3_curves.csv").unlink()
    assert data.list_experiments(tmp_path) == ["E1"]
    assert data.list_experiments(tmp_path / "no_existe") == []


def test_columna_faltante_da_error(tmp_path):
    _write_exp(tmp_path, "E1")
    m = pd.read_csv(tmp_path / "E1_metrics.csv").drop(columns="reach")
    m.to_csv(tmp_path / "E1_metrics.csv", index=False)
    with pytest.raises(ValueError, match="reach"):
        data.load_metrics("E1", tmp_path)


def test_cache_se_invalida_si_cambia_el_csv(tmp_path):
    _write_exp(tmp_path, "E1", scenario="viejo")
    assert set(data.load_metrics("E1", tmp_path)["scenario"]) == {"viejo"}
    path = tmp_path / "E1_metrics.csv"
    old_ns = path.stat().st_mtime_ns
    _write_exp(tmp_path, "E1", scenario="nuevo")
    # en sistemas de archivos con resolución gruesa forzamos un mtime distinto
    os.utime(path, ns=(old_ns + 10**9, old_ns + 10**9))
    assert set(data.load_metrics("E1", tmp_path)["scenario"]) == {"nuevo"}


def test_reach_summary_ic():
    abm = pd.DataFrame({"scenario": "base", "network": "er", "model": "abm", "reach": [0.4, 0.5, 0.6]})
    ode = pd.DataFrame({"scenario": "base", "network": "mean_field", "model": "ode", "reach": [0.55]})
    s = data.reach_summary(pd.concat([abm, ode])).set_index("model")
    assert s.loc["abm", "lo"] < s.loc["abm", "mean"] < s.loc["abm", "hi"]
    assert np.isclose(s.loc["abm", "mean"], 0.5) and s.loc["abm", "n"] == 3
    assert s.loc["ode", "lo"] == s.loc["ode", "mean"] == s.loc["ode", "hi"] == 0.55


def test_make_intervention():
    assert data.make_intervention("ninguna", 12, 0.2) is None
    fc = data.make_intervention("fact-checking", 12, 0.2)
    assert fc.delta == 0.2 and fc.t_start == 12 and fc.name == "factcheck_t12_d0.2"
    sil = data.make_intervention("silenciar", 12, 0.05, "degree")
    assert sil.silence_frac == 0.05 and sil.targeting == "degree" and sil.name == "silencio_deg_5pct"
    pre = data.make_intervention("prebunking", 0, 0.2, "random")
    assert pre.prebunk_frac == 0.2 and pre.delta == 0 and pre.name == "prebunk_rand_20pct"
    with pytest.raises(ValueError):
        data.make_intervention("otra", 0, 0.1)


def _sim(**kw):
    args = dict(kind="er", n=500, params=vars(ModelParams()).copy(), intervention=None,
                seed_strategy="random", n_rep=5, use_mock=True)
    args.update(kw)
    return data.simulate.__wrapped__(**args)  # sin caché de Streamlit


def test_simulate_mock_formato():
    sim = _sim()
    assert sim["sources"] == {"abm": "demo", "ode": "demo"}
    assert len(sim["abm_metrics"]) == 5
    assert list(sim["abm_curves"].columns) == ["scenario", "network", "model", "t", "compartment", "mean", "lo", "hi"]
    ode = sim["ode_curves"]
    assert set(ode["network"]) == {"mean_field"} and np.allclose(ode["lo"], ode["hi"])


def test_simulate_degree_sin_ode():
    iv = vars(data.make_intervention("silenciar", 12, 0.05, "degree")).copy()
    sim = _sim(intervention=iv)
    assert sim["sources"]["ode"] == "n/a" and sim["ode_curves"] is None


def test_simulate_respaldo_si_no_hay_modulos_reales(monkeypatch):
    def no_existe(*a, **k):
        raise NotImplementedError

    monkeypatch.setattr(data.abm, "run_replicates", no_existe)
    monkeypatch.setattr(data.ode_model, "simulate_ode", no_existe)
    sim = _sim(use_mock=False)
    assert sim["sources"] == {"abm": "demo", "ode": "demo"}
    assert len(sim["abm_metrics"]) == 5


def test_demo_experiment():
    metrics, curves = data.demo_experiment.__wrapped__()
    assert set(data.METRICS_COLS) <= set(metrics.columns)
    assert list(curves.columns) == data.CURVES_COLS
    assert metrics["scenario"].nunique() == 3
