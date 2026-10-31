"""Catálogo, formatos, estadística y pipeline P3 con backends mock y real."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from fakenews import experiments as ex
from fakenews.figures import generate_figures
from fakenews.params import SEED0


def test_catalogo_cumple_rejillas_del_contrato():
    assert set(ex.EXPERIMENTS) == {"E1", "E3", "E4", "E5", "E6", "E7"}
    assert {s.network for s in ex.EXPERIMENTS["E1"]} == {"er", "ba", "ws", "mean_field"}
    e3 = ex.EXPERIMENTS["E3"]
    for net in ("er", "ba", "mean_field"):
        assert {(s.intervention.t_start, s.intervention.delta) for s in e3 if s.network == net and s.intervention} == {
            (t, d) for t in (0, 6, 12, 24, 48) for d in (0.05, 0.1, 0.2, 0.4)
        }
    for eid, fractions, field, times, networks in (
        ("E4", (0.01, 0.02, 0.05, 0.1), "silence_frac", (12,), ("er", "ba", "ws")),
        ("E5", (0.05, 0.1, 0.2, 0.4), "prebunk_frac", (0, 12), ("er", "ba")),
    ):
        actual = {(s.network, getattr(s.intervention, field), s.intervention.targeting, s.intervention.t_start)
                  for s in ex.EXPERIMENTS[eid] if s.intervention}
        assert actual == {(n, f, target, t) for n in networks for f in fractions
                          for target in ("random", "degree") for t in times}
    assert {(s.network, s.seed_strategy) for s in ex.EXPERIMENTS["E6"]} == {
        (net, strategy) for net in ("er", "ba", "ws") for strategy in ("random", "hub")
    }
    for scenario in ex.EXPERIMENTS["E7"]:
        if scenario.intervention:
            iv = scenario.intervention
            assert iv.t_start == 12 and iv.prebunk_frac + iv.silence_frac == 0.05


def test_csv_mock_y_aislamiento_de_finales(tmp_path, monkeypatch):
    monkeypatch.setattr(ex, "RESULTS_DIR", tmp_path)
    ex.run_experiment("E3", quick=True, backend="mock")
    directory = tmp_path / "mock_quick"
    assert not (tmp_path / "E3_metrics.csv").exists()
    metrics = pd.read_csv(directory / "E3_metrics.csv")
    curves = pd.read_csv(directory / "E3_curves.csv")
    assert list(metrics.columns[:len(ex.METRICS_COLUMNS)]) == ex.METRICS_COLUMNS
    assert list(curves.columns) == ex.CURVES_COLUMNS
    assert len(metrics) == 2 * 21 * 5 + 21
    assert len(curves) == 63 * 6 * 241
    assert metrics.n.eq(1000).all()
    assert metrics.backend.eq("mock").all()
    assert set(metrics[metrics.model == "abm"].n_rep) == {5}
    assert set(metrics.seed) == set(range(SEED0, SEED0 + 5))
    assert set(curves.compartment) == {"S", "E", "I", "R", "cum_exposed", "cum_believers"}
    assert (curves.lo <= curves.hi).all()
    ode = curves[curves.model == "ode"]
    np.testing.assert_allclose(ode["mean"], ode.lo)
    np.testing.assert_allclose(ode["mean"], ode.hi)
    assert not (directory / "E3_comparisons.csv").exists()
    with pytest.raises(ValueError, match="backend real"):
        generate_figures("E3", results_dir=directory, figures_dir=tmp_path / "figs")
    original = (directory / "E3_metrics.csv").read_bytes()
    ex.run_experiment("E3", quick=True, backend="mock")
    assert original == (directory / "E3_metrics.csv").read_bytes()


@pytest.fixture
def real_pipeline(tmp_path, monkeypatch):
    # Redes pequeñas reales verifican la integración sin costear la rejilla final en pytest.
    monkeypatch.setattr(ex, "N_DEFAULT", 60)
    monkeypatch.setattr(ex, "N_REP", 4)
    monkeypatch.setattr(ex, "T_MAX", 50)
    for exp_id in ex.EXPERIMENTS:
        ex.run_experiment(exp_id, output_dir=tmp_path)
    return tmp_path


def test_pipeline_real_y_figuras_de_todo_el_catalogo(real_pipeline):
    for exp_id in ex.EXPERIMENTS:
        mt = pd.read_csv(real_pipeline / f"{exp_id}_metrics.csv")
        ct = pd.read_csv(real_pipeline / f"{exp_id}_curves.csv")
        assert mt.backend.eq("real").all()
        assert mt.n.eq(60).all()
        assert ct.t.max() == 50
        assert mt.groupby(["scenario", "network", "model", "replicate"]).size().eq(1).all()
        comparisons = pd.read_csv(real_pipeline / f"{exp_id}_comparisons.csv")
        assert comparisons.p_value.between(0, 1).all()
        assert comparisons.p_value_holm.between(0, 1).all()
        assert (comparisons.p_value_holm >= comparisons.p_value).all()
        assert comparisons.rank_biserial.between(-1, 1).all()
        assert comparisons.n_a.eq(2).all() and comparisons.n_b.eq(2).all()
        for path in generate_figures(exp_id, results_dir=real_pipeline, figures_dir=real_pipeline / "figs"):
            assert path.is_file() and path.stat().st_size > 1000
            assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    metrics = pd.read_csv(real_pipeline / "E7_metrics.csv")
    best = metrics[metrics.scenario == "mejor_factcheck"]
    e3 = pd.read_csv(real_pipeline / "E3_metrics.csv")
    for net, rows in best.groupby("network"):
        candidates = e3[(e3.network == net) & (e3.delta > 0)].groupby("scenario").reach.mean()
        assert candidates.loc[rows.source_scenario.iloc[0]] == candidates.min()
        expected = e3[(e3.network == net) & (e3.scenario == rows.source_scenario.iloc[0])]
        np.testing.assert_array_equal(rows.reach, expected.reach)


def test_media_ic_y_reduccion_emparejada():
    mean, lo, hi, count = ex.mean_ci([1, 2, 3, np.nan])
    assert mean == 2 and count == 3 and lo < mean < hi
    assert ex.mean_ci([0.5]) == (0.5, 0.5, 0.5, 1)
    mt = pd.DataFrame({"scenario": ["sin_intervencion"] * 2 + ["accion"] * 2,
                       "network": ["ba"] * 4, "model": ["abm"] * 4,
                       "replicate": [0, 1, 1, 0], "reach": [0.5, 0.8, 0.4, 0.1]})
    reduction = ex.relative_reductions(mt).set_index("replicate")
    assert reduction.loc[0, "relative_reduction"] == pytest.approx(0.8)
    assert reduction.loc[1, "relative_reduction"] == pytest.approx(0.5)
    with pytest.raises(ValueError, match="Faltan"):
        ex.relative_reductions(mt.drop(index=0))
    with pytest.raises(ValueError, match="cero"):
        ex.relative_reductions(mt.assign(reach=[0, 0.8, 0.4, 0.1]))


def test_contraste_efecto_y_no_significancia():
    low, high = np.arange(20), np.arange(40, 60)
    confirmed = ex.compare_samples(low, high, "H4", "grado vs azar", "reach", direction="less")
    assert confirmed["verdict"] == "confirma" and confirmed["rank_biserial"] == -1
    refuted = ex.compare_samples(high, low, "H4", "grado vs azar", "reach", direction="less")
    assert refuted["verdict"] == "refuta" and refuted["rank_biserial"] == 1
    same = ex.compare_samples(low, low, "H4", "grado vs azar", "reach")
    assert same["verdict"] == "evidencia_insuficiente" and same["p_value"] == 1
    constant = ex.compare_samples([0, 0], [0, 0], "H2", "pendientes", "reach")
    assert constant["p_value"] == 1 and constant["rank_biserial"] == 0


def test_e7_rechaza_dependencia_de_otro_backend(tmp_path):
    pd.DataFrame({"backend": ["mock"], "n": [1000], "n_rep": [5],
                  "delta": [0.1], "t_start": [0]}).to_csv(tmp_path / "E3_metrics.csv", index=False)
    with pytest.raises(ValueError, match="no coincide"):
        ex.run_experiment("E7", True, output_dir=tmp_path)


@pytest.mark.parametrize("exp_id,backend", [("E2", "real"), ("E3", "desconocido")])
def test_opciones_invalidas(exp_id, backend):
    with pytest.raises(ValueError):
        ex.run_experiment(exp_id, backend=backend)
