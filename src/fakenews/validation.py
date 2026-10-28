"""Validaciones V1-V3 (ODE vs ABM vs analítico vs literatura). DUEÑA: Camila (P1).

V1 límite de campo medio (ABM en grafo completo vs ODE)       -> results/V1_*.csv
V2 tamaño final analítico (alcance vs R0: ODE, fórmula, ABM)   -> results/V2_*.csv
V3 contrastes cualitativos: pendiente (CP3).

Las gráficas viven aquí en funciones plot_* (contrato, sección 8). Nada se ajusta para que
"cuadre": las diferencias se miden y se diagnostican.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .abm import run_replicates
from .metrics import aggregate_curves, compute_metrics, metrics_table
from .ode_model import final_size, simulate_ode
from .params import MEAN_DEGREE, N_REP, SEED0, T_MAX, ModelParams, SimResult

N_V1 = 1000                  # contrato: N=1000 en grafo completo
T_MAX_V2 = 480               # cerca de R0=1 el horizonte de 240 h es corto (ver 04a)
R0_GRID = [0.5, 0.8, 0.9, 1.0, 1.1, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0]


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _params_for_r0(r0: float, base: ModelParams) -> ModelParams:
    """Barre beta dejando fijos sigma, p, gamma: R0 = beta·<k>·p/gamma (ODE, mezcla homogénea)."""
    beta = r0 * base.gamma / (base.p_believe * MEAN_DEGREE)
    return ModelParams(beta=beta, sigma=base.sigma, p_believe=base.p_believe,
                       gamma=base.gamma, omega=base.omega, i0=base.i0)


def _complete_graph_params(p_ode: ModelParams, n: int) -> ModelParams:
    """Contrato V1: beta_abm = beta_ode/(N-1), así el contagio total por hora iguala al del ODE."""
    return ModelParams(beta=p_ode.beta_ode() / (n - 1), sigma=p_ode.sigma, p_believe=p_ode.p_believe,
                       gamma=p_ode.gamma, omega=p_ode.omega, i0=p_ode.i0)


def discrete_meanfield(p_abm: ModelParams, n: int, t_max: int = T_MAX) -> SimResult:
    """Mapa determinista en tiempo discreto con las MISMAS probabilidades por paso que el ABM
    (grafo completo, omega=0). Es el "ABM sin ruido": sirve para separar el efecto del paso
    de 1 h (discretización) del efecto del tamaño finito (ruido). No es parte del contrato."""
    S, E, I, R = 1 - p_abm.i0, 0.0, p_abm.i0, 0.0
    ce = cb = p_abm.i0
    pd_, pg = 1 - np.exp(-p_abm.sigma), 1 - np.exp(-p_abm.gamma)
    rows = [(S, E, I, R, ce, cb)]
    for _ in range(t_max):
        new_e = S * (1 - np.exp(-p_abm.beta * n * I))   # m = N·I vecinos difusores (grafo completo)
        dec, rec = E * pd_, I * pg
        S, E, I, R = S - new_e, E + new_e - dec, I + p_abm.p_believe * dec - rec, R + (1 - p_abm.p_believe) * dec + rec
        ce, cb = ce + new_e, cb + p_abm.p_believe * dec
        rows.append((S, E, I, R, ce, cb))
    a = np.array(rows)
    return SimResult(t=np.arange(t_max + 1, dtype=float), S=a[:, 0], E=a[:, 1], I=a[:, 2], R=a[:, 3],
                     cum_exposed=a[:, 4], cum_believers=a[:, 5], meta={"model": "discrete_meanfield"})


def _rmse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


def run_v1(n: int = N_V1, n_rep: int = N_REP, out_dir: Optional[Path] = None) -> Dict[str, float]:
    """V1: ABM en grafo completo vs ODE. Devuelve errores y escribe results/V1_*.csv."""
    out_dir = Path(out_dir) if out_dir else _root() / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    p_ode = ModelParams()
    p_abm = _complete_graph_params(p_ode, n)

    ode = simulate_ode(p_ode)
    disc = discrete_meanfield(p_abm, n)
    reps = run_replicates("complete", p_abm, n=n, n_rep=n_rep, seed0=SEED0, t_max=T_MAX)

    mean_I = np.mean([r.I for r in reps], axis=0)
    mean_reach = np.mean([r.cum_exposed for r in reps], axis=0)
    m_abm = compute_metrics(SimResult(reps[0].t, *(np.mean([getattr(r, c) for r in reps], axis=0)
                                                   for c in ("S", "E", "I", "R", "cum_exposed", "cum_believers"))))
    m_ode, m_disc = compute_metrics(ode), compute_metrics(disc)
    per_rep_peak = np.array([compute_metrics(r)["peak_I"] for r in reps])
    per_rep_tpeak = np.array([compute_metrics(r)["t_peak"] for r in reps])
    reach_rep = np.array([r.cum_exposed[-1] for r in reps])

    errs = {
        "n": n, "n_rep": n_rep,
        "rmse_I_abm_vs_ode": _rmse(mean_I, ode.I),
        "rmse_I_abm_vs_discreto": _rmse(mean_I, disc.I),
        "rmse_I_discreto_vs_ode": _rmse(disc.I, ode.I),
        "peak_rel_err_abm_vs_ode": (m_abm["peak_I"] - m_ode["peak_I"]) / m_ode["peak_I"],
        "peak_rel_err_discreto_vs_ode": (m_disc["peak_I"] - m_ode["peak_I"]) / m_ode["peak_I"],
        "t_peak_diff_abm_vs_ode_h": m_abm["t_peak"] - m_ode["t_peak"],
        "t_peak_diff_discreto_vs_ode_h": m_disc["t_peak"] - m_ode["t_peak"],
        "peak_I_rep_mean": float(per_rep_peak.mean()), "peak_I_rep_sd": float(per_rep_peak.std(ddof=1)),
        "t_peak_rep_mean": float(per_rep_tpeak.mean()), "t_peak_rep_sd": float(per_rep_tpeak.std(ddof=1)),
        "reach_abm_mean": float(reach_rep.mean()), "reach_abm_sd": float(reach_rep.std(ddof=1)),
        "reach_ode": m_ode["reach"], "reach_discreto": m_disc["reach"],
        "reach_analitico": 1 - final_size(p_ode.r0_ode(), p_ode.i0, p_ode.p_believe),
        "n_rep_sin_brote": int((reach_rep < 0.1).sum()),
    }
    extras = dict(beta=p_abm.beta, sigma=p_abm.sigma, p_believe=p_abm.p_believe, gamma=p_abm.gamma, i0=p_abm.i0)
    mt = pd.concat([
        metrics_table(reps, exp_id="V1", scenario="completo_N1000", network="complete", model="abm", **extras),
        metrics_table([ode], exp_id="V1", scenario="completo_N1000", network="mean_field", model="ode",
                      **dict(extras, beta=p_ode.beta)),
        metrics_table([disc], exp_id="V1", scenario="completo_N1000", network="complete", model="discreto",
                      **extras),
    ], ignore_index=True)
    ct = pd.concat([
        aggregate_curves(reps, exp_id="V1", scenario="completo_N1000", network="complete", model="abm"),
        _det_curves(ode, "V1", "completo_N1000", "mean_field", "ode"),
        _det_curves(disc, "V1", "completo_N1000", "complete", "discreto"),
    ], ignore_index=True)
    mt.to_csv(out_dir / "V1_metrics.csv", index=False)
    ct.to_csv(out_dir / "V1_curves.csv", index=False)
    pd.DataFrame([errs]).to_csv(out_dir / "V1_errors.csv", index=False)
    return errs


def _det_curves(res: SimResult, exp_id: str, scenario: str, network: str, model: str) -> pd.DataFrame:
    """Curvas de un modelo determinista en formato del contrato (lo = hi = mean)."""
    df = aggregate_curves([res], exp_id=exp_id, scenario=scenario, network=network, model=model)
    return df


def run_v2(n: int = N_V1, n_rep: int = N_REP, r0_grid: Optional[List[float]] = None,
           t_max: int = T_MAX_V2, out_dir: Optional[Path] = None) -> pd.DataFrame:
    """V2: alcance final vs R0 (ODE, fórmula analítica y ABM en grafo completo)."""
    out_dir = Path(out_dir) if out_dir else _root() / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    base = ModelParams()
    rows, mt_frames = [], []
    for r0 in (r0_grid or R0_GRID):
        p_ode = _params_for_r0(r0, base)
        p_abm = _complete_graph_params(p_ode, n)
        ode_reach = simulate_ode(p_ode, t_max=t_max).cum_exposed[-1]
        ode_inf = simulate_ode(p_ode, t_max=5000).cum_exposed[-1]   # horizonte largo: límite t -> infinito
        ana = 1 - final_size(r0, base.i0, base.p_believe)
        ana0 = 1 - final_size(r0, 0.0, base.p_believe)               # i0 -> 0: aquí sí se ve el umbral nítido
        reps = run_replicates("complete", p_abm, n=n, n_rep=n_rep, seed0=SEED0, t_max=t_max)
        reach = np.array([r.cum_exposed[-1] for r in reps])
        rows.append({
            "exp_id": "V2", "scenario": f"R0_{r0:g}", "network": "complete", "r0": r0, "n": n, "n_rep": n_rep,
            "t_max": t_max, "reach_abm_mean": reach.mean(), "reach_abm_sd": reach.std(ddof=1),
            "reach_abm_lo": np.percentile(reach, 2.5), "reach_abm_hi": np.percentile(reach, 97.5),
            "reach_ode_tmax": ode_reach, "reach_ode_inf": ode_inf,
            "reach_analitico": ana, "reach_analitico_i0cero": ana0,
        })
        mt_frames.append(metrics_table(reps, exp_id="V2", scenario=f"R0_{r0:g}", network="complete", model="abm",
                                       r0=r0, beta=p_abm.beta, p_believe=p_abm.p_believe, gamma=p_abm.gamma,
                                       sigma=p_abm.sigma, i0=p_abm.i0))
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "V2_summary.csv", index=False)
    pd.concat(mt_frames, ignore_index=True).to_csv(out_dir / "V2_metrics.csv", index=False)
    return df


def plot_v1(out_dir: Optional[Path] = None, fig_dir: Optional[Path] = None) -> Path:
    """Figura V1: I(t) del ABM (media y percentiles 2.5–97.5 %), ODE y mapa discreto."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out_dir = Path(out_dir) if out_dir else _root() / "results"
    fig_dir = Path(fig_dir) if fig_dir else _root() / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    c = pd.read_csv(out_dir / "V1_curves.csv")
    c = c[c.compartment == "I"]
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    a = c[c.model == "abm"]
    ax.fill_between(a.t, a.lo, a.hi, color="tab:red", alpha=0.2, label="ABM: percentiles 2.5–97.5 % entre réplicas")
    ax.plot(a.t, a["mean"], color="tab:red", lw=2, label="ABM completo (media)")
    ax.plot(c[c.model == "ode"].t, c[c.model == "ode"]["mean"], "k-", lw=2, label="ODE (tiempo continuo)")
    ax.plot(c[c.model == "discreto"].t, c[c.model == "discreto"]["mean"], "--", color="tab:blue", lw=2,
            label="Mapa discreto (paso de 1 h, sin ruido)")
    ax.set(xlabel="Tiempo (horas)", ylabel="Fracción de la población en I",
           title="V1. Límite de campo medio: ABM (N=1000) vs ODE")
    ax.legend(); ax.grid(alpha=0.3)
    path = fig_dir / "fig_V1_campo_medio.png"
    fig.savefig(path, dpi=200, bbox_inches="tight"); plt.close(fig)
    return path


def plot_v2(out_dir: Optional[Path] = None, fig_dir: Optional[Path] = None) -> Path:
    """Figura V2: alcance final vs R0."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out_dir = Path(out_dir) if out_dir else _root() / "results"
    fig_dir = Path(fig_dir) if fig_dir else _root() / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    d = pd.read_csv(out_dir / "V2_summary.csv")
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.errorbar(d.r0, d.reach_abm_mean, yerr=[d.reach_abm_mean - d.reach_abm_lo, d.reach_abm_hi - d.reach_abm_mean],
                fmt="o", color="tab:red", capsize=3, label="ABM completo (media y percentiles 2.5–97.5 %)")
    ax.plot(d.r0, d.reach_ode_tmax, "k-", lw=1.5, label=f"ODE a {int(d.t_max.iloc[0])} h")
    ax.plot(d.r0, d.reach_analitico, "--", color="tab:blue", lw=2, label="Analítico (i0 = 0.01)")
    ax.plot(d.r0, d.reach_analitico_i0cero, ":", color="tab:green", lw=2, label="Analítico (i0 → 0)")
    ax.axvline(1.0, color="gray", ls="-.", lw=1)
    ax.set(xlabel="R0", ylabel="Alcance final (fracción de la población)",
           title="V2. Tamaño final vs R0 (umbral en R0 = 1)")
    ax.legend(); ax.grid(alpha=0.3)
    path = fig_dir / "fig_V2_alcance_vs_R0.png"
    fig.savefig(path, dpi=200, bbox_inches="tight"); plt.close(fig)
    return path


def run_validation(quick: bool = False) -> Dict[str, float]:
    """V1 y V2 (V3 llega en CP3). quick=True usa menos réplicas para pruebas rápidas."""
    n_rep = 5 if quick else N_REP
    errs = run_v1(n_rep=n_rep)
    run_v2(n_rep=n_rep, r0_grid=[0.5, 1.5, 3.0] if quick else None)
    plot_v1(); plot_v2()
    return errs
