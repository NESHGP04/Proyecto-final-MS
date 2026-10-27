"""Contrato compartido: métricas y agregación de resultados (implementación completa).

No lo modifiques sin avisar al grupo (docs/CONTRATO.md, "Cambios al contrato").
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from .params import SimResult

EPS_EXTINCT = 1e-3  # un rumor "se extingue" cuando I <= 0.1% de la población

METRIC_NAMES = ["peak_I", "t_peak", "reach", "believers_total", "t_extinct", "auc_I"]

# numpy >= 2 renombró trapz -> trapezoid; soportamos ambos
_trapezoid = getattr(np, "trapezoid", None) or np.trapz


def compute_metrics(res: SimResult, eps: float = EPS_EXTINCT) -> Dict[str, float]:
    """Métricas de una corrida.

    peak_I          máximo de I(t) (fracción de difusores simultáneos)
    t_peak          hora en la que ocurre peak_I
    reach           alcance total = cum_exposed al final (fracción que llegó a ver la noticia)
    believers_total fracción que alguna vez creyó y compartió = cum_believers al final
    t_extinct       primera hora, después de t_peak, con I <= eps (NaN si nunca ocurre)
    auc_I           integral de I(t) dt en persona-horas por habitante (exposición total a difusores)
    """
    i_peak = int(np.argmax(res.I))
    after = np.where(res.I[i_peak:] <= eps)[0]
    t_ext = float(res.t[i_peak + after[0]]) if len(after) else float("nan")
    return {
        "peak_I": float(res.I[i_peak]),
        "t_peak": float(res.t[i_peak]),
        "reach": float(res.cum_exposed[-1]),
        "believers_total": float(res.cum_believers[-1]),
        "t_extinct": t_ext,
        "auc_I": float(_trapezoid(res.I, res.t)),
    }


def metrics_table(results: List[SimResult], **meta) -> pd.DataFrame:
    """Una fila por réplica: columnas meta (scenario, network, ...) + replicate + métricas."""
    rows = []
    for k, res in enumerate(results):
        row = dict(meta)
        row["replicate"] = k
        row.update(compute_metrics(res))
        rows.append(row)
    return pd.DataFrame(rows)


def aggregate_curves(results: List[SimResult], **meta) -> pd.DataFrame:
    """Curvas agregadas sobre réplicas, en formato largo.

    Columnas: <meta...>, t, compartment, mean, lo, hi
    compartment en {S, E, I, R, cum_exposed, cum_believers}; lo/hi = percentiles 2.5 y 97.5.
    """
    t = results[0].t
    frames = []
    for comp in ["S", "E", "I", "R", "cum_exposed", "cum_believers"]:
        m = np.vstack([getattr(r, comp) for r in results])
        df = pd.DataFrame(
            {
                "t": t,
                "compartment": comp,
                "mean": m.mean(axis=0),
                "lo": np.percentile(m, 2.5, axis=0),
                "hi": np.percentile(m, 97.5, axis=0),
            }
        )
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    for key, val in reversed(list(meta.items())):
        out.insert(0, key, val)
    return out
