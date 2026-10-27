"""Pruebas del modelo ODE (P1). Ejecutar: pytest tests/test_ode.py"""
import numpy as np
import pytest

from fakenews.ode_model import final_size, simulate_ode
from fakenews.params import Intervention, ModelParams


def test_conservacion_y_check():
    res = simulate_ode(ModelParams())
    res.check()
    assert np.allclose(res.S + res.E + res.I + res.R, 1.0, atol=1e-9)
    assert len(res.t) == 241 and res.meta["model"] == "ode" and res.meta["network"] == "mean_field"


def test_conservacion_con_omega_e_intervencion():
    iv = Intervention(t_start=12, delta=0.2, silence_frac=0.05, prebunk_frac=0.1)
    res = simulate_ode(ModelParams(omega=0.02), iv)
    assert np.allclose(res.S + res.E + res.I + res.R, 1.0, atol=1e-9)


def test_bajo_umbral_no_hay_brote():
    p = ModelParams(beta=0.01)           # R0 = 0.6
    assert p.r0_ode() < 1
    res = simulate_ode(p)
    assert res.I.max() < 2 * p.i0 and res.I[-1] < 1e-4
    assert res.cum_exposed[-1] < 0.05


def test_sobre_umbral_hay_brote():
    assert simulate_ode(ModelParams()).cum_exposed[-1] > 0.5   # R0 = 1.8


@pytest.mark.parametrize("beta", [0.02, 0.03, 0.06])
@pytest.mark.parametrize("p_b", [0.3, 0.6, 0.9])
@pytest.mark.parametrize("i0", [1e-4, 0.01])
def test_alcance_ode_coincide_con_tamano_final(beta, p_b, i0):
    params = ModelParams(beta=beta, p_believe=p_b, i0=i0)
    res = simulate_ode(params, t_max=2000)  # horizonte largo: R0 cercano a 1 converge lento
    s_inf = final_size(params.r0_ode(), i0=i0, p_believe=p_b)
    assert res.cum_exposed[-1] == pytest.approx(1 - s_inf, abs=1e-3)


def test_final_size_casos_limite():
    assert final_size(0.5) == 1.0 and final_size(1.0) == 1.0
    s = final_size(2.0)
    assert s == pytest.approx(np.exp(-2.0 * (1 - s)), abs=1e-10)  # ecuación clásica
    assert final_size(4.0) < final_size(2.0)


def test_mas_delta_menor_alcance():
    reach = [simulate_ode(ModelParams(), Intervention(t_start=12, delta=d)).cum_exposed[-1]
             for d in (0.0, 0.05, 0.1, 0.2, 0.4)]
    assert all(a > b for a, b in zip(reach, reach[1:]))


def test_t_start_mayor_mayor_alcance():
    reach = [simulate_ode(ModelParams(), Intervention(t_start=t, delta=0.2)).cum_exposed[-1]
             for t in (0, 6, 12, 24, 48)]
    assert all(a < b for a, b in zip(reach, reach[1:]))


def test_salto_prebunk_y_silencio():
    p = ModelParams()
    base = simulate_ode(p)
    pre = simulate_ode(p, Intervention(t_start=0, prebunk_frac=0.4))
    assert pre.R[0] == pytest.approx(0.4 * (1 - p.i0), abs=1e-9)
    assert pre.cum_exposed[-1] < base.cum_exposed[-1]
    sil = simulate_ode(p, Intervention(t_start=12, silence_frac=0.1))
    assert sil.cum_exposed[-1] < base.cum_exposed[-1]
    no_sil = simulate_ode(p)
    assert sil.I[12] == pytest.approx(0.9 * no_sil.I[12], rel=1e-6)


def test_targeting_degree_lanza_error():
    with pytest.raises(ValueError, match="topolog"):
        simulate_ode(ModelParams(), Intervention(silence_frac=0.05, targeting="degree"))
    with pytest.raises(ValueError):
        simulate_ode(ModelParams(), Intervention(prebunk_frac=0.1, targeting="degree"))