"""Catálogo P3, ejecución reproducible y estadística de E1, E3–E7.

python -m fakenews.experiments --exp E3 [--quick] [--backend mock]
python -m fakenews.experiments --exp all --figures

Los resultados finales usan los modelos reales, N_DEFAULT y N_REP. Las corridas
quick y mock se guardan en subdirectorios para no sobrescribir resultados finales.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

from .abm import simulate_abm
from .metrics import METRIC_NAMES, aggregate_curves, metrics_table
from .mock import mock_result
from .networks import build_network
from .ode_model import simulate_ode
from .params import (
    MEAN_DEGREE, N_DEFAULT, N_REP, SEED0, T_MAX,
    Intervention, ModelParams,
)

RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
METRICS_COLUMNS = ["exp_id", "scenario", "network", "model", "replicate", *METRIC_NAMES]
CURVES_COLUMNS = ["exp_id", "scenario", "network", "model", "t", "compartment", "mean", "lo", "hi"]
NETWORKS = ("er", "ba", "ws")
FACTCHECK_TIMES = (0, 6, 12, 24, 48)
FACTCHECK_DELTAS = (0.05, 0.1, 0.2, 0.4)
SILENCE_FRACS = (0.01, 0.02, 0.05, 0.10)
PREBUNK_FRACS = (0.05, 0.10, 0.20, 0.40)
TARGETINGS = ("random", "degree")


@dataclass(frozen=True)
class Scenario:
    """Una condición experimental; mean_field se ejecuta una sola vez con el ODE."""

    network: str
    intervention: Optional[Intervention] = None
    seed_strategy: str = "random"
    source_scenario: str = ""

    @property
    def name(self) -> str:
        """Identificador legible compartido por métricas y curvas."""
        if self.intervention is not None:
            return self.intervention.name
        return "origen_hub" if self.seed_strategy == "hub" else "sin_intervencion"


def _catalogue() -> dict:
    """Construye exactamente las rejillas de la sección 5, con controles sin intervención."""
    e3 = [Scenario(net) for net in (*NETWORKS[:2], "mean_field")]
    e4 = [Scenario(net) for net in NETWORKS]
    e5 = [Scenario(net) for net in NETWORKS[:2]]
    for net in (*NETWORKS[:2], "mean_field"):
        for t in FACTCHECK_TIMES:
            for delta in FACTCHECK_DELTAS:
                e3.append(Scenario(net, Intervention(
                    name=f"factcheck_t{t}_d{delta:g}", t_start=t, delta=delta,
                )))
    for net in NETWORKS:
        for frac in SILENCE_FRACS:
            for target in TARGETINGS:
                e4.append(Scenario(net, Intervention(
                    name=f"silencio_{target}_{100 * frac:g}pct", t_start=12,
                    silence_frac=frac, targeting=target,
                )))
    for net in NETWORKS[:2]:
        for t in (0, 12):
            for frac in PREBUNK_FRACS:
                for target in TARGETINGS:
                    e5.append(Scenario(net, Intervention(
                        name=f"prebunk_{target}_{100 * frac:g}pct_t{t}", t_start=t,
                        prebunk_frac=frac, targeting=target,
                    )))
    # E7 no fija redes ni tiempo para el presupuesto por nodos. Se comparan ER/BA,
    # comunes a E3–E5, a t=12 para ambas acciones. Fact-checking se selecciona de E3;
    # no se equipara una tasa (1/h) con un costo monetario o con un % de cuentas.
    e7 = [Scenario(net) for net in NETWORKS[:2]]
    for net in NETWORKS[:2]:
        for target in TARGETINGS:
            e7.extend([
                Scenario(net, Intervention(
                    name=f"silencio_{target}_5pct", t_start=12,
                    silence_frac=0.05, targeting=target,
                )),
                Scenario(net, Intervention(
                    name=f"prebunk_{target}_5pct", t_start=12,
                    prebunk_frac=0.05, targeting=target,
                )),
            ])
    return {
        "E1": tuple(Scenario(net) for net in (*NETWORKS, "mean_field")),
        "E3": tuple(e3), "E4": tuple(e4), "E5": tuple(e5),
        "E6": tuple(Scenario(net, seed_strategy=s) for net in NETWORKS for s in ("random", "hub")),
        "E7": tuple(e7),
    }


EXPERIMENTS = _catalogue()


def mean_ci(values) -> tuple:
    """Media e IC t de Student del 95 %; una corrida determinista da ancho cero."""
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if not len(x):
        return np.nan, np.nan, np.nan, 0
    mean = float(x.mean())
    half = float(stats.t.ppf(0.975, len(x) - 1) * stats.sem(x)) if len(x) > 1 else 0.0
    return mean, mean - half, mean + half, len(x)


def summarize_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    """IC de la media; no confundir con las bandas percentiles de las trayectorias."""
    rows = []
    keys = ["exp_id", "scenario", "network", "model"]
    for group, frame in metrics.groupby(keys, sort=False):
        for metric in METRIC_NAMES:
            mean, lo, hi, count = mean_ci(frame[metric])
            rows.append(dict(zip(keys, group), metric=metric, mean=mean, lo=lo, hi=hi, n=count))
    return pd.DataFrame(rows)


def relative_reductions(metrics: pd.DataFrame) -> pd.DataFrame:
    """1 - alcance/base por réplica, con IC t del 95 % sobre esas reducciones.

    Se emparejan red, modelo y réplica: comparten grafo y semilla, aunque las
    intervenciones pueden consumir distintos números aleatorios en la dinámica.
    """
    keys = ["network", "model", "replicate"]
    base = metrics[metrics.scenario == "sin_intervencion"][keys + ["reach"]]
    if base.duplicated(keys).any():
        raise ValueError("Hay más de una línea base por red, modelo y réplica")
    data = metrics[metrics.scenario != "sin_intervencion"].merge(
        base.rename(columns={"reach": "base_reach"}), on=keys, validate="many_to_one",
    )
    if len(data) != (metrics.scenario != "sin_intervencion").sum():
        raise ValueError("Faltan réplicas de la línea base")
    if (data.base_reach <= 0).any():
        raise ValueError("No se puede dividir por alcance base cero")
    data["relative_reduction"] = 1 - data.reach / data.base_reach
    return data


def compare_samples(a, b, hypothesis: str, comparison: str, metric: str,
                    network: str = "", direction: str = "greater") -> dict:
    """Mann–Whitney bilateral y efecto rank-biserial (positivo si A > B).

    Requiere muestras independientes. hypothesis_tests usa réplicas disjuntas
    para evitar comparar dos condiciones sobre el mismo grafo aleatorio.
    No rechazar H0 no demuestra igualdad: se reporta como evidencia insuficiente.
    """
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    if not len(a) or not len(b):
        raise ValueError("Se necesitan dos muestras no vacías")
    # Con todos los valores iguales la varianza de rangos es cero: H0 no se rechaza.
    if np.all(a == a[0]) and np.all(b == a[0]):
        statistic, p_value = len(a) * len(b) / 2, 1.0
    else:
        test = stats.mannwhitneyu(a, b, alternative="two-sided", method="asymptotic")
        statistic, p_value = float(test.statistic), float(test.pvalue)
    effect = 2 * statistic / (len(a) * len(b)) - 1
    sign = 1 if direction == "greater" else -1
    verdict = "evidencia_insuficiente"
    if p_value < 0.05:
        verdict = "confirma" if effect * sign > 0 else "refuta"
    return dict(hypothesis=hypothesis, comparison=comparison, network=network,
                metric=metric, test="Mann-Whitney bilateral exploratorio",
                n_a=len(a), n_b=len(b), mean_a=float(a.mean()), mean_b=float(b.mean()),
                u=statistic, p_value=p_value,
                rank_biserial=effect, expected_direction=direction, verdict=verdict)


def hypothesis_tests(exp_id: str, metrics: pd.DataFrame) -> pd.DataFrame:
    """Comparaciones H1–H5; H2 incluye pendientes tempranas y tardías del retraso.

    H1 usa pico y 1/t_peak como velocidad. H2 requiere aumento y cambio de
    pendiente, por lo que ningún contraste aislado demuestra toda la hipótesis.
    H3 en ER espera ausencia de ventaja: no significancia no confirma igualdad.
    A usa réplicas pares y B impares (15 y 15 en la corrida completa), pues las
    condiciones comparten red/semilla. Los IC descriptivos usan todas las réplicas.
    Se aplica Holm a los p de todas las comparaciones del experimento.
    """
    data = metrics[metrics.model == "abm"]
    rows = []

    def add(a, b, hyp, label, metric, net="", direction="greater"):
        rows.append(compare_samples(np.asarray(a)[::2], np.asarray(b)[1::2],
                                    hyp, label, metric, net, direction))

    if exp_id == "E1":
        ba = data[data.network == "ba"]
        for net in ("er", "ws"):
            other = data[data.network == net]
            add(ba.peak_I, other.peak_I, "H1", f"BA vs {net.upper()}", "peak_I")
            add(1 / ba.t_peak.clip(lower=1), 1 / other.t_peak.clip(lower=1),
                "H1", f"BA vs {net.upper()}", "velocidad_1_sobre_t_peak")
    elif exp_id == "E3":
        for (net, delta), group in data[data.delta > 0].groupby(["network", "delta"]):
            grid = group.pivot(index="replicate", columns="t_start", values="reach")
            for earlier, later in zip(FACTCHECK_TIMES, FACTCHECK_TIMES[1:]):
                add(grid[later], grid[earlier], "H2",
                    f"retraso {later} vs {earlier}; delta={delta:g}", "reach", net)
            # No linealidad: pendientes de intervalos con distinta amplitud, en fracción/h.
            early, late = (grid[6] - grid[0]) / 6, (grid[48] - grid[24]) / 24
            row = compare_samples(late.to_numpy()[::2], early.to_numpy()[1::2], "H2", f"pendiente tardía vs temprana; delta={delta:g}",
                                  "pendiente_alcance_por_hora", net)
            row["verdict"] = "confirma" if row["p_value"] < 0.05 else "evidencia_insuficiente"
            row["expected_direction"] = "different"
            rows.append(row)
    elif exp_id in ("E4", "E5"):
        frac_col = "silence_frac" if exp_id == "E4" else "prebunk_frac"
        hyp = "H3" if exp_id == "E4" else "H4"
        active = data[data[frac_col] > 0]
        for (net, frac, t), group in active.groupby(["network", frac_col, "t_start"]):
            a = group[group.targeting == "degree"].reach
            b = group[group.targeting == "random"].reach
            row = compare_samples(a.to_numpy()[::2], b.to_numpy()[1::2], hyp, f"grado vs azar; frac={frac:g}; t={t:g}",
                                  "reach", net, "less")
            if hyp == "H3" and net == "er":
                row["verdict"] = "refuta" if row["p_value"] < 0.05 and row["rank_biserial"] < 0 else "evidencia_insuficiente"
                row["expected_direction"] = "sin_ventaja_de_grado"
            if hyp == "H3" and net == "ws":
                row["hypothesis"] = "exploratoria"
            rows.append(row)
    elif exp_id == "E6":
        for net, group in data.groupby("network"):
            hub, rnd = group[group.seed_strategy == "hub"], group[group.seed_strategy == "random"]
            add(hub.peak_I, rnd.peak_I, "H5", "origen hub vs azar", "peak_I", net)
            add(hub.t_peak, rnd.t_peak, "H5", "origen hub vs azar", "t_peak", net, "less")
    elif exp_id == "E7":
        for (net, target), group in data[data.silence_frac + data.prebunk_frac > 0].groupby(["network", "targeting"]):
            add(group[group.silence_frac > 0].reach, group[group.prebunk_frac > 0].reach,
                "exploratoria", f"silencio vs prebunk; {target}", "reach", net, "less")
    out = pd.DataFrame(rows)
    if not out.empty:
        order = np.argsort(out.p_value.to_numpy())
        corrected = np.minimum(1, np.maximum.accumulate(
            out.p_value.to_numpy()[order] * np.arange(len(out), 0, -1),
        ))
        adjusted = np.empty(len(out))
        adjusted[order] = corrected
        out["p_value_holm"] = adjusted
        out.loc[out.p_value_holm >= 0.05, "verdict"] = "evidencia_insuficiente"
        out["sampling"] = "A: replicas pares; B: replicas impares"
    return out


def _best_factcheck(directory: Path, quick: bool, backend: str) -> list:
    """Escoge el menor alcance medio de E3 por red; desempate por inicio y delta.

    Es selección descriptiva en la misma rejilla, no validación fuera de muestra.
    """
    path = directory / "E3_metrics.csv"
    if not path.exists():
        run_experiment("E3", quick, backend=backend, output_dir=directory)
    data = pd.read_csv(path)
    expected_n, expected_reps = (1000, 5) if quick else (N_DEFAULT, N_REP)
    if (not {"backend", "n", "n_rep", "delta", "t_start", "model"}.issubset(data.columns)
            or not data.backend.eq(backend).all() or not data.n.eq(expected_n).all()
            or not data.loc[data.model == "abm", "n_rep"].eq(expected_reps).all()):
        raise ValueError("E3 no coincide con el backend/tamaño de E7; vuelve a ejecutar E3")
    selected = []
    for net in NETWORKS[:2]:
        fc = data[(data.network == net) & (data.delta > 0)]
        means = fc.groupby(["scenario", "t_start", "delta"], as_index=False).reach.mean()
        if means.empty:
            raise ValueError(f"E3 no contiene fact-checking para {net}")
        best = means.sort_values(["reach", "t_start", "delta"]).iloc[0]
        selected.append(Scenario(net, Intervention(
            name="mejor_factcheck", t_start=float(best.t_start), delta=float(best.delta),
        ), source_scenario=str(best.scenario)))
    return selected


def run_experiment(exp_id: str, quick: bool = False, *, backend: str = "real",
                   output_dir: Optional[Path] = None) -> None:
    """Ejecuta E1/E3–E7 y escribe el contrato 4.5 más resúmenes y contrastes.

    Conserva los dos argumentos públicos. Las opciones adicionales son de palabra
    clave. Mock verifica únicamente el pipeline: no modela silencio/prebunk/origen.
    """
    exp_id = exp_id.upper()
    if exp_id not in EXPERIMENTS:
        raise ValueError(f"Experimento desconocido: {exp_id}. Opciones: {', '.join(EXPERIMENTS)}")
    if backend not in ("real", "mock"):
        raise ValueError("backend debe ser 'real' o 'mock'")
    directory = Path(output_dir) if output_dir is not None else RESULTS_DIR
    if output_dir is None and (quick or backend == "mock"):
        directory = directory / ("mock_quick" if quick and backend == "mock" else "quick" if quick else "mock")
    directory.mkdir(parents=True, exist_ok=True)
    n, n_rep = (1000, 5) if quick else (N_DEFAULT, N_REP)
    scenarios = list(EXPERIMENTS[exp_id])
    if exp_id == "E7":
        scenarios.extend(_best_factcheck(directory, quick, backend))
    params = ModelParams()
    metric_frames, curve_frames, graph_cache = [], [], {}
    for index, scenario in enumerate(scenarios, 1):
        ode = scenario.network == "mean_field"
        iv = scenario.intervention or Intervention()
        results = []
        for replicate in range(1 if ode else n_rep):
            seed = SEED0 + replicate
            if backend == "mock":
                result = mock_result(params, scenario.intervention, seed=seed, t_max=T_MAX,
                                     mean_degree=MEAN_DEGREE)
            elif ode:
                result = simulate_ode(params, scenario.intervention, mean_degree=MEAN_DEGREE, t_max=T_MAX)
            else:
                key = scenario.network, seed
                if key not in graph_cache:
                    graph_cache[key] = build_network(scenario.network, n=n, mean_degree=MEAN_DEGREE, seed=seed)
                result = simulate_abm(graph_cache[key], params, scenario.intervention, seed=seed,
                                      t_max=T_MAX, seed_strategy=scenario.seed_strategy)
            result.check()
            results.append(result)
        meta = dict(exp_id=exp_id, scenario=scenario.name, network=scenario.network,
                    model="ode" if ode else "abm")
        extras = dict(asdict(params), t_start=iv.t_start, delta=iv.delta,
                      silence_frac=iv.silence_frac, prebunk_frac=iv.prebunk_frac,
                      targeting=iv.targeting, seed_strategy=scenario.seed_strategy,
                      n=n, n_rep=1 if ode else n_rep, mean_degree=MEAN_DEGREE,
                      seed0=SEED0, t_max=T_MAX, backend=backend, quick=quick,
                      source_scenario=scenario.source_scenario)
        mt = metrics_table(results, **meta)
        ct = aggregate_curves(results, **meta)
        for key, value in extras.items():
            mt[key] = value
        mt["seed"] = [SEED0 + r for r in range(len(results))]
        metric_frames.append(mt)
        curve_frames.append(ct)
        print(f"{exp_id} [{index}/{len(scenarios)}] {scenario.network}: {scenario.name}", flush=True)
    metrics = pd.concat(metric_frames, ignore_index=True)
    curves = pd.concat(curve_frames, ignore_index=True)
    metrics.to_csv(directory / f"{exp_id}_metrics.csv", index=False)
    curves.to_csv(directory / f"{exp_id}_curves.csv", index=False, float_format="%.9g")
    summarize_metrics(metrics).to_csv(directory / f"{exp_id}_summary.csv", index=False)
    # Un mock no produce evidencia científica: se omiten IC derivados y contrastes.
    if backend == "real":
        tests = hypothesis_tests(exp_id, metrics)
        tests.to_csv(directory / f"{exp_id}_comparisons.csv", index=False)
        if exp_id in ("E3", "E4", "E5", "E7"):
            relative_reductions(metrics).to_csv(directory / f"{exp_id}_reductions.csv", index=False)


def main() -> None:
    """CLI para una rejilla o todos los experimentos P3, con figuras opcionales."""
    parser = argparse.ArgumentParser(description="Experimentos P3 de propagación de fake news")
    parser.add_argument("--exp", required=True, choices=[*EXPERIMENTS, "all"])
    parser.add_argument("--quick", action="store_true", help="N=1000 y 5 réplicas en results/quick/")
    parser.add_argument("--backend", choices=("real", "mock"), default="real")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--figures", action="store_true", help="Generar también las figuras del experimento")
    args = parser.parse_args()
    if args.figures and args.backend == "mock":
        parser.error("Las figuras científicas requieren --backend real")
    for exp_id in EXPERIMENTS if args.exp == "all" else [args.exp]:
        run_experiment(exp_id, args.quick, backend=args.backend, output_dir=args.output_dir)
        if args.figures:
            from .figures import generate_figures
            directory = args.output_dir or (RESULTS_DIR / "quick" if args.quick else RESULTS_DIR)
            generate_figures(exp_id, results_dir=directory)


if __name__ == "__main__":
    main()
