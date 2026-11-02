"""Pruebas de sensitivity.py (E2) y de los contrastes V3. Tamaños chicos para ser rápidas."""
import numpy as np
import pandas as pd
import pytest

from fakenews.metrics import METRIC_NAMES
from fakenews.params import ModelParams
from fakenews.sensitivity import run_sensitivity
from fakenews.validation import (
    _first_crossing, beta_critical, beta_critical_meanfield, discrete_transmissibility, r_network, run_v3,
)


def test_transmisibilidad_discreta_coincide_con_montecarlo_de_la_regla():
    """T = prob. de que un difusor contagie a un vecino: se simula la regla del contrato 3.2 directamente."""
    beta, gamma, trials = 0.03, 0.1, 200_000
    rng = np.random.default_rng(0)
    q = 1 - np.exp(-beta)
    steps = rng.geometric(1 - np.exp(-gamma), size=trials)       # pasos que el difusor pasa en I
    exposed = rng.random(trials) < 1 - (1 - q) ** steps          # al menos un éxito en esos pasos
    se = np.sqrt(exposed.mean() * (1 - exposed.mean()) / trials)
    assert abs(exposed.mean() - discrete_transmissibility(beta, gamma)) < 4 * se


def test_transmisibilidad_limite_continuo():
    # con tasas pequeñas el paso de 1 h deja de importar y T -> beta/(beta+gamma)
    assert discrete_transmissibility(1e-4, 1e-3) == pytest.approx(1e-4 / (1e-4 + 1e-3), rel=2e-3)
    # con gamma = 0.1 el paso extra de recuperación sube T ~5 % respecto al límite continuo (efecto de discretización)
    cont = 0.03 / (0.03 + 0.1)
    assert 1.0 < discrete_transmissibility(0.03, 0.1) / cont < 1.10


def test_umbral_critico_es_raiz_de_r_red():
    p = ModelParams()
    k, k2 = 10.0, 110.0   # ER: <k^2> = <k>^2 + <k>
    bc = beta_critical(p, k, k2)
    assert r_network(ModelParams(beta=bc), k, k2) == pytest.approx(1.0, abs=1e-6)


def test_mas_heterogeneidad_baja_el_umbral():
    p = ModelParams()
    assert beta_critical(p, 10.0, 300.0) < beta_critical(p, 10.0, 110.0)


def test_umbral_meanfield():
    assert beta_critical_meanfield(ModelParams()) == pytest.approx(0.1 / (0.6 * 10))


def test_primer_cruce():
    x, y = np.array([0.0, 1.0, 2.0]), np.array([0.0, 0.05, 0.25])
    assert _first_crossing(x, y, 0.10) == pytest.approx(1.25)
    assert np.isnan(_first_crossing(x, y, 0.9))


def test_e2_quick_formato_del_contrato(tmp_path):
    out = run_sensitivity(quick=True, out_dir=tmp_path / "res", fig_dir=tmp_path / "fig")
    m = pd.read_csv(tmp_path / "res" / "E2_metrics.csv")
    assert list(m.columns[:4]) == ["exp_id", "scenario", "network", "model"]
    assert {"replicate", *METRIC_NAMES} <= set(m.columns)
    assert set(m.model) == {"ode", "abm"} and set(m.exp_id) == {"E2"}
    c = pd.read_csv(tmp_path / "res" / "E2_curves.csv")
    assert {"t", "compartment", "mean", "lo", "hi"} <= set(c.columns)
    for f in ("fig_E2_mapas_beta_gamma", "fig_E2_p_believe", "fig_E2_tornado", "fig_E2_abm_vs_ode"):
        assert (tmp_path / "fig" / f"{f}.png").exists()
    # monotonía física: más beta -> mayor R0 y mayor alcance (a gamma fijo)
    g = out["grid"]
    fila = g[g.gamma == g.gamma.min()].sort_values("beta")
    assert fila.r0.is_monotonic_increasing and fila.reach_inf.is_monotonic_increasing


def test_e2_tornado_signos():
    out_dir = None  # no escribe: reutiliza la rejilla quick
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as d:
        out = run_sensitivity(quick=True, out_dir=pathlib.Path(d) / "r", fig_dir=pathlib.Path(d) / "f")
    t = out["tornado"]
    reach = t[t.metric == "reach"].set_index("param")
    assert reach.loc["beta", "rel_change_plus20"] > 0 > reach.loc["gamma", "rel_change_plus20"]
    assert reach.loc["p_believe", "rel_change_plus20"] > 0


def test_v3_quick(tmp_path):
    s = run_v3(n=500, n_rep_a=3, n_rep_b=6, beta_grid=[0.004, 0.02, 0.04], out_dir=tmp_path)
    thr = pd.read_csv(tmp_path / "V3_threshold.csv").set_index("network")
    assert thr.loc["ba", "beta_c_pred"] < thr.loc["er", "beta_c_pred"]      # BA: umbral teórico menor
    assert set(pd.read_csv(tmp_path / "V3_metrics.csv").network) == {"er", "ba", "ws"}
    cmp_ = pd.read_csv(tmp_path / "V3_comparisons.csv")
    assert set(cmp_.metric) == {"reach", "peak_I", "t_peak", "t_5pct"} and s["v3b_total"] == 8
    assert "t_5pct" in pd.read_csv(tmp_path / "V3_metrics.csv").columns
    hz = pd.read_csv(tmp_path / "V3_horizon.csv")
    assert set(hz.columns) >= {"network", "beta", "reach_corto", "reach_largo"}
    assert (hz.reach_largo >= hz.reach_corto - 0.05).all()   # un horizonte mayor no reduce el alcance (salvo ruido)
    c = pd.read_csv(tmp_path / "V3_curves.csv")
    assert list(c.columns[:4]) == ["exp_id", "scenario", "network", "model"]
