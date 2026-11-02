"""Experimento E2: sensibilidad de parámetros (ODE + subconjunto ABM). DUEÑA: Camila (P1).

Responde: ¿cuánto dependen las conclusiones de los parámetros ilustrativos (no calibrados)?

  E2a  ODE: rejilla beta x gamma  -> R0, alcance, pico y hora del pico (mapas de calor)
  E2b  ODE: barrido de p_believe
  E2c  ODE: sensibilidad local (±20 % de un parámetro a la vez, "tornado")
  E2d  ABM: rejilla 3x3 de (beta, gamma) en ER y BA contra el ODE en los mismos puntos

Uso:  python -m fakenews.sensitivity [--quick]
Escribe results/E2_metrics.csv y results/E2_curves.csv (formato del contrato 4.5) más tablas extra
(E2_grid.csv, E2_tornado.csv, E2_abm_vs_ode.csv) y figures/fig_E2_*.png.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

from .abm import run_replicates  # noqa: E402
from .metrics import aggregate_curves, compute_metrics, metrics_table  # noqa: E402
from .networks import build_network, degree_stats  # noqa: E402
from .ode_model import simulate_ode  # noqa: E402
from .params import MEAN_DEGREE, N_DEFAULT, N_REP, SEED0, T_MAX, ModelParams  # noqa: E402
from .validation import r_network  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

BETA_GRID = np.linspace(0.005, 0.06, 12)
GAMMA_GRID = np.linspace(0.03, 0.30, 12)
P_GRID = np.round(np.arange(0.2, 0.91, 0.1), 2)
ABM_BETAS = (0.015, 0.03, 0.045)
ABM_GAMMAS = (0.05, 0.10, 0.20)
ABM_NETWORKS = ("er", "ba")
TORNADO_PARAMS = ("beta", "sigma", "p_believe", "gamma", "i0")
TORNADO_DELTA = 0.20
TORNADO_LABELS = {"beta": "β (contagio)", "sigma": "σ (decisión)", "p_believe": "p (creer)",
                  "gamma": "γ (pérdida de interés)", "i0": "i0 (semillas)"}


def _with(base: ModelParams, **kw) -> ModelParams:
    return replace(base, **kw)


def _ode_row(res, **meta) -> Dict[str, float]:
    return {**meta, **compute_metrics(res)}


def run_sensitivity(quick: bool = False, out_dir: Optional[Path] = None,
                    fig_dir: Optional[Path] = None) -> Dict[str, pd.DataFrame]:
    """Corre E2 completo. quick=True usa rejillas y redes pequeñas (solo para depurar)."""
    out_dir = Path(out_dir) if out_dir else ROOT / "results"
    fig_dir = Path(fig_dir) if fig_dir else ROOT / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    base = ModelParams()
    betas = BETA_GRID[::3] if quick else BETA_GRID
    gammas = GAMMA_GRID[::3] if quick else GAMMA_GRID
    n, n_rep = (500, 3) if quick else (N_DEFAULT, N_REP)

    metric_frames: List[pd.DataFrame] = []
    curve_frames: List[pd.DataFrame] = []

    # --- E2a: rejilla beta x gamma (ODE, mezcla homogénea)
    grid_rows = []
    for beta in betas:
        for gamma in gammas:
            p = _with(base, beta=float(beta), gamma=float(gamma))
            res = simulate_ode(p)
            meta = dict(exp_id="E2", scenario=f"grid_b{beta:.4f}_g{gamma:.3f}", network="mean_field", model="ode",
                        beta=float(beta), gamma=float(gamma), p_believe=p.p_believe, r0=p.r0_ode())
            metric_frames.append(metrics_table([res], **meta))
            reach_inf = simulate_ode(p, t_max=2000).cum_exposed[-1]   # alcance en el límite t -> infinito
            grid_rows.append({"beta": float(beta), "gamma": float(gamma), "r0": p.r0_ode(),
                              **compute_metrics(res), "reach_inf": float(reach_inf)})
    grid = pd.DataFrame(grid_rows)

    # --- E2b: barrido de p_believe (ODE)
    for pb in P_GRID:
        p = _with(base, p_believe=float(pb))
        res = simulate_ode(p)
        meta = dict(exp_id="E2", scenario=f"p{pb:g}", network="mean_field", model="ode",
                    beta=p.beta, gamma=p.gamma, p_believe=float(pb), r0=p.r0_ode())
        metric_frames.append(metrics_table([res], **meta))
        curve_frames.append(aggregate_curves([res], **meta))

    # --- E2c: sensibilidad local ±20 % (ODE)
    ref = compute_metrics(simulate_ode(base))
    tornado = []
    for name in TORNADO_PARAMS:
        v0 = getattr(base, name)
        lo = compute_metrics(simulate_ode(_with(base, **{name: v0 * (1 - TORNADO_DELTA)})))
        hi = compute_metrics(simulate_ode(_with(base, **{name: v0 * (1 + TORNADO_DELTA)})))
        for metric in ("reach", "peak_I", "t_peak"):
            tornado.append({"param": name, "metric": metric, "base": ref[metric],
                            "at_minus20": lo[metric], "at_plus20": hi[metric],
                            "rel_change_minus20": lo[metric] / ref[metric] - 1,
                            "rel_change_plus20": hi[metric] / ref[metric] - 1})
    tornado = pd.DataFrame(tornado)

    # --- E2d: rejilla 3x3 con ABM (ER y BA) y ODE en los mismos puntos
    abm_rows = []
    for beta in ABM_BETAS:
        for gamma in ABM_GAMMAS:
            p = _with(base, beta=beta, gamma=gamma)
            scen = f"b{beta:g}_g{gamma:g}"
            extras = dict(beta=beta, gamma=gamma, p_believe=p.p_believe)
            ode = simulate_ode(p)
            metric_frames.append(metrics_table([ode], exp_id="E2", scenario=scen, network="mean_field",
                                               model="ode", r0=p.r0_ode(), **extras))
            curve_frames.append(aggregate_curves([ode], exp_id="E2", scenario=scen, network="mean_field",
                                                 model="ode", r0=p.r0_ode(), **extras))
            for net in ABM_NETWORKS:
                reps = run_replicates(net, p, n=n, n_rep=n_rep, seed0=SEED0)
                ds = degree_stats(build_network(net, n=n, seed=SEED0))
                r_net = r_network(p, ds["k_mean"], ds["k2_mean"])
                mt = metrics_table(reps, exp_id="E2", scenario=scen, network=net, model="abm", r0=r_net, **extras)
                metric_frames.append(mt)
                curve_frames.append(aggregate_curves(reps, exp_id="E2", scenario=scen, network=net, model="abm",
                                                     r0=r_net, **extras))
                reach = mt["reach"].to_numpy()
                half = stats.t.ppf(0.975, len(reach) - 1) * reach.std(ddof=1) / np.sqrt(len(reach))
                abm_rows.append({"network": net, "beta": beta, "gamma": gamma, "r0_ode": p.r0_ode(),
                                 "r_red": r_net, "reach_abm": reach.mean(), "reach_abm_half_ci": half,
                                 "peak_abm": mt["peak_I"].mean(), "reach_ode": compute_metrics(ode)["reach"],
                                 "peak_ode": compute_metrics(ode)["peak_I"], "n": n, "n_rep": n_rep})
    abm_vs_ode = pd.DataFrame(abm_rows)

    # --- escritura
    metrics_df = pd.concat(metric_frames, ignore_index=True)
    curves_df = pd.concat(curve_frames, ignore_index=True)
    metrics_df.to_csv(out_dir / "E2_metrics.csv", index=False)
    curves_df.to_csv(out_dir / "E2_curves.csv", index=False)
    grid.to_csv(out_dir / "E2_grid.csv", index=False)
    tornado.to_csv(out_dir / "E2_tornado.csv", index=False)
    abm_vs_ode.to_csv(out_dir / "E2_abm_vs_ode.csv", index=False)
    plot_e2(out_dir, fig_dir)
    return {"metrics": metrics_df, "curves": curves_df, "grid": grid, "tornado": tornado,
            "abm_vs_ode": abm_vs_ode}


def plot_e2(out_dir: Optional[Path] = None, fig_dir: Optional[Path] = None) -> List[Path]:
    """Cuatro figuras de E2 a partir de los CSV ya escritos (no vuelve a simular)."""
    out_dir = Path(out_dir) if out_dir else ROOT / "results"
    fig_dir = Path(fig_dir) if fig_dir else ROOT / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    grid = pd.read_csv(out_dir / "E2_grid.csv")
    m = pd.read_csv(out_dir / "E2_metrics.csv")

    # (1) mapas de calor beta x gamma
    bs, gs = sorted(grid.beta.unique()), sorted(grid.gamma.unique())
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.3))
    for ax, (col, title, cmap) in zip(axes, (("r0", "R0 = β·⟨k⟩·p/γ", "viridis"),
                                             ("reach", "Alcance a 240 h", "magma"),
                                             ("peak_I", "Pico de difusores", "magma"))):
        z = grid.pivot(index="gamma", columns="beta", values=col).reindex(index=gs, columns=bs)
        im = ax.imshow(z.to_numpy(), origin="lower", aspect="auto", cmap=cmap,
                       extent=[bs[0], bs[-1], gs[0], gs[-1]])
        r0 = grid.pivot(index="gamma", columns="beta", values="r0").reindex(index=gs, columns=bs)
        ax.contour(np.linspace(bs[0], bs[-1], len(bs)), np.linspace(gs[0], gs[-1], len(gs)), r0.to_numpy(),
                   levels=[1.0], colors="white", linewidths=1.5, linestyles="--")
        ax.set(xlabel="β (por vecino difusor y hora)", ylabel="γ (pérdida de interés, 1/h)", title=title)
        fig.colorbar(im, ax=ax)
    fig.suptitle("E2a. Sensibilidad del ODE a β y γ (línea blanca: R0 = 1)", fontsize=11)
    fig.tight_layout()
    path = fig_dir / "fig_E2_mapas_beta_gamma.png"
    fig.savefig(path, dpi=200, bbox_inches="tight"); plt.close(fig); paths.append(path)

    # (2) barrido de p_believe
    pm = m[(m.model == "ode") & m.scenario.str.match(r"^p[0-9.]+$")].sort_values("p_believe")
    fig, ax = plt.subplots(figsize=(7.5, 4.3))
    ax.plot(pm.p_believe, pm.reach, "o-", color="#d62728", label="Alcance total")
    ax.plot(pm.p_believe, pm.peak_I * 10, "s--", color="#4c78a8", label="Pico de difusores (×10)")
    ax2 = ax.twinx()
    ax2.plot(pm.p_believe, pm.r0, ":", color="gray", label="R0")
    ax2.axhline(1.0, color="gray", lw=0.8)
    ax2.set_ylabel("R0", color="gray")
    ax.set(xlabel="p (probabilidad de creer y compartir)", ylabel="Fracción de la población",
           title="E2b. Sensibilidad del ODE a la credulidad p")
    ax.legend(loc="upper left"); ax.grid(alpha=0.3)
    path = fig_dir / "fig_E2_p_believe.png"
    fig.savefig(path, dpi=200, bbox_inches="tight"); plt.close(fig); paths.append(path)

    # (3) tornado
    tor = pd.read_csv(out_dir / "E2_tornado.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.9), sharey=True)
    for ax, (metric, title) in zip(axes, (("reach", "Alcance total"), ("peak_I", "Pico de difusores"))):
        d = tor[tor.metric == metric].copy()
        d["span"] = (d.rel_change_plus20 - d.rel_change_minus20).abs()
        d = d.sort_values("span")
        y = np.arange(len(d))
        ax.barh(y, 100 * d.rel_change_minus20, color="#4c78a8", label="−20 % del parámetro")
        ax.barh(y, 100 * d.rel_change_plus20, color="#d62728", label="+20 % del parámetro")
        ax.set_yticks(y); ax.set_yticklabels([TORNADO_LABELS[p] for p in d.param])
        ax.axvline(0, color="k", lw=0.8)
        ax.set(xlabel="Cambio relativo de la métrica (%)", title=title); ax.grid(alpha=0.3, axis="x")
    axes[0].legend(loc="lower right", fontsize=8)
    fig.suptitle("E2c. Sensibilidad local del ODE: ±20 % de un parámetro a la vez", fontsize=11)
    fig.tight_layout()
    path = fig_dir / "fig_E2_tornado.png"
    fig.savefig(path, dpi=200, bbox_inches="tight"); plt.close(fig); paths.append(path)

    # (4) ABM 3x3 vs ODE
    av = pd.read_csv(out_dir / "E2_abm_vs_ode.csv")
    av["label"] = av.apply(lambda r: f"β={r.beta:g}\nγ={r.gamma:g}", axis=1)
    labels = list(dict.fromkeys(av.label))
    fig, ax = plt.subplots(figsize=(11, 4.3))
    x = np.arange(len(labels)); w = 0.27
    for j, (net, col, name) in enumerate((("er", "#4c78a8", "ABM Erdős–Rényi"), ("ba", "#d62728", "ABM Barabási–Albert"))):
        d = av[av.network == net].set_index("label").reindex(labels)
        ax.bar(x + (j - 1) * w, d.reach_abm, w, yerr=d.reach_abm_half_ci, color=col, capsize=2, label=name)
    ode = av[av.network == "er"].set_index("label").reindex(labels)
    ax.bar(x + w, ode.reach_ode, w, color="#444444", label="ODE (mezcla homogénea)")
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8)
    ax.set(ylabel="Alcance a 240 h", title="E2d. Alcance: ABM (IC 95 % de la media) vs ODE en la rejilla 3×3")
    ax.legend(); ax.grid(alpha=0.3, axis="y")
    path = fig_dir / "fig_E2_abm_vs_ode.png"
    fig.savefig(path, dpi=200, bbox_inches="tight"); plt.close(fig); paths.append(path)
    return paths


def main() -> None:
    ap = argparse.ArgumentParser(description="E2: análisis de sensibilidad")
    ap.add_argument("--quick", action="store_true", help="versión pequeña para depurar")
    args = ap.parse_args()
    out = run_sensitivity(quick=args.quick)
    print(out["tornado"][out["tornado"].metric == "reach"].round(3).to_string(index=False))
    print(out["abm_vs_ode"].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
