"""Pruebas de convergence.py (V4, P2)."""
import numpy as np
import pandas as pd

from fakenews.convergence import ci_half_width, ci_vs_reps, run_convergence
from fakenews.metrics import METRIC_NAMES


def test_ci_half_width_escala_como_inverso_de_raiz_r():
    rng = np.random.default_rng(0)
    x = rng.normal(0.5, 0.1, size=100_000)
    hw = {r: np.mean([ci_half_width(rng.choice(x, r)) for _ in range(300)]) for r in (10, 40)}
    # 4 veces más réplicas -> IC ~2 veces más estrecho (t de Student añade un poco de holgura a r chico)
    assert 1.7 < hw[10] / hw[40] < 2.5


def test_ci_vs_reps_columnas_y_monotonia():
    vals = np.random.default_rng(1).normal(0.5, 0.05, size=100)
    df = ci_vs_reps(vals, rep_grid=(5, 10, 30, 100), n_draws=50)
    assert list(df.columns) == ["n_rep", "half_width", "rel_half_width"]
    assert df.half_width.is_monotonic_decreasing


def test_run_convergence_quick_escribe_formato_del_contrato(tmp_path):
    out = run_convergence(quick=True, out_dir=tmp_path / "res", fig_dir=tmp_path / "fig")
    m = pd.read_csv(tmp_path / "res" / "V4_metrics.csv")
    assert list(m.columns[:5]) == ["exp_id", "scenario", "network", "model", "n"]
    assert {"replicate", *METRIC_NAMES} <= set(m.columns)
    c = pd.read_csv(tmp_path / "res" / "V4_curves.csv")
    assert list(c.columns[:4]) == ["exp_id", "scenario", "network", "model"]
    assert {"t", "compartment", "mean", "lo", "hi"} <= set(c.columns)
    assert (tmp_path / "fig" / "fig_V4_ic_vs_replicas.png").exists()
    assert (tmp_path / "fig" / "fig_V4_variabilidad_vs_N.png").exists()
    assert set(out) == {"metrics", "curves", "ci_width", "variance"}
