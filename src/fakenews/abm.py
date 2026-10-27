"""Simulación basada en agentes sobre redes + Monte Carlo. DUEÑA: Marinés (P2).

Reglas de transición exactas en docs/CONTRATO.md, sección 3.2. Debe devolver SimResult.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import List, Optional

import networkx as nx
import numpy as np

from . import interventions
from .networks import build_network
from .params import (
    E, I, R, S,
    Intervention, ModelParams, SimResult,
    MEAN_DEGREE, N_DEFAULT, N_REP, SEED0, T_MAX,
)

SEED_STRATEGIES = ("random", "hub")


def _choose_seeds(
    degrees: np.ndarray, eligible: np.ndarray, n_seeds: int, strategy: str, rng: np.random.Generator
) -> np.ndarray:
    """Elige las semillas entre los nodos elegibles (no silenciados)."""
    idx = np.flatnonzero(eligible)
    n_seeds = min(n_seeds, len(idx))
    if n_seeds == 0:
        return idx[:0]
    if strategy == "random":
        return rng.choice(idx, size=n_seeds, replace=False)
    # "hub": los de mayor grado; el desempate es al azar (se baraja antes de ordenar de forma estable)
    shuffled = rng.permutation(idx)
    order = np.argsort(-degrees[shuffled], kind="stable")
    return shuffled[order[:n_seeds]]


def simulate_abm(
    G: nx.Graph,
    params: ModelParams,
    intervention: Optional[Intervention] = None,
    seed: int = 0,
    t_max: int = T_MAX,
    seed_strategy: str = "random",
) -> SimResult:
    """Una corrida estocástica en tiempo discreto (dt = 1 h, actualización síncrona).

    seed_strategy: "random" (semillas al azar) | "hub" (semillas = nodos de mayor grado).
    La intervención se aplica con fakenews.interventions.plan(...) (ver contrato).

    Convenciones (contrato 3.2):
    - El estado se registra en t = 0..t_max. Si la intervención empieza en t_start > 0, el estado
      registrado en t_start YA incluye el silencio/la inmunización (se aplican antes de las transiciones).
    - Si t_start = 0 la intervención se aplica antes de elegir semillas y estas salen de nodos no silenciados.
    - Los nodos silenciados quedan en R para siempre (aunque omega > 0); los inmunizados sí pueden olvidar.
    """
    if seed_strategy not in SEED_STRATEGIES:
        raise ValueError(f"seed_strategy desconocida: {seed_strategy!r}. Opciones: {SEED_STRATEGIES}")
    n = G.number_of_nodes()
    rng = np.random.default_rng(seed)

    A = nx.to_scipy_sparse_array(G, nodelist=range(n), format="csr", dtype=np.float32)
    degrees = np.asarray(A.sum(axis=1)).ravel()

    pl = interventions.plan(G, intervention, rng)
    state = np.full(n, S, dtype=np.int8)
    silenced = np.zeros(n, dtype=bool)

    def apply_intervention() -> None:
        silenced[pl.silence] = True
        state[pl.silence] = R
        imm = pl.immunize[state[pl.immunize] == S]  # solo los que aún están en S
        state[imm] = R

    if pl.t_start == 0:
        apply_intervention()

    n_seeds = max(1, round(params.i0 * n))
    seeds = _choose_seeds(degrees, ~silenced & (state == S), n_seeds, seed_strategy, rng)
    state[seeds] = I
    # "alguna vez": se cuentan nodos únicos (con omega > 0 una persona puede exponerse varias veces)
    ever_exposed = np.zeros(n, dtype=bool)
    ever_believer = np.zeros(n, dtype=bool)
    ever_exposed[seeds] = ever_believer[seeds] = True  # las semillas cuentan como expuestas y creyentes

    # probabilidades por paso (dt = 1 h): 1 - exp(-tasa·dt)
    q = 1.0 - np.exp(-params.beta)
    p_decide = 1.0 - np.exp(-params.sigma)
    p_wane = 1.0 - np.exp(-params.omega)

    frac = np.zeros((t_max + 1, 6))  # S, E, I, R, cum_exposed, cum_believers (conteos; se normalizan al final)
    for t in range(t_max + 1):
        if t == pl.t_start and t > 0:
            apply_intervention()
        frac[t, :4] = np.bincount(state, minlength=4)
        frac[t, 4], frac[t, 5] = ever_exposed.sum(), ever_believer.sum()
        if t == t_max:
            break

        # --- transiciones síncronas: todas se calculan con el estado al inicio del paso ---
        delta_t = pl.delta if t >= pl.t_start else 0.0
        p_recover = 1.0 - np.exp(-(params.gamma + delta_t))
        m = A @ (state == I).astype(np.float32)  # nº de vecinos difusores de cada nodo
        u = rng.random(n)      # un uniforme por nodo: cada nodo está en un solo estado, solo una regla le aplica
        v = rng.random(n)      # segundo uniforme: decisión creer/no creer al salir de E
        new = state.copy()

        s_to_e = (state == S) & (u < 1.0 - (1.0 - q) ** m)
        decides = (state == E) & (u < p_decide)
        e_to_i = decides & (v < params.p_believe)
        e_to_r = decides & (v >= params.p_believe)
        i_to_r = (state == I) & (u < p_recover)
        new[s_to_e] = E
        new[e_to_i] = I
        new[e_to_r] = R
        new[i_to_r] = R
        if params.omega > 0:
            r_to_s = (state == R) & ~silenced & (u < p_wane)
            new[r_to_s] = S

        ever_exposed |= s_to_e
        ever_believer |= e_to_i
        state = new

    frac /= n
    return SimResult(
        t=np.arange(t_max + 1, dtype=float),
        S=frac[:, 0], E=frac[:, 1], I=frac[:, 2], R=frac[:, 3],
        cum_exposed=frac[:, 4], cum_believers=frac[:, 5],
        meta={
            "model": "abm",
            "n": n,
            "seed": seed,
            "seed_strategy": seed_strategy,
            "k_mean": float(degrees.mean()),
            "params": asdict(params),
            "intervention": asdict(intervention) if intervention else None,
        },
    )


def run_replicates(
    kind: str,
    params: ModelParams,
    intervention: Optional[Intervention] = None,
    n: int = N_DEFAULT,
    mean_degree: float = MEAN_DEGREE,
    n_rep: int = N_REP,
    seed0: int = SEED0,
    t_max: int = T_MAX,
    seed_strategy: str = "random",
) -> List[SimResult]:
    """Monte Carlo: n_rep corridas; la réplica r usa red y dinámica con semilla seed0 + r."""
    results = []
    for r in range(n_rep):
        G = build_network(kind, n=n, mean_degree=mean_degree, seed=seed0 + r)
        res = simulate_abm(G, params, intervention, seed=seed0 + r, t_max=t_max, seed_strategy=seed_strategy)
        res.meta.update({"network": kind, "replicate": r})
        results.append(res)
    return results
