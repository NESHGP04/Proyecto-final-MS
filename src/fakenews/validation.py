"""Validaciones V1-V3 (ODE vs ABM vs analítico vs literatura). DUEÑA: Camila (P1).

V1 límite de campo medio (ABM en grafo completo vs ODE)       -> results/V1_*.csv
V2 tamaño final analítico (alcance vs R0: ODE, fórmula, ABM)   -> results/V2_*.csv
V3 contrastes cualitativos con la teoría y la literatura                  -> results/V3_*.csv

Las gráficas viven aquí en funciones plot_* (contrato, sección 8). Nada se ajusta para que
"cuadre": las diferencias se miden y se diagnostican.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from scipy import stats
from scipy.optimize import brentq

from .abm import run_replicates
from .metrics import aggregate_curves, compute_metrics, metrics_table
from .networks import build_network, degree_stats
from .ode_model import final_size, simulate_ode
from .params import MEAN_DEGREE, N_DEFAULT, N_REP, SEED0, T_MAX, ModelParams, SimResult

N_V1 = 1000                  # contrato: N=1000 en grafo completo
T_MAX_V2 = 480               # cerca de R0=1 el horizonte de 240 h es corto (ver 04a)
R0_GRID = [0.5, 0.8, 0.9, 1.0, 1.1, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0]
V3_NETWORKS = ("er", "ba", "ws")
V3_I0 = 0.002                # semillas pocas (10 de 5000): el umbral se ve mejor que con i0 = 0.01
V3_OUTBREAK = 0.10           # criterio de "brote": alcance medio >= 10 % de la población
V3_TRUE = ModelParams(beta=0.02, p_believe=0.45)   # noticia "verdadera": menos contagiosa y menos creída
V3_FALSE = ModelParams()                           # noticia "falsa": parámetros por defecto
V3_SPEED_LEVEL = 0.05        # velocidad: hora en que se expone el 5 % de la población


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


def discrete_transmissibility(beta: float, gamma: float) -> float:
    """Probabilidad T de que un difusor contagie a UN vecino susceptible durante todo su periodo en I.

    El ABM (contrato 3.2) da a cada difusor, en cada paso que pasa en I (incluido el paso en el que se
    recupera), una oportunidad de contagiar con q = 1 - exp(-beta); el nº de pasos en I es geométrico con
    parámetro 1 - exp(-gamma). Sumando:  T = (1 - e^-beta) / (1 - e^-(beta+gamma)).
    (En tiempo continuo sería beta/(beta+gamma).)
    """
    return float((1.0 - np.exp(-beta)) / (1.0 - np.exp(-(beta + gamma))))


def r_network(params: ModelParams, k_mean: float, k2_mean: float) -> float:
    """Número reproductivo efectivo en una red sin correlaciones (aproximación de Newman, 2002):

        R_red = T · p · (<k^2> - <k>) / <k>

    Un nodo que se hace difusor tiene, en promedio, (<k^2> - <k>)/<k> vecinos "nuevos" (grado en exceso);
    cada uno se contagia con prob. T y se vuelve difusor con prob. p. En ER el cociente de grados es <k>."""
    return discrete_transmissibility(params.beta, params.gamma) * params.p_believe * (k2_mean - k_mean) / k_mean


def beta_critical(params: ModelParams, k_mean: float, k2_mean: float) -> float:
    """beta tal que R_red = 1 (NaN si ni con T -> 1 se llega al umbral)."""
    def g(beta: float) -> float:
        return r_network(ModelParams(beta=beta, sigma=params.sigma, p_believe=params.p_believe, gamma=params.gamma,
                                     omega=params.omega, i0=params.i0), k_mean, k2_mean) - 1.0
    hi = 20.0
    if g(hi) < 0:
        return float("nan")
    return float(brentq(g, 1e-9, hi, xtol=1e-12))


def beta_critical_meanfield(params: ModelParams, mean_degree: float = MEAN_DEGREE) -> float:
    """Umbral del ODE de mezcla homogénea: R0 = beta·<k>·p/gamma = 1."""
    return params.gamma / (params.p_believe * mean_degree)


def _first_crossing(x: np.ndarray, y: np.ndarray, level: float) -> float:
    """Primer x en que y cruza `level` hacia arriba (interpolación lineal); NaN si no cruza."""
    for i in range(1, len(x)):
        if y[i - 1] < level <= y[i]:
            return float(x[i - 1] + (level - y[i - 1]) * (x[i] - x[i - 1]) / (y[i] - y[i - 1]))
    return float("nan")


def _time_to_exposed(res: SimResult, level: float) -> float:
    """Primera hora con cum_exposed >= level; si nunca ocurre, t_max + 1 (dato censurado: es el más lento)."""
    hit = np.flatnonzero(res.cum_exposed >= level)
    return float(res.t[hit[0]]) if len(hit) else float(res.t[-1] + 1)


def run_v3(n: int = N_DEFAULT, n_rep_a: int = 15, n_rep_b: int = N_REP, beta_grid: Optional[List[float]] = None,
           out_dir: Optional[Path] = None) -> Dict[str, float]:
    """V3: contrastes cualitativos. NO es una calibración con datos reales.

    V3a  Umbral de propagación por topología: se barre beta con el ABM en ER, BA y WS (i0 pequeño) y se compara
         el beta empírico en que el alcance medio cruza 10 % con el umbral que predice R_red = 1
         (Newman, 2002) y con el umbral del ODE. Teoría de Pastor-Satorras y Vespignani (2001): cuanto más
         heterogénea la red (<k^2> grande), menor umbral.
    V3b  Noticia "falsa" vs "verdadera": con parámetros supuestos (la falsa es más contagiosa y más creída,
         coherente con Vosoughi et al. 2018) se comprueba que el modelo la propaga más lejos y más rápido.
         Es una prueba de CONSISTENCIA cualitativa: el resultado está inducido por los parámetros supuestos.
    Escribe results/V3_metrics.csv, V3_curves.csv (formato del contrato), V3_threshold.csv y V3_comparisons.csv.
    """
    out_dir = Path(out_dir) if out_dir else _root() / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    grid = np.asarray(beta_grid if beta_grid is not None else np.linspace(0.002, 0.044, 15))
    base = ModelParams(i0=V3_I0)

    # --- V3a: barrido de beta por topología
    mt_frames, thr_rows = [], []
    reach_by_net: Dict[str, np.ndarray] = {}
    for net in V3_NETWORKS:
        means = []
        for beta in grid:
            p = ModelParams(beta=float(beta), sigma=base.sigma, p_believe=base.p_believe, gamma=base.gamma,
                            omega=base.omega, i0=base.i0)
            reps = run_replicates(net, p, n=n, n_rep=n_rep_a, seed0=SEED0)
            mt = metrics_table(reps, exp_id="V3", scenario=f"umbral_beta{beta:.4f}", network=net, model="abm",
                               beta=float(beta), p_believe=p.p_believe, gamma=p.gamma, i0=p.i0)
            mt_frames.append(mt)
            means.append(float(mt["reach"].mean()))
        reach_by_net[net] = np.asarray(means)
        ds = degree_stats(build_network(net, n=n, seed=SEED0))
        thr_rows.append({
            "network": net, "k_mean": ds["k_mean"], "k2_mean": ds["k2_mean"], "k_max": ds["k_max"],
            "excess_degree": (ds["k2_mean"] - ds["k_mean"]) / ds["k_mean"],
            "beta_c_pred": beta_critical(base, ds["k_mean"], ds["k2_mean"]),
            "beta_c_emp": _first_crossing(grid, reach_by_net[net], V3_OUTBREAK),
        })
    thr_rows.append({"network": "mean_field", "k_mean": MEAN_DEGREE, "k2_mean": float("nan"), "k_max": float("nan"),
                     "excess_degree": MEAN_DEGREE, "beta_c_pred": beta_critical_meanfield(base),
                     "beta_c_emp": float("nan")})
    thr = pd.DataFrame(thr_rows)
    thr.to_csv(out_dir / "V3_threshold.csv", index=False)

    # ¿el horizonte de 240 h subestima el alcance justo en el umbral empírico? (se repite a 720 h)
    hz_rows = []
    for net in V3_NETWORKS:
        b_emp = float(thr.loc[thr.network == net, "beta_c_emp"].iloc[0])
        if not np.isfinite(b_emp):
            continue
        p_hz = ModelParams(beta=b_emp, sigma=base.sigma, p_believe=base.p_believe, gamma=base.gamma,
                           omega=base.omega, i0=base.i0)
        short = [r.cum_exposed[-1] for r in run_replicates(net, p_hz, n=n, n_rep=n_rep_a, seed0=SEED0, t_max=T_MAX)]
        long_ = [r.cum_exposed[-1] for r in run_replicates(net, p_hz, n=n, n_rep=n_rep_a, seed0=SEED0, t_max=3 * T_MAX)]
        hz_rows.append({"network": net, "beta": b_emp, "t_max_corto": T_MAX, "reach_corto": float(np.mean(short)),
                        "t_max_largo": 3 * T_MAX, "reach_largo": float(np.mean(long_))})
    pd.DataFrame(hz_rows).to_csv(out_dir / "V3_horizon.csv", index=False)
    sweep = pd.DataFrame({"beta": grid, **{f"reach_{k}": v for k, v in reach_by_net.items()}})
    sweep.to_csv(out_dir / "V3_beta_sweep.csv", index=False)

    # --- V3b: falsa vs verdadera (réplicas independientes: semillas disjuntas)
    comp_rows, ct_frames = [], []
    summary: Dict[str, float] = {}
    for net in ("er", "ba"):
        res = {}
        for label, p, s0 in (("noticia_falsa", V3_FALSE, SEED0), ("noticia_verdadera", V3_TRUE, SEED0 + 10_000)):
            reps = run_replicates(net, p, n=n, n_rep=n_rep_b, seed0=s0)
            extras = dict(beta=p.beta, p_believe=p.p_believe, gamma=p.gamma, i0=p.i0)
            mt = metrics_table(reps, exp_id="V3", scenario=label, network=net, model="abm", **extras)
            mt["t_5pct"] = [_time_to_exposed(r, V3_SPEED_LEVEL) for r in reps]   # métrica extra de velocidad
            mt_frames.append(mt)
            ct_frames.append(aggregate_curves(reps, exp_id="V3", scenario=label, network=net, model="abm"))
            res[label] = mt
        # t_peak no es una medida de velocidad válida si no hay brote (el "pico" es la semilla en t=0);
        # por eso se agrega t_5pct: hora en que se expone el 5 % (censurada en t_max+1 si nunca ocurre).
        for metric, expected in (("reach", "greater"), ("peak_I", "greater"), ("t_5pct", "less"), ("t_peak", "less")):
            a, b = res["noticia_falsa"][metric].to_numpy(), res["noticia_verdadera"][metric].to_numpy()
            u, pv = stats.mannwhitneyu(a, b, alternative="two-sided", method="asymptotic")
            effect = 2 * float(u) / (len(a) * len(b)) - 1   # rank-biserial: >0 si falsa > verdadera
            ok = (effect > 0) if expected == "greater" else (effect < 0)
            comp_rows.append({
                "network": net, "metric": metric, "mean_falsa": a.mean(), "mean_verdadera": b.mean(),
                "n_falsa": len(a), "n_verdadera": len(b), "U": float(u), "p_value": float(pv),
                "rank_biserial": effect, "expected": f"falsa {expected} que verdadera",
                "verdict": "consistente" if (pv < 0.05 and ok) else "no_consistente",
            })
    comp = pd.DataFrame(comp_rows)
    comp.to_csv(out_dir / "V3_comparisons.csv", index=False)
    pd.concat(mt_frames, ignore_index=True).to_csv(out_dir / "V3_metrics.csv", index=False)
    pd.concat(ct_frames, ignore_index=True).to_csv(out_dir / "V3_curves.csv", index=False)

    for _, r in thr.iterrows():
        summary[f"beta_c_pred_{r.network}"] = float(r.beta_c_pred)
        summary[f"beta_c_emp_{r.network}"] = float(r.beta_c_emp)
    summary["v3b_consistentes"] = int((comp.verdict == "consistente").sum())
    summary["v3b_total"] = int(len(comp))
    return summary


def plot_v3(out_dir: Optional[Path] = None, fig_dir: Optional[Path] = None) -> List[Path]:
    """Figuras V3: (a) alcance vs beta por topología con umbrales; (b) noticia falsa vs verdadera."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out_dir = Path(out_dir) if out_dir else _root() / "results"
    fig_dir = Path(fig_dir) if fig_dir else _root() / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    names = {"er": "Erdős–Rényi", "ba": "Barabási–Albert", "ws": "Watts–Strogatz"}
    colors = {"er": "#4c78a8", "ba": "#d62728", "ws": "#53945b"}
    paths = []

    sweep = pd.read_csv(out_dir / "V3_beta_sweep.csv")
    thr = pd.read_csv(out_dir / "V3_threshold.csv").set_index("network")
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for net in V3_NETWORKS:
        ax.plot(sweep.beta, sweep[f"reach_{net}"], "o-", color=colors[net], label=names[net])
        ax.axvline(thr.loc[net, "beta_c_pred"], color=colors[net], ls=":", lw=1.5)
    ax.axvline(thr.loc["mean_field", "beta_c_pred"], color="k", ls="-.", lw=1.2, label="Umbral del ODE (R0 = 1)")
    ax.axhline(V3_OUTBREAK, color="gray", ls="--", lw=1)
    ax.text(sweep.beta.min(), V3_OUTBREAK + 0.01, "criterio de brote (10 %)", ha="left", color="gray", fontsize=8)
    ax.set(xlabel="β (contagio por vecino difusor y hora)", ylabel="Alcance medio (fracción de la población)",
           title="V3a. Umbral de propagación por topología (líneas punteadas: umbral teórico R_red = 1)")
    ax.title.set_fontsize(9.5)
    ax.legend(); ax.grid(alpha=0.3)
    path = fig_dir / "fig_V3_umbral_topologias.png"
    fig.savefig(path, dpi=200, bbox_inches="tight"); plt.close(fig); paths.append(path)

    m = pd.read_csv(out_dir / "V3_metrics.csv")
    m = m[m.scenario.isin(["noticia_falsa", "noticia_verdadera"])]
    fig, axes = plt.subplots(1, 4, figsize=(14, 4))
    for ax, (metric, label) in zip(axes, (("reach", "Alcance total"), ("peak_I", "Pico de difusores"),
                                          ("t_5pct", "Hora en que se expone el 5 % (h)"),
                                          ("t_peak", "Hora del pico (h)\n(sin sentido si no hay brote)"))):
        for j, net in enumerate(("er", "ba")):
            for k, (sc, col) in enumerate((("noticia_falsa", "#d62728"), ("noticia_verdadera", "#4c78a8"))):
                v = m[(m.network == net) & (m.scenario == sc)][metric].to_numpy()
                mean = v.mean(); half = stats.t.ppf(0.975, len(v) - 1) * v.std(ddof=1) / np.sqrt(len(v))
                ax.bar(j * 3 + k, mean, yerr=half, color=col, capsize=4,
                       label=("Noticia falsa" if sc == "noticia_falsa" else "Noticia verdadera") if j == 0 else None)
        ax.set_xticks([0.5, 3.5]); ax.set_xticklabels(["Erdős–Rényi", "Barabási–Albert"])
        ax.set_title(label, fontsize=9.5); ax.grid(alpha=0.3, axis="y")
    axes[0].legend()
    fig.suptitle("V3b. Noticia falsa vs verdadera (consistencia cualitativa; IC 95 % de la media)", fontsize=10)
    fig.tight_layout()
    path = fig_dir / "fig_V3_falsa_vs_verdadera.png"
    fig.savefig(path, dpi=200, bbox_inches="tight"); plt.close(fig); paths.append(path)
    return paths



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
    """V1, V2 y V3. quick=True usa menos réplicas y redes chicas para pruebas rápidas."""
    n_rep = 5 if quick else N_REP
    errs = run_v1(n_rep=n_rep)
    run_v2(n_rep=n_rep, r0_grid=[0.5, 1.5, 3.0] if quick else None)
    plot_v1(); plot_v2()
    if quick:
        errs.update(run_v3(n=500, n_rep_a=3, n_rep_b=5, beta_grid=[0.005, 0.02, 0.04]))
    else:
        errs.update(run_v3())
    plot_v3()
    return errs
