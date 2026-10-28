"""Pruebas de validation.py (P1). Usan tamaños chicos para ser rápidas."""
import numpy as np
import pandas as pd
import pytest

from fakenews.ode_model import final_size
from fakenews.params import ModelParams
from fakenews.validation import (
    _complete_graph_params, _params_for_r0, discrete_meanfield, run_v1, run_v2,
)


def test_barrido_de_r0_reproduce_r0():
    base = ModelParams()
    for r0 in (0.5, 1.0, 2.5, 4.0):
        assert _params_for_r0(r0, base).r0_ode() == pytest.approx(r0)


def test_beta_grafo_completo_iguala_contagio_ode():
    p = ModelParams()
    assert _complete_graph_params(p, 1000).beta * 999 == pytest.approx(p.beta_ode())


def test_mapa_discreto_conserva_y_pasa_check():
    p = _complete_graph_params(ModelParams(), 1000)
    res = discrete_meanfield(p, 1000)
    res.check()


def test_v1_pequeno_escribe_csv_con_formato_del_contrato(tmp_path):
    errs = run_v1(n=200, n_rep=3, out_dir=tmp_path)
    assert np.isfinite(errs["rmse_I_abm_vs_ode"]) and errs["rmse_I_abm_vs_ode"] < 0.05
    m = pd.read_csv(tmp_path / "V1_metrics.csv")
    assert list(m.columns[:4]) == ["exp_id", "scenario", "network", "model"]
    assert {"abm", "ode", "discreto"} == set(m.model)
    c = pd.read_csv(tmp_path / "V1_curves.csv")
    assert list(c.columns) == ["exp_id", "scenario", "network", "model", "t", "compartment", "mean", "lo", "hi"]
    ode = c[(c.model == "ode") & (c.compartment == "I")]
    assert np.allclose(ode.lo, ode["mean"]) and np.allclose(ode.hi, ode["mean"])  # ODE: lo = hi = mean


def test_v2_umbral_y_columnas_analiticas(tmp_path):
    d = run_v2(n=200, n_rep=3, r0_grid=[0.5, 2.0], t_max=150, out_dir=tmp_path)
    lo, hi = d.iloc[0], d.iloc[1]
    assert lo.reach_abm_mean < hi.reach_abm_mean and lo.reach_ode_inf < hi.reach_ode_inf
    for row in (lo, hi):
        esperado = 1 - final_size(row.r0, ModelParams().i0, ModelParams().p_believe)
        assert row.reach_analitico == pytest.approx(esperado)
        assert row.reach_ode_inf == pytest.approx(row.reach_analitico, abs=1e-3)