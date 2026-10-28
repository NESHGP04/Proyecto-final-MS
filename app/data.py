"""Capa de datos del dashboard. DUEÑO: Ernesto (P4).

Carga los CSV de results/ (formato del contrato, sección 4.5) y corre simulaciones con
respaldo a datos de demostración. Está separada de dashboard.py para probarla con pytest
sin levantar Streamlit.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from fakenews import abm, ode_model
from fakenews.metrics import aggregate_curves, metrics_table
from fakenews.mock import mock_result
from fakenews.params import Intervention, ModelParams, SEED0

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"

# Columnas mínimas del contrato 4.5; las columnas extra de parámetros se aceptan
METRICS_COLS = ["exp_id", "scenario", "network", "model", "replicate",
                "peak_I", "t_peak", "reach", "believers_total", "t_extinct", "auc_I"]
CURVES_COLS = ["exp_id", "scenario", "network", "model", "t", "compartment", "mean", "lo", "hi"]

INTERVENTION_KINDS = ("ninguna", "fact-checking", "silenciar", "prebunking")


@st.cache_data(show_spinner=False)
def _read_csv(path: str, mtime_ns: int) -> pd.DataFrame:
    """Lee un CSV. mtime_ns va en la llave de caché: si P3 regenera el archivo, se relee."""
    return pd.read_csv(path)


def _load(path: Path, required: List[str]) -> pd.DataFrame:
    df = _read_csv(str(path), path.stat().st_mtime_ns)
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: faltan columnas del contrato {missing}")
    return df


def load_metrics(exp_id: str, results_dir: Path = RESULTS_DIR) -> pd.DataFrame:
    """results/<EXP>_metrics.csv: una fila por réplica."""
    return _load(Path(results_dir) / f"{exp_id}_metrics.csv", METRICS_COLS)


def load_curves(exp_id: str, results_dir: Path = RESULTS_DIR) -> pd.DataFrame:
    """results/<EXP>_curves.csv: curvas agregadas en formato largo (mean, lo, hi)."""
    return _load(Path(results_dir) / f"{exp_id}_curves.csv", CURVES_COLS)


def list_experiments(results_dir: Path = RESULTS_DIR) -> List[str]:
    """Experimentos con AMBOS CSV. Sin caché: el directorio cambia cuando P3 corre experimentos."""
    d = Path(results_dir)
    ids = {p.name[: -len("_metrics.csv")] for p in d.glob("*_metrics.csv")}
    return sorted(i for i in ids if (d / f"{i}_curves.csv").exists())


def reach_summary(metrics: pd.DataFrame) -> pd.DataFrame:
    """Alcance medio por escenario con IC 95 % de la media (aprox. normal: media ± 1.96·EE).

    El ODE es determinista (una fila): su EE es NaN y se toma 0, así lo = hi = media.
    """
    g = metrics.groupby(["scenario", "network", "model"], sort=False)["reach"]
    out = g.agg(mean="mean", sem="sem", n="count").reset_index()
    half = 1.96 * out.pop("sem").fillna(0.0)
    out["lo"], out["hi"] = out["mean"] - half, out["mean"] + half
    return out


def make_intervention(
    kind: str, t_start: float, intensity: float, targeting: str = "random"
) -> Optional[Intervention]:
    """Traduce los controles de la barra lateral a una Intervention del contrato.

    intensity es delta (1/h) en fact-checking y fracción de nodos en silenciar/prebunking.
    El nombre sigue el estilo de los escenarios del contrato (p. ej. "factcheck_t12_d0.2").
    """
    if kind == "ninguna":
        return None
    if kind == "fact-checking":
        return Intervention(name=f"factcheck_t{t_start:g}_d{intensity:g}", t_start=t_start, delta=intensity)
    tag = f"{'deg' if targeting == 'degree' else 'rand'}_{intensity * 100:g}pct"
    if kind == "silenciar":
        return Intervention(name=f"silencio_{tag}", t_start=t_start, silence_frac=intensity, targeting=targeting)
    if kind == "prebunking":
        return Intervention(name=f"prebunk_{tag}", t_start=t_start, prebunk_frac=intensity, targeting=targeting)
    raise ValueError(f"Intervención desconocida: {kind!r}. Opciones: {INTERVENTION_KINDS}")


@st.cache_data(show_spinner=False, max_entries=32)
def simulate(
    kind: str,
    n: int,
    params: Dict,
    intervention: Optional[Dict] = None,
    seed_strategy: str = "random",
    n_rep: int = 10,
    use_mock: bool = False,
) -> Dict:
    """Corre n_rep réplicas del ABM y el ODE; devuelve todo en el formato de results/.

    params/intervention llegan como dict (asdict) para que la llave de caché sea estable.
    Si el ABM o el ODE reales aún no existen (NotImplementedError), o si use_mock=True, se usa
    mock_result y la fuente queda marcada "demo" para que la interfaz lo avise.

    Devuelve {"abm_curves", "abm_metrics", "ode_curves", "ode_metrics", "sources"};
    las entradas ode_* son None cuando el ODE no aplica (targeting="degree").
    """
    p = ModelParams(**params)
    iv = Intervention(**intervention) if intervention else None
    scenario = iv.name if iv else "sin_intervencion"
    sources = {"abm": "demo", "ode": "demo"}

    results = None
    if not use_mock:
        try:
            results = abm.run_replicates(kind, p, iv, n=n, n_rep=n_rep, seed_strategy=seed_strategy)
            sources["abm"] = "real"
        except NotImplementedError:
            pass
    if results is None:
        results = [mock_result(p, iv, seed=SEED0 + r) for r in range(n_rep)]

    ode = None
    if iv is not None and iv.targeting == "degree":
        # el ODE no ve la topología (contrato 3.1: targeting="degree" -> ValueError)
        sources["ode"] = "n/a"
    else:
        if not use_mock:
            try:
                ode = ode_model.simulate_ode(p, iv)
                sources["ode"] = "real"
            except NotImplementedError:
                pass
        if ode is None:
            ode = mock_result(p, iv, seed=SEED0)

    abm_meta = dict(scenario=scenario, network=kind, model="abm")
    ode_meta = dict(scenario=scenario, network="mean_field", model="ode")
    return {
        "abm_curves": aggregate_curves(results, **abm_meta),
        "abm_metrics": metrics_table(results, **abm_meta),
        "ode_curves": aggregate_curves([ode], **ode_meta) if ode is not None else None,
        "ode_metrics": metrics_table([ode], **ode_meta) if ode is not None else None,
        "sources": sources,
    }


@st.cache_data(show_spinner=False)
def demo_experiment() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Experimento de demostración (solo en memoria, nunca a disco) para la pestaña Comparar.

    Tres escenarios de fact-checking con mock_result; NO es un resultado del proyecto.
    """
    metrics, curves = [], []
    for delta in (0.0, 0.1, 0.3):
        iv = make_intervention("fact-checking", 12, delta) if delta else None
        res = [mock_result(ModelParams(), iv, seed=SEED0 + r) for r in range(5)]
        meta = dict(exp_id="DEMO", scenario=iv.name if iv else "sin_intervencion", network="er", model="mock")
        metrics.append(metrics_table(res, **meta))
        curves.append(aggregate_curves(res, **meta))
    return pd.concat(metrics, ignore_index=True), pd.concat(curves, ignore_index=True)
