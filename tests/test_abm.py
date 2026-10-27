"""Pruebas de abm.py (P2). Las intervenciones de silencio/inmunización se prueban con un plan inyectado
(monkeypatch) para no depender de que interventions.plan esté completo."""
import dataclasses
import time

import numpy as np
import pytest

from fakenews import abm, interventions
from fakenews.abm import run_replicates, simulate_abm
from fakenews.interventions import InterventionPlan
from fakenews.metrics import compute_metrics
from fakenews.networks import build_network
from fakenews.params import Intervention, ModelParams

N = 1000
P = ModelParams()


@pytest.fixture(scope="module")
def graphs():
    return {k: build_network(k, n=N, seed=3) for k in ("er", "ba", "ws")}


def _inyectar_plan(monkeypatch, **kw):
    monkeypatch.setattr(interventions, "plan", lambda G, iv, rng: InterventionPlan(**kw))


@pytest.mark.parametrize("kind", ["er", "ba", "ws"])
def test_cumple_contrato(graphs, kind):
    res = simulate_abm(graphs[kind], P, seed=1)
    res.check()
    assert len(res.t) == 241
    assert res.meta["model"] == "abm"
    assert res.I[0] == pytest.approx(P.i0)


def test_hay_brote_en_er_y_ba(graphs):
    for kind in ("er", "ba"):
        res = simulate_abm(graphs[kind], P, seed=1)
        assert res.cum_exposed[-1] > 0.2
        assert res.I.max() > res.I[0]


def test_sin_contagio_si_beta_cero(graphs):
    res = simulate_abm(graphs["er"], dataclasses.replace(P, beta=0.0), seed=1)
    assert res.cum_exposed[-1] == pytest.approx(P.i0)
    assert res.I[-1] < res.I[0]  # los difusores iniciales solo se recuperan


def test_misma_semilla_mismo_resultado(graphs):
    a = simulate_abm(graphs["ba"], P, seed=5)
    b = simulate_abm(graphs["ba"], P, seed=5)
    c = simulate_abm(graphs["ba"], P, seed=6)
    assert np.array_equal(a.I, b.I) and np.array_equal(a.cum_exposed, b.cum_exposed)
    assert not np.array_equal(a.I, c.I)


def test_acumulados_no_decrecen_y_orden(graphs):
    res = simulate_abm(graphs["er"], P, seed=2)
    assert np.all(np.diff(res.cum_exposed) >= 0) and np.all(np.diff(res.cum_believers) >= 0)
    assert np.all(res.cum_exposed >= res.cum_believers - 1e-12)


def test_conservacion_con_omega(graphs):
    res = simulate_abm(graphs["er"], dataclasses.replace(P, omega=0.05), seed=2)
    res.check()


def test_factcheck_reduce_alcance(graphs):
    base = np.mean([simulate_abm(graphs["er"], P, seed=s).cum_exposed[-1] for s in range(8)])
    iv = Intervention(name="fc", delta=0.4)
    fc = np.mean([simulate_abm(graphs["er"], P, iv, seed=s).cum_exposed[-1] for s in range(8)])
    assert fc < base


def test_semillas_hub_tienen_mayor_grado(graphs):
    degrees = np.array([d for _, d in sorted(graphs["ba"].degree())], dtype=float)
    rng = np.random.default_rng(0)
    hub = abm._choose_seeds(degrees, np.ones(N, bool), 10, "hub", rng)
    rnd = abm._choose_seeds(degrees, np.ones(N, bool), 10, "random", rng)
    assert sorted(degrees[hub]) == sorted(degrees)[-10:]  # son exactamente los 10 de mayor grado
    assert degrees[hub].mean() > degrees[rnd].mean()
    for strat in ("random", "hub"):  # ambas estrategias entregan i0 inicial
        assert simulate_abm(graphs["ba"], P, seed=1, t_max=1, seed_strategy=strat).I[0] == pytest.approx(P.i0)


def test_semillas_respetan_elegibles():
    degrees = np.arange(20, dtype=float)
    eligible = np.ones(20, bool)
    eligible[15:] = False  # los 5 de mayor grado están silenciados
    s = abm._choose_seeds(degrees, eligible, 3, "hub", np.random.default_rng(0))
    assert set(s) == {12, 13, 14}
    assert len(abm._choose_seeds(degrees, eligible, 100, "random", np.random.default_rng(0))) == 15


def test_todos_silenciados_en_t0_no_hay_propagacion(graphs, monkeypatch):
    _inyectar_plan(monkeypatch, t_start=0, silence=np.arange(N))
    res = simulate_abm(graphs["er"], P, seed=1)
    res.check()
    assert res.R[0] == pytest.approx(1.0)
    assert res.cum_exposed[-1] == 0.0


def test_silencio_en_t0_excluye_semillas_silenciadas(graphs, monkeypatch):
    silenciados = np.arange(N // 2)
    _inyectar_plan(monkeypatch, t_start=0, silence=silenciados)
    res = simulate_abm(graphs["er"], P, seed=1)
    res.check()
    assert res.I[0] == pytest.approx(P.i0)  # las semillas salieron de la otra mitad
    assert res.R[0] == pytest.approx(0.5)


def test_inmunizar_todos_en_t0_no_deja_semillas(graphs, monkeypatch):
    # contrato 3.2: con t_start=0 la intervención va antes de las semillas, y estas salen de nodos no inmunes
    _inyectar_plan(monkeypatch, t_start=0, immunize=np.arange(N))
    res = simulate_abm(graphs["er"], P, seed=1)
    res.check()
    assert res.R[0] == pytest.approx(1.0) and res.cum_exposed[-1] == 0.0


def test_inmunizar_en_t_start_solo_afecta_a_los_susceptibles(graphs, monkeypatch):
    _inyectar_plan(monkeypatch, t_start=1, immunize=np.arange(N))
    res = simulate_abm(graphs["er"], P, seed=1)
    res.check()
    assert res.S[1] == 0.0                      # todos los S pasan a R en t=1...
    assert res.I[0] == pytest.approx(P.i0)      # ...pero las semillas (ya en I) no se inmunizan
    assert res.cum_exposed[-1] == res.cum_exposed[1]  # nadie nuevo se expone después


def test_intervencion_tardia_se_registra_en_t_start(graphs, monkeypatch):
    _inyectar_plan(monkeypatch, t_start=10, silence=np.arange(N // 2))
    res = simulate_abm(graphs["er"], P, seed=1)
    res.check()
    assert res.R[9] < 0.3 and res.R[10] >= 0.5  # el salto aparece justo en t_start


def test_silenciados_no_olvidan_con_omega(graphs, monkeypatch):
    _inyectar_plan(monkeypatch, t_start=0, silence=np.arange(N // 2))
    res = simulate_abm(graphs["er"], dataclasses.replace(P, omega=0.5), seed=1)
    assert res.R.min() >= 0.5 - 1e-9  # la mitad silenciada nunca vuelve a S


def test_seed_strategy_invalida(graphs):
    with pytest.raises(ValueError):
        simulate_abm(graphs["er"], P, seed_strategy="x")


def test_run_replicates():
    reps = run_replicates("er", P, n=500, n_rep=4, t_max=50)
    assert len(reps) == 4
    assert [r.meta["replicate"] for r in reps] == [0, 1, 2, 3]
    assert all(r.meta["network"] == "er" for r in reps)
    assert not np.array_equal(reps[0].I, reps[1].I)
    again = run_replicates("er", P, n=500, n_rep=4, t_max=50)
    assert np.array_equal(reps[2].I, again[2].I)


def test_rendimiento_30_replicas_n5000():
    t0 = time.time()
    reps = run_replicates("ba", P, n=5000, n_rep=30)
    assert time.time() - t0 < 60
    assert len(reps) == 30
    assert compute_metrics(reps[0])["reach"] > 0
