"""Valores y tablas del informe, calculados directamente de results/*.csv (ninguna cifra se teclea a mano).

`valores()` devuelve un dict: claves escalares (para <<clave:formato>>) y claves `tabla_*` con tablas en Markdown.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
NET = {"er": "ER", "ba": "BA", "ws": "WS", "mean_field": "ODE", "complete": "completo"}


def _csv(name: str) -> pd.DataFrame:
    return pd.read_csv(RES / name)


def md_table(header: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f} %"


def pm(mean: float, hw: float, d: int = 1) -> str:
    return f"{100 * mean:.{d}f} ± {100 * hw:.{d}f}"


def valores() -> dict:
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from fakenews.ode_model import final_size
    from fakenews.params import ModelParams

    v: dict = {}
    d = ModelParams()
    v["r0_default"] = d.r0_ode()
    v["delta_star"] = d.beta_ode() * d.p_believe - d.gamma
    v["fs_default"] = 1 - final_size(d.r0_ode(), d.i0, d.p_believe)
    # cuánto subestiman 240 h el alcance límite del ODE cerca del umbral (R0 = 1.2)
    from dataclasses import replace
    from fakenews.ode_model import simulate_ode

    for i0, key in ((0.01, "hz_ode_i01"), (0.001, "hz_ode_i0001")):
        pr = replace(d, i0=i0, beta=1.2 * d.gamma / (d.p_believe * 10.0))
        v[key] = simulate_ode(pr, t_max=3000).cum_exposed[-1] - simulate_ode(pr, t_max=240).cum_exposed[-1]

    # ------------------------------------------------------------------ E1
    s1 = _csv("E1_summary.csv").set_index(["network", "metric"])
    for net, key in (("er", "er"), ("ba", "ba"), ("ws", "ws"), ("mean_field", "mf")):
        for metric, k in (("peak_I", "peak"), ("t_peak", "tpeak"), ("reach", "reach"),
                          ("believers_total", "bel"), ("auc_I", "auc")):
            r = s1.loc[(net, metric)]
            v[f"e1_{key}_{k}"], v[f"e1_{key}_{k}_lo"], v[f"e1_{key}_{k}_hi"] = r["mean"], r["lo"], r["hi"]
    v["tabla_e1"] = md_table(
        ["Red", "Pico de difusores (IC 95 %)", "Hora del pico (h)", "Alcance total (IC 95 %)", "Creyentes totales",
         "Difusores·hora (∫I dt)"],
        [[name, f"{v[f'e1_{k}_peak']:.4f} [{v[f'e1_{k}_peak_lo']:.4f}, {v[f'e1_{k}_peak_hi']:.4f}]",
          f"{v[f'e1_{k}_tpeak']:.1f}", f"{v[f'e1_{k}_reach']:.3f} [{v[f'e1_{k}_reach_lo']:.3f}, {v[f'e1_{k}_reach_hi']:.3f}]",
          f"{v[f'e1_{k}_bel']:.3f}", f"{v[f'e1_{k}_auc']:.2f}"]
         for name, k in (("Erdős–Rényi", "er"), ("Barabási–Albert", "ba"), ("Watts–Strogatz", "ws"),
                         ("ODE (campo medio)", "mf"))])

    def comps(exp: str) -> pd.DataFrame:
        return _csv(f"{exp}_comparisons.csv")

    def comp_table(df: pd.DataFrame, cols_label: str = "Comparación") -> str:
        rows = []
        for _, r in df.iterrows():
            p = r.p_value_holm
            rows.append([r.hypothesis, r.comparison, NET.get(r.network, "") if isinstance(r.network, str) else "",
                         r.metric.replace("velocidad_1_sobre_t_peak", "1/t_pico").replace("peak_I", "pico"),
                         f"{r.mean_a:.4f}", f"{r.mean_b:.4f}", "< 0.0001" if p < 1e-4 else f"{p:.4f}",
                         f"{r.rank_biserial:+.2f}", r.verdict.replace("_", " ")])
        return md_table(["Hip.", cols_label, "Red", "Métrica", "Media A", "Media B", "p (Holm)", "Efecto", "Veredicto"], rows)

    c1 = comps("E1")
    v["tabla_h1"] = comp_table(c1)

    # ------------------------------------------------------------------ E6
    s6 = _csv("E6_summary.csv").set_index(["scenario", "network", "metric"])
    rows = []
    for net in ("er", "ba", "ws"):
        for sc, lab in (("sin_intervencion", "Al azar"), ("origen_hub", "Hubs")):
            g = lambda m: s6.loc[(sc, net, m)]["mean"]
            rows.append([NET[net], lab, f"{g('peak_I'):.4f}", f"{g('t_peak'):.1f}", f"{g('reach'):.3f}"])
    v["tabla_e6"] = md_table(["Red", "Origen de la noticia", "Pico de difusores", "Hora del pico (h)", "Alcance total"], rows)
    for net in ("er", "ba", "ws"):
        for sc, lab in (("sin_intervencion", "rnd"), ("origen_hub", "hub")):
            for m, k in (("peak_I", "peak"), ("t_peak", "tpeak"), ("reach", "reach")):
                v[f"e6_{net}_{lab}_{k}"] = s6.loc[(sc, net, m)]["mean"]
    c6 = comps("E6")
    v["tabla_h5"] = comp_table(c6)

    # ------------------------------------------------------------------ E3
    r3 = _csv("E3_reductions.csv")
    base3 = _csv("E3_metrics.csv")
    for net in ("er", "ba"):
        v[f"e3_base_{net}"] = base3[(base3.network == net) & (base3.scenario == "sin_intervencion")].reach.mean()

    def red_table(df: pd.DataFrame, net: str) -> str:
        d = df[df.network == net]
        rows = []
        for t in (0, 6, 12, 24, 48):
            row = [f"{t} h"]
            for de in (0.05, 0.1, 0.2, 0.4):
                x = d[d.scenario == f"factcheck_t{t}_d{de:g}"].relative_reduction
                hw = 1.96 * x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else 0.0
                row.append(pm(x.mean(), hw))
            rows.append(row)
        return md_table(["Retraso t_start", "δ = 0.05", "δ = 0.10", "δ = 0.20", "δ = 0.40"], rows)

    v["tabla_e3_er"], v["tabla_e3_ba"] = red_table(r3, "er"), red_table(r3, "ba")
    for net in ("er", "ba"):
        for t in (0, 24, 48):
            for de in (0.1, 0.2, 0.4):
                x = r3[(r3.network == net) & (r3.scenario == f"factcheck_t{t}_d{de:g}")].relative_reduction.mean()
                v[f"e3_{net}_t{t}_d{str(de).replace('.', '')}"] = x
    # ODE (sin réplicas) para comparar con el ABM
    for t in (0, 48):
        for de in (0.1, 0.2):
            x = r3[(r3.network == "mean_field") & (r3.scenario == f"factcheck_t{t}_d{de:g}")].relative_reduction.mean()
            v[f"e3_mf_t{t}_d{str(de).replace('.', '')}"] = x

    c3 = comps("E3")
    h2rows = []
    for net in ("er", "ba"):
        for de in (0.05, 0.1, 0.2, 0.4):
            sub = c3[(c3.network == net) & c3.comparison.str.endswith(f"delta={de:g}")]
            def cell(label):
                r = sub[sub.comparison.str.startswith(label)]
                return "sí" if len(r) and r.iloc[0].verdict == "confirma" else "n.s."
            h2rows.append([NET[net], f"{de:g}", cell("retraso 6 vs 0"), cell("retraso 12 vs 6"), cell("retraso 24 vs 12"),
                           cell("retraso 48 vs 24"), cell("pendiente")])
    v["tabla_h2"] = md_table(["Red", "δ", "6 h vs 0 h", "12 h vs 6 h", "24 h vs 12 h", "48 h vs 24 h", "Pendiente tardía > temprana"],
                             h2rows)
    inc = c3[c3.metric == "reach"]
    v["h2_inc_total"], v["h2_inc_conf"] = len(inc), int((inc.verdict == "confirma").sum())
    late = inc[inc.comparison.str.startswith("retraso 48 vs 24")]
    v["h2_late_total"], v["h2_late_conf"] = len(late), int((late.verdict == "confirma").sum())
    slope = c3[c3.metric == "pendiente_alcance_por_hora"]
    v["h2_slope_total"], v["h2_slope_conf"] = len(slope), int((slope.verdict == "confirma").sum())

    # ------------------------------------------------------------------ E4
    r4 = _csv("E4_reductions.csv")
    rows = []
    for f in (1, 2, 5, 10):
        row = [f"{f} %"]
        for net in ("er", "ba", "ws"):
            for tg in ("random", "degree"):
                x = r4[(r4.network == net) & (r4.scenario == f"silencio_{tg}_{f}pct")].relative_reduction
                row.append(pm(x.mean(), 1.96 * x.std(ddof=1) / np.sqrt(len(x))))
        rows.append(row)
    v["tabla_e4"] = md_table(["Nodos silenciados", "ER azar", "ER grado", "BA azar", "BA grado", "WS azar", "WS grado"], rows)
    for net in ("er", "ba", "ws"):
        for tg in ("random", "degree"):
            v[f"e4_{net}_{tg}_10"] = r4[(r4.network == net) & (r4.scenario == f"silencio_{tg}_10pct")].relative_reduction.mean()
            v[f"e4_{net}_{tg}_5"] = r4[(r4.network == net) & (r4.scenario == f"silencio_{tg}_5pct")].relative_reduction.mean()
    c4 = comps("E4")
    v["tabla_h3"] = comp_table(c4)
    h3ba = c4[(c4.hypothesis == "H3") & (c4.network == "ba")]
    h3er = c4[(c4.hypothesis == "H3") & (c4.network == "er")]
    v["h3_ba_conf"], v["h3_ba_total"] = int((h3ba.verdict == "confirma").sum()), len(h3ba)
    v["h3_er_ref"], v["h3_er_total"] = int((h3er.verdict == "refuta").sum()), len(h3er)
    v["h3_er_ins"] = int((h3er.verdict == "evidencia_insuficiente").sum())

    # ------------------------------------------------------------------ E5
    r5 = _csv("E5_reductions.csv")

    def e5_table(t: int) -> str:
        rows = []
        for f in (5, 10, 20, 40):
            row = [f"{f} %"]
            for net in ("er", "ba"):
                for tg in ("random", "degree"):
                    x = r5[(r5.network == net) & (r5.scenario == f"prebunk_{tg}_{f}pct_t{t}")].relative_reduction
                    row.append(pm(x.mean(), 1.96 * x.std(ddof=1) / np.sqrt(len(x))))
            rows.append(row)
        return md_table(["Nodos inmunizados", "ER azar", "ER grado", "BA azar", "BA grado"], rows)

    v["tabla_e5_t0"], v["tabla_e5_t12"] = e5_table(0), e5_table(12)
    for net in ("er", "ba"):
        for tg in ("random", "degree"):
            for f in (5, 10, 20, 40):
                for tt in (0, 12):
                    v[f"e5_{net}_{tg}_{f}_t{tt}"] = r5[(r5.network == net) & (r5.scenario == f"prebunk_{tg}_{f}pct_t{tt}")].relative_reduction.mean()
    c5 = comps("E5")
    v["tabla_h4"] = comp_table(c5)
    v["h4_conf"], v["h4_total"] = int((c5.verdict == "confirma").sum()), len(c5)

    # ------------------------------------------------------------------ E7
    r7 = _csv("E7_reductions.csv")
    m7 = _csv("E7_metrics.csv")
    names = {"silencio_degree_5pct": "Silenciar 5 % de mayor grado", "silencio_random_5pct": "Silenciar 5 % al azar",
             "prebunk_degree_5pct": "Prebunking 5 % de mayor grado", "prebunk_random_5pct": "Prebunking 5 % al azar",
             "mejor_factcheck": "Mejor fact-checking de E3 (tasa, no presupuesto de nodos)"}
    rows = []
    for sc, lab in names.items():
        row = [lab]
        for net in ("er", "ba"):
            x = r7[(r7.network == net) & (r7.scenario == sc)].relative_reduction
            row.append(pm(x.mean(), 1.96 * x.std(ddof=1) / np.sqrt(len(x))))
        rows.append(row)
    v["tabla_e7"] = md_table(["Estrategia (inicio t = 12 h salvo fact-checking)", "ER: reducción del alcance (% ± IC 95 %)",
                              "BA: reducción del alcance (% ± IC 95 %)"], rows)
    for net in ("er", "ba"):
        x = m7[(m7.network == net) & (m7.scenario == "mejor_factcheck")].iloc[0]
        v[f"e7_{net}_fc_t"], v[f"e7_{net}_fc_d"] = x.t_start, x.delta
        for sc, k in (("silencio_degree_5pct", "sil_deg"), ("silencio_random_5pct", "sil_rnd"),
                      ("prebunk_degree_5pct", "pre_deg"), ("prebunk_random_5pct", "pre_rnd"), ("mejor_factcheck", "fc")):
            v[f"e7_{net}_{k}"] = r7[(r7.network == net) & (r7.scenario == sc)].relative_reduction.mean()
    v["tabla_e7_h"] = comp_table(comps("E7"))

    # ------------------------------------------------------------------ E2
    t2 = _csv("E2_tornado.csv")
    for p in ("beta", "sigma", "p_believe", "gamma", "i0"):
        for m, k in (("reach", "reach"), ("peak_I", "peak")):
            r = t2[(t2.param == p) & (t2.metric == m)].iloc[0]
            v[f"tor_{k}_{p}_m"], v[f"tor_{k}_{p}_p"] = r.rel_change_minus20, r.rel_change_plus20
        r = t2[(t2.param == p) & (t2.metric == "t_peak")].iloc[0]
        v[f"tor_tpeak_{p}_m"], v[f"tor_tpeak_{p}_p"] = r.rel_change_minus20, r.rel_change_plus20
    v["e2_base_reach"] = t2[t2.metric == "reach"].iloc[0].base
    v["e2_base_peak"] = t2[t2.metric == "peak_I"].iloc[0].base
    rows = []
    for p, lab in (("beta", "β (contagio)"), ("p_believe", "p (credulidad)"), ("gamma", "γ (pérdida de interés)"),
                   ("sigma", "σ (decisión)"), ("i0", "i0 (semillas)")):
        rows.append([lab] + [f"{100 * v[f'tor_{k}_{p}_{s}']:+.1f} %" for k in ("reach", "peak", "tpeak") for s in ("m", "p")])
    v["tabla_e2_tornado"] = md_table(
        ["Parámetro", "Alcance −20 %", "Alcance +20 %", "Pico −20 %", "Pico +20 %", "Hora del pico −20 %", "Hora del pico +20 %"], rows)
    av = _csv("E2_abm_vs_ode.csv")
    rows = []
    for (b, g), grp in av.groupby(["beta", "gamma"]):
        er, ba = grp[grp.network == "er"].iloc[0], grp[grp.network == "ba"].iloc[0]
        rows.append([f"{b:g}", f"{g:g}", f"{er.r0_ode:.2f}", f"{er.reach_ode:.3f}", f"{er.reach_abm:.3f}", f"{ba.reach_abm:.3f}",
                     f"{er.r_red:.2f}", f"{ba.r_red:.2f}"])
    v["tabla_e2_abm"] = md_table(["β", "γ", "R0 (ODE)", "Alcance ODE", "Alcance ABM-ER", "Alcance ABM-BA", "R_red ER", "R_red BA"], rows)
    def avp(net, b, g, col):
        return av[(av.network == net) & (np.isclose(av.beta, b)) & (np.isclose(av.gamma, g))].iloc[0][col]
    v["e2_def_rred_er"], v["e2_def_rred_ba"] = avp("er", .03, .1, "r_red"), avp("ba", .03, .1, "r_red")
    v["e2_def_er"], v["e2_def_ba"], v["e2_def_ode"] = avp("er", .03, .1, "reach_abm"), avp("ba", .03, .1, "reach_abm"), avp("er", .03, .1, "reach_ode")
    v["e2_sub_er"], v["e2_sub_ba"], v["e2_sub_ode"] = avp("er", .015, .1, "reach_abm"), avp("ba", .015, .1, "reach_abm"), avp("er", .015, .1, "reach_ode")
    v["e2_sub_r0"] = avp("er", .015, .1, "r0_ode")
    v["e2_sub_rred_ba"] = avp("ba", .015, .1, "r_red")
    g2 = _csv("E2_grid.csv")
    v["e2_grid_n"] = len(g2)
    v["e2_grid_r0_max"], v["e2_grid_r0_min"] = g2.r0.max(), g2.r0.min()
    v["e2_grid_sub_share"] = float((g2.r0 < 1).mean())
    m2 = _csv("E2_metrics.csv")
    pm_ = m2[m2.scenario.str.match(r"^p[0-9.]+$") & (m2.model == "ode")].sort_values("p_believe")
    v["e2_p_lo"], v["e2_p_hi"] = pm_.p_believe.iloc[0], pm_.p_believe.iloc[-1]
    v["e2_p_reach_lo"], v["e2_p_reach_hi"] = pm_.reach.iloc[0], pm_.reach.iloc[-1]
    v["e2_p_crit"] = d.gamma / d.beta_ode()   # p tal que R0 = 1

    # ------------------------------------------------------------------ V1 / V2
    e = _csv("V1_errors.csv").iloc[0]
    for k in e.index:
        v[f"v1_{k}"] = e[k]
    v["tabla_v1"] = md_table(
        ["Medida (N = 1000, 30 réplicas)", "Valor"],
        [["RMSE de I(t): ABM vs ODE", f"{e.rmse_I_abm_vs_ode:.4f}"],
         ["RMSE de I(t): ABM vs mapa discreto", f"{e.rmse_I_abm_vs_discreto:.4f}"],
         ["RMSE de I(t): mapa discreto vs ODE", f"{e.rmse_I_discreto_vs_ode:.4f}"],
         ["Error relativo del pico: ABM vs ODE", pct(e.peak_rel_err_abm_vs_ode)],
         ["Error relativo del pico: mapa discreto vs ODE", pct(e.peak_rel_err_discreto_vs_ode)],
         ["Diferencia de la hora del pico: ABM − ODE", f"{e.t_peak_diff_abm_vs_ode_h:+.0f} h"],
         ["Alcance: ABM (media ± d.e.)", f"{e.reach_abm_mean:.3f} ± {e.reach_abm_sd:.3f}"],
         ["Alcance: ODE / mapa discreto / analítico", f"{e.reach_ode:.3f} / {e.reach_discreto:.3f} / {e.reach_analitico:.3f}"],
         ["Réplicas sin brote", f"{int(e.n_rep_sin_brote)} de {int(e.n_rep)}"]])
    s2 = _csv("V2_summary.csv")
    v["tabla_v2"] = md_table(
        ["R0", "ABM completo: media [p2.5, p97.5]", "ODE (480 h)", "Analítico (i0 = 0.01)", "Analítico (i0 → 0)"],
        [[f"{r.r0:g}", f"{r.reach_abm_mean:.3f} [{r.reach_abm_lo:.3f}, {r.reach_abm_hi:.3f}]", f"{r.reach_ode_tmax:.3f}",
          f"{r.reach_analitico:.3f}", f"{r.reach_analitico_i0cero:.3f}"] for _, r in s2.iterrows()])
    r1 = s2[np.isclose(s2.r0, 1.0)].iloc[0]
    v["v2_10_lo"], v["v2_10_hi"] = r1.reach_abm_lo, r1.reach_abm_hi
    for r0 in (1.2, 1.5, 2.0, 4.0):
        row = s2[np.isclose(s2.r0, r0)].iloc[0]
        v[f"v2_{str(r0).replace('.', '')}_abm"], v[f"v2_{str(r0).replace('.', '')}_ana"] = row.reach_abm_mean, row.reach_analitico
    v["v2_max_abs_err_high"] = float((s2[s2.r0 >= 1.5].reach_abm_mean - s2[s2.r0 >= 1.5].reach_analitico).abs().max())
    v["v2_ode_vs_ana_max"] = float((s2.reach_ode_inf - s2.reach_analitico).abs().max())

    # ------------------------------------------------------------------ V3
    th = _csv("V3_threshold.csv").set_index("network")
    for net in ("er", "ba", "ws", "mean_field"):
        v[f"v3_pred_{net}"] = th.loc[net, "beta_c_pred"]
        if net != "mean_field":
            v[f"v3_emp_{net}"] = th.loc[net, "beta_c_emp"]
            v[f"v3_k2_{net}"] = th.loc[net, "k2_mean"]
            v[f"v3_kmax_{net}"] = th.loc[net, "k_max"]
            v[f"v3_exc_{net}"] = th.loc[net, "excess_degree"]
    v["tabla_v3a"] = md_table(
        ["Red", "⟨k²⟩", "k máx.", "Grado en exceso (⟨k²⟩−⟨k⟩)/⟨k⟩", "β crítico teórico (R_red = 1)", "β empírico (alcance 10 %)"],
        [[NET[n] if n != "mean_field" else "ODE (mezcla homogénea)",
          "—" if n == "mean_field" else f"{th.loc[n, 'k2_mean']:.1f}", "—" if n == "mean_field" else f"{th.loc[n, 'k_max']:.0f}",
          f"{th.loc[n, 'excess_degree']:.1f}", f"{th.loc[n, 'beta_c_pred']:.4f}",
          "—" if n == "mean_field" else f"{th.loc[n, 'beta_c_emp']:.4f}"] for n in ("er", "ba", "ws", "mean_field")])
    c3b = _csv("V3_comparisons.csv")
    rows = []
    for _, r in c3b.iterrows():
        rows.append([NET[r.network], r.metric.replace("peak_I", "pico").replace("t_5pct", "hora del 5 % expuesto")
                     .replace("t_peak", "hora del pico"), f"{r.mean_falsa:.4f}", f"{r.mean_verdadera:.4f}",
                     "< 0.0001" if r.p_value < 1e-4 else f"{r.p_value:.4f}", f"{r.rank_biserial:+.2f}",
                     r.verdict.replace("_", " ")])
    v["tabla_v3b"] = md_table(["Red", "Métrica", "Falsa (media)", "Verdadera (media)", "p", "Efecto", "¿Coincide con lo esperado?"], rows)
    get = lambda net, m, col: c3b[(c3b.network == net) & (c3b.metric == m)].iloc[0][col]
    for net in ("er", "ba"):
        for m, k in (("reach", "reach"), ("t_5pct", "t5"), ("peak_I", "peak"), ("t_peak", "tpeak")):
            v[f"v3b_{net}_{k}_f"], v[f"v3b_{net}_{k}_v"] = get(net, m, "mean_falsa"), get(net, m, "mean_verdadera")
    v["v3b_ok"], v["v3b_total"] = int((c3b.verdict == "consistente").sum()), len(c3b)
    hz = _csv("V3_horizon.csv").set_index("network")
    for net in hz.index:
        v[f"v3_hz_{net}_corto"], v[f"v3_hz_{net}_largo"] = hz.loc[net, "reach_corto"], hz.loc[net, "reach_largo"]
    v["v3_hz_largo_h"] = hz.t_max_largo.iloc[0]

    # ------------------------------------------------------------------ V4
    ci = _csv("V4_ci_width.csv")
    for net in ("er", "ba"):
        for m, k in (("reach", "reach"), ("peak_I", "peak")):
            for n in (5, 30, 100):
                row = ci[(ci.network == net) & (ci.metric == m) & (ci.n_rep == n)].iloc[0]
                v[f"v4_{net}_{k}_{n}"] = row.rel_half_width
    var = _csv("V4_variance_vs_N.csv")
    for net in ("er", "ba"):
        for n in (1000, 5000, 10000):
            v[f"v4_sd_{net}_{n}"] = var[(var.network == net) & (var.metric == "reach") & (var.n == n)].iloc[0]["std"]
    v["tabla_v4"] = md_table(
        ["Réplicas", "Alcance ER", "Alcance BA", "Pico ER", "Pico BA"],
        [[n] + [pct(v[f"v4_{net}_{k}_{n}"]) for k in ("reach", "peak") for net in ("er", "ba")] for n in (5, 30, 100)])
    return v


if __name__ == "__main__":
    vals = valores()
    print(len(vals), "valores")
    for k in sorted(vals):
        if not k.startswith("tabla"):
            print(k, vals[k])
