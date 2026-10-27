"""Corredor de experimentos E1, E3-E7 y escritura de resultados. DUEÑO: Juan Francisco (P3).

Uso previsto:  python -m fakenews.experiments --exp E3 [--quick]
Escribe results/<EXP>_curves.csv y results/<EXP>_metrics.csv (formato en docs/CONTRATO.md, sección 4.5).
"""
from __future__ import annotations

from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"


def run_experiment(exp_id: str, quick: bool = False) -> None:
    """Ejecuta un experimento del catálogo (contrato, sección 5) y guarda sus CSV.

    quick=True: N=1000 y 5 réplicas, para depurar rápido.
    """
    raise NotImplementedError("P3 (Juan Francisco): implementar")
