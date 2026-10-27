"""V4: convergencia Monte Carlo del ABM. DUEÑA: Marinés (P2).

Responde dos preguntas que justifican nuestras elecciones N=5000 y 30 réplicas:
  (a) ¿cuánto se estrecha el IC 95 % de la media al aumentar el nº de réplicas?
  (b) ¿cómo cambia la variabilidad entre réplicas al aumentar el tamaño de la red N?

Uso:  python -m fakenews.convergence [--quick]
Escribe results/V4_metrics.csv, results/V4_curves.csv (formato del contrato 4.5), results/V4_ci_width.csv
(extra, con el ancho del IC) y figures/fig_V4_*.png.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

from .abm import run_replicates  # noqa: E402
from .metrics import aggregate_curves, metrics_table  # noqa: E402
from .params import MEAN_DEGREE, N_DEFAULT, N_REP, SEED0, ModelParams  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = ROOT / "figures"

NETWORKS = ("er", "ba")
REP_GRID = (5, 10, 20, 30, 50, 100)
N_GRID = (1000, 2000, 5000, 10000)
METRICS_CI = ("reach", "peak_I")
LABELS = {"reach": "Alcance total", "peak_I": "Pico de difusores"}
COLORS = {"er": "#4c78a8", "ba": "#d62728"}  # misma convención de color por red en todas las figuras de V4
NAMES = {"er": "Erdős–Rényi", "ba": "Barabási–Albert"}


def ci_half_width(x: np.ndarray, level: float = 0.95) -> float:
    """Semiancho del IC t de Student para la media: t_{1-α/2, r-1} · s / sqrt(r)."""
    r = len(x)
    return float(stats.t.ppf(0.5 + level / 2, r - 1) * np.std(x, ddof=1) / np.sqrt(r))


def ci_vs_reps(values: np.ndarray, rep_grid=REP_GRID, n_draws: int = 200, seed: int = SEED0) -> pd.DataFrame:
    """Semiancho promedio del IC para subconjuntos aleatorios de r réplicas (n_draws sorteos por r).

    Promediar sobre sorteos evita que el resultado dependa de qué réplicas "tocaron" primero.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for r in rep_grid:
        if r > len(values):
            continue
        hw = [ci_half_width(rng.choice(values, size=r, replace=False)) for _ in range(n_draws)]
        mean_all = float(np.mean(values))
        rows.append({"n_rep": r, "half_width": float(np.mean(hw)), "rel_half_width": float(np.mean(hw)) / mean_all})
    return pd.DataFrame(rows)


def plot_ci_vs_reps(ci: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    for ax, metric in zip(axes, METRICS_CI):
        for net in NETWORKS:
            d = ci[(ci.network == net) & (ci.metric == metric)]
            ax.plot(d.n_rep, 100 * d.rel_half_width, "o-", color=COLORS[net], label=NAMES[net])
        ax.axvline(N_REP, color="gray", ls="--", lw=1)
        ax.text(N_REP * 1.05, ax.get_ylim()[1] * 0.9, f"{N_REP} réplicas", color="gray", fontsize=8)
        ax.set_xscale("log")
        ax.set_xticks(REP_GRID)
        ax.set_xticklabels(REP_GRID)
        ax.set_xlabel("Número de réplicas Monte Carlo")
        ax.set_ylabel("Semiancho del IC 95 % (% de la media)")
        ax.set_title(LABELS[metric])
        ax.grid(alpha=0.3)
    axes[0].legend()
    fig.suptitle("V4a: el IC se estrecha como 1/√réplicas", fontsize=11)
    fig.tight_layout(w_pad=2.5)
    fig.savefig(path, dpi=200)
    plt.close(fig)


def plot_variance_vs_n(df: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    for ax, metric in zip(axes, METRICS_CI):
        for net in NETWORKS:
            d = df[(df.network == net) & (df.metric == metric)]
            ax.plot(d.n, d["std"], "o-", color=COLORS[net], label=NAMES[net])
        ax.set_xscale("log")
        ax.set_xticks(N_GRID)
        ax.set_xticklabels(N_GRID)
        ax.set_xlabel("Tamaño de la red N")
        ax.set_ylabel("Desv. estándar entre réplicas")
        ax.set_title(LABELS[metric])
        ax.grid(alpha=0.3)
    axes[0].legend()
    fig.suptitle("V4b: la variabilidad entre réplicas baja al crecer N", fontsize=11)
    fig.tight_layout(w_pad=2.5)
    fig.savefig(path, dpi=200)
    plt.close(fig)


def run_convergence(
    quick: bool = False,
    out_dir: Optional[Path] = None,
    fig_dir: Optional[Path] = None,
) -> Dict[str, pd.DataFrame]:
    """Corre V4 completo. quick=True usa redes y réplicas pequeñas (solo para depurar)."""
    out_dir = Path(out_dir or RESULTS_DIR)
    fig_dir = Path(fig_dir or FIGURES_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    params = ModelParams()
    n_base, n_rep_max = (500, 30) if quick else (N_DEFAULT, 100)
    n_grid = (200, 400, 800) if quick else N_GRID
    rep_grid = (5, 10, 20, 30) if quick else REP_GRID

    metric_frames, curve_frames, ci_rows, var_rows = [], [], [], []

    # (a) muchas réplicas a N fijo -> ancho del IC vs nº de réplicas
    for net in NETWORKS:
        reps = run_replicates(net, params, n=n_base, n_rep=n_rep_max, mean_degree=MEAN_DEGREE)
        meta = dict(exp_id="V4", scenario=f"reps{n_rep_max}_N{n_base}", network=net, model="abm", n=n_base)
        mt = metrics_table(reps, **meta)
        metric_frames.append(mt)
        curve_frames.append(aggregate_curves(reps, **meta))
        for metric in METRICS_CI:
            ci = ci_vs_reps(mt[metric].to_numpy(), rep_grid)
            ci.insert(0, "metric", metric)
            ci.insert(0, "network", net)
            ci_rows.append(ci)

    # (b) 30 réplicas a distintos N -> variabilidad vs N
    for net in NETWORKS:
        for n in n_grid:
            reps = run_replicates(net, params, n=n, n_rep=N_REP if not quick else 10, mean_degree=MEAN_DEGREE)
            meta = dict(exp_id="V4", scenario=f"N{n}_{len(reps)}reps", network=net, model="abm", n=n)
            mt = metrics_table(reps, **meta)
            metric_frames.append(mt)
            curve_frames.append(aggregate_curves(reps, **meta))
            for metric in METRICS_CI:
                var_rows.append(
                    {"network": net, "metric": metric, "n": n,
                     "mean": float(mt[metric].mean()), "std": float(mt[metric].std(ddof=1))}
                )

    metrics_df = pd.concat(metric_frames, ignore_index=True)
    curves_df = pd.concat(curve_frames, ignore_index=True)
    ci_df = pd.concat(ci_rows, ignore_index=True)
    var_df = pd.DataFrame(var_rows)

    metrics_df.to_csv(out_dir / "V4_metrics.csv", index=False)
    curves_df.to_csv(out_dir / "V4_curves.csv", index=False)
    ci_df.to_csv(out_dir / "V4_ci_width.csv", index=False)
    var_df.to_csv(out_dir / "V4_variance_vs_N.csv", index=False)
    plot_ci_vs_reps(ci_df, fig_dir / "fig_V4_ic_vs_replicas.png")
    plot_variance_vs_n(var_df, fig_dir / "fig_V4_variabilidad_vs_N.png")
    return {"metrics": metrics_df, "curves": curves_df, "ci_width": ci_df, "variance": var_df}


def main() -> None:
    ap = argparse.ArgumentParser(description="V4: convergencia Monte Carlo del ABM")
    ap.add_argument("--quick", action="store_true", help="versión pequeña para depurar")
    args = ap.parse_args()
    out = run_convergence(quick=args.quick)
    ci = out["ci_width"]
    print(ci[ci.n_rep.isin([5, 30])].round(4).to_string(index=False))
    print(out["variance"].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
