"""Dashboard interactivo del proyecto. DUEÑO: Ernesto (P4).

Ejecutar desde la raíz del repo:  streamlit run app/dashboard.py
Pestañas: Simulador (ABM + ODE), Comparar escenarios (results/) y Estructura de la red.
"""
from __future__ import annotations

from dataclasses import asdict

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.colors import qualitative

from data import (
    INTERVENTION_KINDS,
    demo_experiment,
    list_experiments,
    load_curves,
    load_metrics,
    make_intervention,
    reach_summary,
    simulate,
)
from fakenews import networks
from fakenews.params import MEAN_DEGREE, SEED0, ModelParams

# Interruptor de datos de demostración (valor inicial del toggle). Con False se usan ABM/ODE
# reales y el mock solo entra como respaldo mientras esos módulos no estén en main.
USE_MOCK = False

TOPOLOGIES = {"er": "Erdős–Rényi", "ba": "Barabási–Albert", "ws": "Watts–Strogatz"}
# Convención de color del contrato (sección 8): S azul, E amarillo, I rojo, R gris
COLORS = {"S": "#1f77b4", "E": "#e6b800", "I": "#d62728", "R": "#7f7f7f"}
NAMES = {"S": "S · susceptibles", "E": "E · expuestos", "I": "I · difusores", "R": "R · removidos"}
COMPARTMENTS = ["I", "S", "E", "R", "cum_exposed", "cum_believers"]


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def add_curve(fig: go.Figure, df: pd.DataFrame, name: str, color: str, dash: str = "solid") -> None:
    """Media como línea y banda lo-hi (percentiles 2.5-97.5) como relleno. Sin banda si lo == hi (ODE)."""
    if (df["hi"] - df["lo"]).abs().max() > 0:
        fig.add_trace(go.Scatter(x=df["t"], y=df["lo"], line=dict(width=0), showlegend=False,
                                 hoverinfo="skip", legendgroup=name))
        fig.add_trace(go.Scatter(x=df["t"], y=df["hi"], line=dict(width=0), fill="tonexty",
                                 fillcolor=rgba(color, 0.2), showlegend=False, hoverinfo="skip",
                                 legendgroup=name))
    fig.add_trace(go.Scatter(x=df["t"], y=df["mean"], name=name, legendgroup=name,
                             line=dict(color=color, dash=dash)))


def layout(fig: go.Figure, y_title: str = "Fracción de la población") -> go.Figure:
    fig.update_layout(xaxis_title="Tiempo (horas)", yaxis_title=y_title, hovermode="x unified",
                      margin=dict(t=30, b=10), legend=dict(orientation="h", y=-0.2))
    return fig


# ---------------------------------------------------------------- barra lateral
def sidebar():
    """Controles dentro de un form: la simulación solo corre al pulsar "Simular"."""
    d = ModelParams()
    with st.sidebar.form("controles"):
        st.header("Simulación")
        kind = st.selectbox("Topología", list(TOPOLOGIES), format_func=TOPOLOGIES.get)
        n = st.slider("N (nodos)", 500, 5000, 1000, step=500)
        n_rep = st.slider("Réplicas Monte Carlo", 5, 30, 10)
        seed_strategy = st.radio("Origen de la noticia (seed_strategy)", ["random", "hub"], horizontal=True)

        st.subheader("Parámetros SEIR-D (1/h)")
        beta = st.slider("beta · contagio por vecino difusor", 0.005, 0.06, d.beta, 0.005, format="%.3f")
        sigma = st.slider("sigma · tasa de decisión E → I/R", 0.05, 1.0, d.sigma, 0.05)
        p_believe = st.slider("p_believe · prob. de creer y compartir", 0.05, 0.95, d.p_believe, 0.05)
        gamma = st.slider("gamma · pérdida de interés I → R", 0.03, 0.3, d.gamma, 0.01)
        i0 = st.slider("i0 · fracción inicial de difusores", 0.001, 0.05, d.i0, 0.001, format="%.3f")

        st.subheader("Intervención")
        iv_kind = st.selectbox("Tipo", INTERVENTION_KINDS)
        t_start = st.slider("t_start (h)", 0, 72, 12)
        intensity = st.slider("Intensidad", 0.01, 0.5, 0.1, 0.01,
                              help="delta (1/h) en fact-checking; fracción de nodos en silenciar/prebunking")
        targeting = st.radio("targeting (silenciar / prebunking)", ["random", "degree"], horizontal=True)

        use_mock = st.toggle("Usar datos de demostración (USE_MOCK)", value=USE_MOCK)
        st.form_submit_button("Simular", type="primary")

    params = ModelParams(beta=beta, sigma=sigma, p_believe=p_believe, gamma=gamma, i0=i0)
    iv = make_intervention(iv_kind, t_start, intensity, targeting if iv_kind in ("silenciar", "prebunking") else "random")
    return dict(kind=kind, n=n, n_rep=n_rep, seed_strategy=seed_strategy, params=params, iv=iv, use_mock=use_mock)


# ---------------------------------------------------------------- pestaña 1
def tab_simulator(cfg: dict) -> None:
    with st.spinner(f"Simulando {cfg['n_rep']} réplicas en {TOPOLOGIES[cfg['kind']]} (N = {cfg['n']})…"):
        sim = simulate(cfg["kind"], cfg["n"], asdict(cfg["params"]), asdict(cfg["iv"]) if cfg["iv"] else None,
                       cfg["seed_strategy"], cfg["n_rep"], cfg["use_mock"])
    src = sim["sources"]
    if "demo" in src.values():
        st.warning(f"**Datos de demostración** (`fakenews.mock`): ABM {src['abm']}, ODE {src['ode']}. "
                   "El mock es un ODE con ruido: ignora la topología, N, seed_strategy, silenciar y "
                   "prebunking. No usar en resultados.")

    m = sim["abm_metrics"]
    c = st.columns(4)
    c[0].metric("Pico de difusores", f"{m['peak_I'].mean():.1%}")
    c[1].metric("Hora del pico", f"{m['t_peak'].mean():.0f} h")
    c[2].metric("Alcance", f"{m['reach'].mean():.1%}", help="cum_exposed final (media de las réplicas)")
    c[3].metric("R0 (campo medio)", f"{cfg['params'].r0_ode(MEAN_DEGREE):.2f}",
                help=f"ModelParams.r0_ode con ⟨k⟩ = {MEAN_DEGREE:g}")
    if sim["ode_metrics"] is not None:
        o = sim["ode_metrics"].iloc[0]
        st.caption(f"ODE: pico {o['peak_I']:.1%} · hora del pico {o['t_peak']:.0f} h · alcance {o['reach']:.1%}")
    else:
        st.caption("ODE no superpuesto: con targeting = degree el ODE no aplica (no ve la topología).")

    fig = go.Figure()
    for comp in "SEIR":
        add_curve(fig, sim["abm_curves"].query("compartment == @comp"), f"{NAMES[comp]} (ABM)", COLORS[comp])
        if sim["ode_curves"] is not None:
            add_curve(fig, sim["ode_curves"].query("compartment == @comp"), f"{comp} (ODE)", COLORS[comp], "dash")
    st.plotly_chart(layout(fig))
    st.caption("Línea continua: media del ABM con banda del 95 % de las réplicas. Línea discontinua: ODE. "
               "Clic en la leyenda para ocultar S y R y ver mejor E e I.")


# ---------------------------------------------------------------- pestaña 2
def tab_compare() -> None:
    exps = list_experiments()
    if exps:
        exp = st.selectbox("Experimento (results/)", exps)
        try:
            metrics, curves = load_metrics(exp), load_curves(exp)
        except ValueError as err:
            st.error(str(err))
            return
    else:
        st.warning("Aún no hay resultados en `results/` (los genera P3). Se muestra un experimento de "
                   "**datos de demostración**.")
        metrics, curves = demo_experiment()

    c1, c2, c3 = st.columns(3)
    nets_all = list(curves["network"].unique())
    scen_all = list(curves["scenario"].unique())
    nets = c1.multiselect("Redes", nets_all, default=nets_all)
    scens = c2.multiselect("Escenarios", scen_all, default=scen_all[:4])
    comp = c3.selectbox("Compartimento", COMPARTMENTS)
    if not nets or not scens:
        st.info("Elige al menos una red y un escenario.")
        return

    sel = curves[curves["scenario"].isin(scens) & curves["network"].isin(nets) & (curves["compartment"] == comp)]
    fig = go.Figure()
    groups = sel.groupby(["scenario", "network", "model"], sort=False)
    for k, ((s, nw, mo), g) in enumerate(groups):
        add_curve(fig, g, f"{s} · {nw} · {mo}", qualitative.Plotly[k % len(qualitative.Plotly)])
    st.plotly_chart(layout(fig))

    summ = reach_summary(metrics[metrics["scenario"].isin(scens) & metrics["network"].isin(nets)])
    bars = go.Figure()
    for nw, g in summ.groupby("network", sort=False):
        bars.add_trace(go.Bar(x=g["scenario"] + " · " + g["model"], y=g["mean"], name=nw,
                              error_y=dict(type="data", symmetric=False,
                                           array=g["hi"] - g["mean"], arrayminus=g["mean"] - g["lo"])))
    bars.update_layout(barmode="group", yaxis_title="Alcance (fracción de la población)",
                       margin=dict(t=30, b=10))
    st.plotly_chart(bars)
    st.caption("Barras: alcance medio por escenario; bigotes: IC 95 % de la media (media ± 1.96·EE).")
    st.dataframe(summ, hide_index=True)


# ---------------------------------------------------------------- pestaña 3
@st.cache_resource(show_spinner=False)
def get_graph(kind: str, n: int, seed: int) -> nx.Graph:
    """Caché de recursos: el grafo no se copia en cada rerun (no se modifica aquí)."""
    return networks.build_network(kind, n=n, mean_degree=MEAN_DEGREE, seed=seed)


def tab_network(n: int) -> None:
    c1, c2 = st.columns(2)
    n_draw = c1.slider("N del dibujo (red pequeña)", 30, 200, 100, step=10)
    log_y = c2.checkbox("Eje Y logarítmico (cola de los hubs en BA)")
    try:
        graphs = {k: (get_graph(k, n, SEED0), get_graph(k, n_draw, SEED0)) for k in TOPOLOGIES}
    except NotImplementedError:
        st.info("`networks.build_network` (P2, Marinés) aún no está en `main`: esta pestaña se activa "
                "tras el merge.")
        return

    for col, kind in zip(st.columns(3), TOPOLOGIES):
        G, small = graphs[kind]
        stats = networks.degree_stats(G)
        with col:
            st.subheader(TOPOLOGIES[kind])
            st.caption(f"N = {n} · ⟨k⟩ = {stats['k_mean']:.2f} · ⟨k²⟩ = {stats['k2_mean']:.1f} · "
                       f"k_max = {stats['k_max']:.0f}")
            hist = go.Figure(go.Histogram(x=[d for _, d in G.degree()], marker_color=COLORS["S"]))
            hist.update_layout(xaxis_title="Grado k", yaxis_title="Número de nodos",
                               yaxis_type="log" if log_y else "linear", margin=dict(t=10, b=10), height=300)
            st.plotly_chart(hist)

            fig, ax = plt.subplots(figsize=(4, 4))
            deg = dict(small.degree())
            nx.draw(small, pos=nx.spring_layout(small, seed=SEED0), ax=ax, width=0.3, edge_color="#bbbbbb",
                    node_size=[8 + 4 * deg[v] for v in small], node_color=COLORS["S"])
            ax.set_title(f"N = {n_draw} (tamaño ∝ grado)", fontsize=9)
            st.pyplot(fig)
            plt.close(fig)
    st.caption("No se muestran estados por nodo: SimResult solo guarda fracciones agregadas (contrato).")


# ---------------------------------------------------------------- app
st.set_page_config(page_title="Fake news · SEIR-D", layout="wide")
st.title("Propagación de fake news · SEIR-D en redes")
cfg = sidebar()
t1, t2, t3 = st.tabs(["Simulador", "Comparar escenarios", "Estructura de la red"])
with t1:
    tab_simulator(cfg)
with t2:
    tab_compare()
with t3:
    tab_network(cfg["n"])
