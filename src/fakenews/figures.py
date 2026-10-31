"""Figuras P3 desde CSV reproducibles, sin volver a simular.

python -m fakenews.figures --exp all [--results-dir results/quick]
Las bandas de trayectorias son percentiles 2.5–97.5 entre réplicas; las barras
para medias y reducciones son IC t de Student del 95 %. Etiquetas en español.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .experiments import (  # noqa: E402
    CURVES_COLUMNS, EXPERIMENTS, METRICS_COLUMNS, RESULTS_DIR,
    mean_ci, relative_reductions,
)

FIGURES_DIR = Path(__file__).resolve().parents[2] / "figures"
COMPARTMENT_COLORS = {"S": "#1f77b4", "E": "#e3ae00", "I": "#d62728", "R": "#53945b"}
NAMES = {"er": "Erdős–Rényi", "ba": "Barabási–Albert", "ws": "Watts–Strogatz", "mean_field": "ODE"}
STYLES = {"er": "-", "ba": "--", "ws": ":", "mean_field": "-."}
TARGET_COLORS = {"random": "#1f77b4", "degree": "#d62728"}
TARGET_NAMES = {"random": "Al azar", "degree": "Mayor grado"}


def _curve(ax, data: pd.DataFrame, label: str, *, style: str = "-", color: str = "#d62728") -> None:
    """Dibuja I(t) y su intervalo percentil del 95 % entre réplicas."""
    data = data[data.compartment == "I"].sort_values("t")
    ax.plot(data.t, data["mean"], label=label, color=color, ls=style)
    ax.fill_between(data.t, data.lo, data.hi, color=color, alpha=0.10)
    ax.set_xlabel("Tiempo (horas)")
    ax.set_ylabel("Difusores I (fracción de la población)")
    ax.grid(alpha=0.25)


def _mean_points(ax, data: pd.DataFrame, x: str, label: str, color: str) -> None:
    """Medias por valor de un parámetro con IC 95 % de la media."""
    xs, ys, errors = [], [], []
    for value, group in data.groupby(x, sort=True):
        mean, lo, hi, _ = mean_ci(group.reach)
        xs.append(value)
        ys.append(mean)
        errors.append([mean - lo, hi - mean])
    ax.errorbar(xs, ys, yerr=np.asarray(errors).T, fmt="o-", capsize=3, color=color, label=label)
    ax.set_ylabel("Alcance total (fracción de la población)")
    ax.grid(alpha=0.25)


def _baseline(ax, frame: pd.DataFrame) -> None:
    """Línea y franja de IC 95 % para el alcance sin intervención."""
    base = frame[frame.scenario == "sin_intervencion"]
    mean, lo, hi, _ = mean_ci(base.reach)
    ax.axhline(mean, color="gray", ls=":", label="Sin intervención")
    ax.axhspan(lo, hi, color="gray", alpha=0.1)


def _plot_e1(metrics, curves):
    """Compara todas las topologías con el campo medio."""
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for net, group in curves.groupby("network", sort=False):
        _curve(ax, group, NAMES[net], style=STYLES[net],
               color="#333333" if net == "mean_field" else COMPARTMENT_COLORS["I"])
    ax.set_title("E1: topología y difusión · bandas percentiles del 95 %")
    ax.legend()
    return [("topologias", fig)]


def _plot_e3(metrics, curves):
    """Alcance frente al retraso para cada intensidad de fact-checking."""
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.3), sharey=True)
    palette = plt.get_cmap("viridis")
    for ax, net in zip(axes, ("er", "ba", "mean_field")):
        frame = metrics[metrics.network == net]
        for i, (delta, group) in enumerate(frame[frame.delta > 0].groupby("delta")):
            _mean_points(ax, group, "t_start", f"δ={delta:g} h⁻¹", palette(i / 3))
        _baseline(ax, frame)
        ax.set_xlabel("Inicio del fact-checking (horas)")
        ax.set_title(NAMES[net])
        ax.legend(fontsize=8)
    fig.suptitle("E3: alcance y retraso del fact-checking · IC 95 % de la media")
    return [("alcance_vs_retraso", fig)]


def _plot_e4(metrics, curves):
    """Compara silencio aleatorio y dirigido a las 12 horas."""
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.3), sharey=True)
    for ax, net in zip(axes, ("er", "ba", "ws")):
        frame = metrics[metrics.network == net].copy()
        frame["porcentaje"] = frame.silence_frac * 100
        for target in ("random", "degree"):
            _mean_points(ax, frame[(frame.silence_frac > 0) & (frame.targeting == target)],
                         "porcentaje", TARGET_NAMES[target], TARGET_COLORS[target])
        _baseline(ax, frame)
        ax.set_xlabel("Nodos silenciados (% de la red)")
        ax.set_title(NAMES[net])
        ax.legend(fontsize=8)
    fig.suptitle("E4: silencio a las 12 h · IC 95 % de la media")
    return [("silencio", fig)]


def _plot_e5(metrics, curves):
    """Efecto de cobertura, targeting y momento del prebunking."""
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharey=True)
    for row, net in enumerate(("er", "ba")):
        for col, t in enumerate((0, 12)):
            ax = axes[row, col]
            frame = metrics[metrics.network == net].copy()
            frame["porcentaje"] = frame.prebunk_frac * 100
            for target in ("random", "degree"):
                active = frame[(frame.prebunk_frac > 0) & (frame.t_start == t) & (frame.targeting == target)]
                _mean_points(ax, active, "porcentaje", TARGET_NAMES[target], TARGET_COLORS[target])
            _baseline(ax, frame)
            ax.set_xlabel("Nodos seleccionados para prebunking (% de la red)")
            ax.set_title(f"{NAMES[net]} · inicio {t} h")
            ax.legend(fontsize=8)
    fig.suptitle("E5: prebunking · IC 95 % de la media")
    return [("prebunking", fig)]


def _plot_e6(metrics, curves):
    """Trayectorias y pico/tiempo del pico según el origen de la noticia."""
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.3), sharey=True)
    for ax, net in zip(axes, ("er", "ba", "ws")):
        for scenario, group in curves[curves.network == net].groupby("scenario"):
            hub = scenario == "origen_hub"
            _curve(ax, group, "Origen hub" if hub else "Origen al azar", style="--" if hub else "-")
        ax.set_title(NAMES[net])
        ax.legend(fontsize=8)
    fig.suptitle("E6: origen de la noticia · bandas percentiles del 95 %")
    summary, axs = plt.subplots(1, 2, figsize=(10, 4.4))
    for ax, metric, ylabel in zip(axs, ("peak_I", "t_peak"),
                                ("Pico de difusores (fracción)", "Hora del pico (horas)")):
        for offset, strategy, color, label in ((-0.12, "random", "#1f77b4", "Origen al azar"),
                                                (0.12, "hub", "#d62728", "Origen hub")):
            for i, net in enumerate(("er", "ba", "ws")):
                values = metrics[(metrics.network == net) & (metrics.seed_strategy == strategy)][metric]
                mean, lo, hi, _ = mean_ci(values)
                ax.errorbar(i + offset, mean, yerr=[[mean - lo], [hi - mean]], fmt="o", capsize=4,
                            color=color, label=label if i == 0 else None)
        ax.set_xticks(range(3), ["ER", "BA", "WS"])
        ax.set_xlabel("Topología de la red")
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
    summary.suptitle("E6: altura y momento del pico · IC 95 % de la media")
    return [("origen_curvas", fig), ("origen_picos", summary)]


def _plot_e7(metrics, curves):
    """Reducción relativa; fact-checking se muestra como referencia sin costo equiparado."""
    reductions = relative_reductions(metrics)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    order = ("silencio_random_5pct", "silencio_degree_5pct", "prebunk_random_5pct",
             "prebunk_degree_5pct", "mejor_factcheck")
    labels = ("Silencio\nal azar", "Silencio\npor grado", "Prebunking\nal azar",
              "Prebunking\npor grado", "Fact-checking*\n(referencia)")
    for ax, net in zip(axes, ("er", "ba")):
        frame = reductions[reductions.network == net]
        for i, scenario in enumerate(order):
            group = frame[frame.scenario == scenario]
            mean, lo, hi, _ = mean_ci(group.relative_reduction)
            ax.bar(i, 100 * mean, color="#888888" if i == 4 else "#d62728" if i % 2 else "#1f77b4", alpha=0.8)
            ax.errorbar(i, 100 * mean, yerr=[[100 * (mean - lo)], [100 * (hi - mean)]], fmt="none", capsize=4, color="black")
        ax.axhline(0, color="gray", lw=1)
        ax.set_xticks(range(len(order)), labels, fontsize=8)
        ax.set_xlabel("Estrategia de intervención")
        ax.set_ylabel("Reducción relativa del alcance (%)")
        ax.set_title(NAMES[net])
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle("E7: 5 % de nodos a las 12 h · IC 95 % de la reducción media")
    details = metrics[metrics.scenario == "mejor_factcheck"].drop_duplicates("network")
    params = "; ".join(f"{r.network.upper()}: t={r.t_start:g} h, δ={r.delta:g} h⁻¹" for r in details.itertuples())
    fig.text(0.5, 0.015, f"*Menor alcance medio en E3 ({params}). Su costo no está equiparado al 5 % de nodos.",
             ha="center", fontsize=8)
    return [("reduccion_relativa", fig)]


PLOTTERS = {"E1": _plot_e1, "E3": _plot_e3, "E4": _plot_e4,
            "E5": _plot_e5, "E6": _plot_e6, "E7": _plot_e7}


def generate_figures(exp_id: str, *, results_dir: Path = RESULTS_DIR,
                     figures_dir: Optional[Path] = None) -> list:
    """Lee el contrato de CSV y guarda PNG a 200 dpi. Rechaza datos mock."""
    if exp_id not in PLOTTERS:
        raise ValueError(f"Experimento desconocido: {exp_id}")
    results_dir = Path(results_dir)
    directory = Path(figures_dir) if figures_dir is not None else FIGURES_DIR
    metrics = pd.read_csv(results_dir / f"{exp_id}_metrics.csv")
    curves = pd.read_csv(results_dir / f"{exp_id}_curves.csv")
    if not set(METRICS_COLUMNS).issubset(metrics) or not set(CURVES_COLUMNS).issubset(curves):
        raise ValueError("Los CSV no cumplen las columnas del contrato 4.5")
    if "backend" not in metrics or not metrics.backend.eq("real").all():
        raise ValueError("Las figuras científicas requieren resultados del backend real")
    is_quick = "quick" in metrics and metrics.quick.astype(str).str.lower().eq("true").any()
    if figures_dir is None and is_quick:
        directory = directory / "quick"
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, fig in PLOTTERS[exp_id](metrics, curves):
        if is_quick:
            fig.text(0.99, 0.99, "PRUEBA RÁPIDA: N=1000, 5 réplicas", ha="right", va="top", fontsize=8)
        fig.tight_layout(rect=(0, 0.06 if exp_id == "E7" else 0, 1, 0.95))
        path = directory / f"fig_{exp_id}_{name}.png"
        fig.savefig(path, dpi=200)
        plt.close(fig)
        paths.append(path)
    return paths


def main() -> None:
    """CLI para regenerar figuras a partir de resultados existentes."""
    parser = argparse.ArgumentParser(description="Figuras de resultados P3")
    parser.add_argument("--exp", choices=[*EXPERIMENTS, "all"], required=True)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--figures-dir", type=Path)
    args = parser.parse_args()
    for exp_id in EXPERIMENTS if args.exp == "all" else [args.exp]:
        for path in generate_figures(exp_id, results_dir=args.results_dir, figures_dir=args.figures_dir):
            print(path)


if __name__ == "__main__":
    main()
