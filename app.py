import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(
    page_title="Dashboard Agentes MEI",
    page_icon="🛴",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.kpi-box {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    border-left: 4px solid #2563eb;
    margin-bottom: 0.5rem;
}
.kpi-value { font-size: 2rem; font-weight: 700; color: #1e3a5f; }
.kpi-label { font-size: 0.85rem; color: #6b7280; margin-top: -4px; }
.alert-red   { border-left-color: #dc2626; }
.alert-yellow{ border-left-color: #d97706; }
.alert-green { border-left-color: #16a34a; }
.insight-box {
    background: #fff7ed;
    border-left: 4px solid #f97316;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    margin: 0.4rem 0;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)


# ─── Data loading ─────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    base = Path(__file__).parent / "data"

    # ── Onboarding ────────────────────────────────────────────────────────────
    ob = pd.read_excel(base / "onboarding.xlsx", engine="openpyxl")
    ob.columns = [
        "timestamp", "email", "nome", "cidade",
        "preparado", "parte_confusa", "ganho_claro",
        "identifica_patinetes", "sabe_suporte",
        "comunic_resp", "atencao_resp", "pontualidade_resp",
    ] + [f"_extra_{i}" for i in range(len(ob.columns) - 12)]

    # ── Disponibilidade ───────────────────────────────────────────────────────
    disp_raw = pd.read_excel(base / "disponibilidade.xlsx", engine="openpyxl", header=None)
    disp_raw.columns = range(len(disp_raw.columns))
    disp = disp_raw.iloc[1:].reset_index(drop=True)
    disp.columns = [
        "timestamp", "horarios", "motivo_nao_turnos", "bom_ganho",
        "dificuldade_op", "o_que_faria_pegar_mais", "mensagem_sucesso",
        "nome", "fez_primeiro_turno", "cidade",
    ] + [f"_extra_{i}" for i in range(len(disp.columns) - 10)]

    # ── Normalizar cidades ────────────────────────────────────────────────────
    def norm(c):
        if pd.isna(c): return "N/A"
        c = str(c).strip().lower()
        if "paulo" in c:      return "São Paulo"
        if "horizonte" in c:  return "Belo Horizonte"
        if "recife" in c:     return "Recife"
        if "maceio" in c or "maceió" in c: return "Maceió"
        return c.title()

    ob["cidade_norm"] = ob["cidade"].apply(norm)
    disp["cidade_norm"] = disp["cidade"].apply(norm)

    # ── Converter respostas binárias/parciais para score 0-100 ───────────────
    def score(s):
        if pd.isna(s): return None
        s = str(s).strip().lower()
        if s.startswith("sim"):        return 100
        if "parcialmente" in s:        return 50
        if s.startswith("não") or s.startswith("nao"): return 0
        return None

    for col in ["preparado", "ganho_claro", "identifica_patinetes",
                "sabe_suporte", "comunic_resp", "atencao_resp", "pontualidade_resp"]:
        ob[f"{col}_score"] = ob[col].apply(score)

    # ── Bom ganho em disponibilidade ─────────────────────────────────────────
    def ganho_cat(s):
        if pd.isna(s): return None
        s = str(s).strip().lower()
        if s.startswith("sim"):  return "Sim"
        if s.startswith("não") or s.startswith("nao"): return "Não"
        return "Parcial"

    disp["ganho_cat"] = disp["bom_ganho"].apply(ganho_cat)

    return ob, disp


ob, disp = load_data()

CITIES = sorted(set(ob["cidade_norm"].unique()) | set(disp["cidade_norm"].unique()) - {"N/A"})
CITY_COLORS = {
    "São Paulo":       "#2563eb",
    "Belo Horizonte":  "#16a34a",
    "Recife":          "#d97706",
    "Maceió":          "#9333ea",
}


def kpi(value, label, color=""):
    return f"""<div class="kpi-box {color}">
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
    </div>"""


# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown("## 🛴 Dashboard — Agentes MEI | Funil de Ativação e Consistência")
st.caption("Concilia dados de Onboarding e Disponibilidade de Turnos para identificar gargalos operacionais por cidade.")

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Visão Geral",
    "🏙️ Por Cidade",
    "🔻 Funil de Ativação",
    "💡 Diagnóstico",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Visão Geral
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(kpi(len(ob), "Respostas Onboarding"), unsafe_allow_html=True)
    with col2:
        st.markdown(kpi(len(disp), "Respostas Disponibilidade"), unsafe_allow_html=True)
    with col3:
        st.markdown(kpi(len(CITIES), "Cidades ativas"), unsafe_allow_html=True)
    with col4:
        pct_sim = round((disp["ganho_cat"] == "Sim").sum() / disp["ganho_cat"].notna().sum() * 100)
        color = "alert-green" if pct_sim >= 60 else "alert-yellow" if pct_sim >= 40 else "alert-red"
        st.markdown(kpi(f"{pct_sim}%", "Satisfeitos com ganhos", color), unsafe_allow_html=True)

    st.divider()
    col_a, col_b = st.columns(2)

    # ── Preparação pós-treinamento ────────────────────────────────────────────
    with col_a:
        st.markdown("#### Preparação após o treinamento")
        prep_counts = ob["preparado"].value_counts().reset_index()
        prep_counts.columns = ["resposta", "count"]
        color_map = {"Sim": "#16a34a", "Parcialmente": "#d97706", "Não": "#dc2626"}
        fig = px.pie(
            prep_counts, names="resposta", values="count",
            color="resposta", color_discrete_map=color_map,
            hole=0.45,
        )
        fig.update_traces(textinfo="percent+label", pull=[0.05 if r == "Não" else 0 for r in prep_counts["resposta"]])
        fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=300)
        st.plotly_chart(fig, use_container_width=True)

    # ── Motivos para não pegar mais turnos ───────────────────────────────────
    with col_b:
        st.markdown("#### Motivos para não pegar mais turnos")
        motivo_counts = disp["motivo_nao_turnos"].value_counts().reset_index()
        motivo_counts.columns = ["motivo", "count"]
        fig2 = px.bar(
            motivo_counts.sort_values("count"),
            x="count", y="motivo", orientation="h",
            color="count",
            color_continuous_scale=["#bfdbfe", "#2563eb"],
            text="count",
        )
        fig2.update_traces(textposition="outside")
        fig2.update_layout(
            showlegend=False, coloraxis_showscale=False,
            xaxis_title="", yaxis_title="",
            margin=dict(t=10, b=10, l=10, r=30), height=300,
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    col_c, col_d = st.columns(2)

    # ── Satisfação com ganhos ─────────────────────────────────────────────────
    with col_c:
        st.markdown("#### Satisfação com ganhos por turno")
        ganho_counts = disp.groupby(["cidade_norm", "ganho_cat"]).size().reset_index(name="n")
        ganho_counts = ganho_counts[ganho_counts["cidade_norm"] != "N/A"]
        fig3 = px.bar(
            ganho_counts, x="cidade_norm", y="n", color="ganho_cat",
            color_discrete_map={"Sim": "#16a34a", "Não": "#dc2626", "Parcial": "#d97706"},
            barmode="stack", text="n",
        )
        fig3.update_traces(textposition="inside")
        fig3.update_layout(
            xaxis_title="", yaxis_title="Agentes", legend_title="Ganho satisfatório",
            margin=dict(t=10, b=10), height=300,
        )
        st.plotly_chart(fig3, use_container_width=True)

    # ── Conhecimento de suporte ────────────────────────────────────────────────
    with col_d:
        st.markdown("#### Sabe acionar suporte em campo?")
        sup_counts = ob["sabe_suporte"].value_counts().reset_index()
        sup_counts.columns = ["resposta", "count"]
        color_map2 = {"Sim": "#16a34a", "Parcialmente - Depende do problema": "#d97706", "Não": "#dc2626"}
        labels = {"Sim": "Sim", "Parcialmente - Depende do problema": "Parcialmente", "Não": "Não"}
        sup_counts["label"] = sup_counts["resposta"].map(labels).fillna(sup_counts["resposta"])
        fig4 = px.pie(
            sup_counts, names="label", values="count",
            color="resposta", color_discrete_map=color_map2,
            hole=0.45,
        )
        fig4.update_traces(textinfo="percent+label", pull=[0.05 if "Não" in r else 0 for r in sup_counts["resposta"]])
        fig4.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=300)
        st.plotly_chart(fig4, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Por Cidade
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    SCORE_COLS = {
        "preparado_score":          "Preparado pós-treino",
        "ganho_claro_score":        "Entendeu o modelo de ganho",
        "identifica_patinetes_score": "Identifica patinetes a priorizar",
        "sabe_suporte_score":       "Sabe acionar suporte",
        "comunic_resp_score":       "Comunicação do responsável",
        "atencao_resp_score":       "Atenção do responsável",
        "pontualidade_resp_score":  "Pontualidade do responsável",
    }

    city_scores = (
        ob[ob["cidade_norm"] != "N/A"]
        .groupby("cidade_norm")[list(SCORE_COLS.keys())]
        .mean()
        .round(1)
        .rename(columns=SCORE_COLS)
    )

    st.markdown("#### Heatmap de qualidade do Onboarding por Cidade (score 0–100)")
    st.caption("Verde = alto (≥80), Amarelo = médio (50–79), Vermelho = baixo (<50)")

    fig_heat = go.Figure(data=go.Heatmap(
        z=city_scores.values,
        x=city_scores.columns.tolist(),
        y=city_scores.index.tolist(),
        colorscale=[
            [0.0, "#dc2626"],
            [0.5, "#fbbf24"],
            [1.0, "#16a34a"],
        ],
        zmin=0, zmax=100,
        text=city_scores.values,
        texttemplate="%{text}",
        textfont={"size": 14},
        hoverongaps=False,
    ))
    fig_heat.update_layout(
        height=320,
        margin=dict(t=10, b=60, l=10, r=10),
        xaxis=dict(tickangle=-30),
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    st.divider()

    selected_city = st.selectbox("Detalhar cidade:", CITIES)

    col_x, col_y = st.columns(2)

    with col_x:
        st.markdown(f"##### Motivos para não pegar turnos — {selected_city}")
        city_disp = disp[disp["cidade_norm"] == selected_city]
        if city_disp.empty:
            st.info("Sem dados de disponibilidade para esta cidade.")
        else:
            m = city_disp["motivo_nao_turnos"].value_counts().reset_index()
            m.columns = ["motivo", "count"]
            fig_m = px.bar(
                m.sort_values("count"),
                x="count", y="motivo", orientation="h",
                color="count", color_continuous_scale=["#bfdbfe", "#1d4ed8"],
                text="count",
            )
            fig_m.update_traces(textposition="outside")
            fig_m.update_layout(
                showlegend=False, coloraxis_showscale=False,
                xaxis_title="", yaxis_title="",
                margin=dict(t=5, b=5, l=5, r=30), height=280,
            )
            st.plotly_chart(fig_m, use_container_width=True)

    with col_y:
        st.markdown(f"##### Radar de Onboarding — {selected_city}")
        city_ob = ob[ob["cidade_norm"] == selected_city]
        if city_ob.empty:
            st.info("Sem dados de onboarding para esta cidade.")
        else:
            radar_vals = city_ob[list(SCORE_COLS.keys())].mean().round(1)
            categories = list(SCORE_COLS.values())
            vals = radar_vals.tolist()
            fig_r = go.Figure(go.Scatterpolar(
                r=vals + [vals[0]],
                theta=categories + [categories[0]],
                fill="toself",
                fillcolor=CITY_COLORS.get(selected_city, "#2563eb") + "33",
                line_color=CITY_COLORS.get(selected_city, "#2563eb"),
                name=selected_city,
            ))
            fig_r.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=False,
                margin=dict(t=20, b=20, l=20, r=20),
                height=280,
            )
            st.plotly_chart(fig_r, use_container_width=True)

    # ── Dificuldades abertas ────────────────────────────────────────────────────
    diffs = disp[(disp["cidade_norm"] == selected_city) & (disp["dificuldade_op"].notna())]
    diffs_filtered = diffs[~diffs["dificuldade_op"].astype(str).str.strip().str.lower().isin(["não", "nao", "nao.", "não.", "n/a"])]
    if not diffs_filtered.empty:
        with st.expander(f"Dificuldades operacionais reportadas ({len(diffs_filtered)} respostas)"):
            for _, row in diffs_filtered.iterrows():
                st.markdown(f"- {row['dificuldade_op']}")

    # ── Partes confusas do treino ────────────────────────────────────────────────
    confusas = ob[(ob["cidade_norm"] == selected_city) & (ob["parte_confusa"].notna())]
    confusas_filtered = confusas[~confusas["parte_confusa"].astype(str).str.strip().str.lower().isin(["não", "nao", "nao.", "não.", "não ", "nao "])]
    if not confusas_filtered.empty:
        with st.expander(f"Lacunas reportadas no treinamento ({len(confusas_filtered)} respostas)"):
            for _, row in confusas_filtered.iterrows():
                st.markdown(f"- {row['parte_confusa']}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Funil de Ativação
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("#### Funil: Do Treinamento à Consistência Operacional")
    st.caption("Quanto se perde em cada etapa até o agente operar de forma consistente.")

    # ── Funil global ─────────────────────────────────────────────────────────
    total_treinados = len(ob)
    preparados = (ob["preparado"] == "Sim").sum()
    ganho_entendido = (ob["ganho_claro"] == "Sim").sum()
    suporte_ok = (ob["sabe_suporte"] == "Sim").sum()

    # Fez primeiro turno (dados de Disponibilidade, BH + Recife)
    fez_turno_data = disp[disp["fez_primeiro_turno"].notna()]
    fez_turno_sim = (fez_turno_data["fez_primeiro_turno"] == "Sim").sum()
    fez_turno_total = len(fez_turno_data)

    # Bom ganho (proxy de consistência)
    ganho_ok_disp = (disp["ganho_cat"] == "Sim").sum()
    ganho_total_disp = disp["ganho_cat"].notna().sum()

    funnel_labels = [
        "1. Realizaram treinamento",
        "2. Se sentiram preparados",
        "3. Entenderam modelo de ganho",
        "4. Sabem acionar suporte",
    ]
    funnel_values = [total_treinados, preparados, ganho_entendido, suporte_ok]

    fig_funnel = go.Figure(go.Funnel(
        y=funnel_labels,
        x=funnel_values,
        textposition="inside",
        textinfo="value+percent initial",
        marker=dict(color=["#1d4ed8", "#2563eb", "#3b82f6", "#60a5fa"]),
        connector=dict(line=dict(color="#e5e7eb", width=1)),
    ))
    fig_funnel.update_layout(
        margin=dict(t=20, b=20, l=10, r=10),
        height=360,
    )
    st.plotly_chart(fig_funnel, use_container_width=True)

    # ── Funil por cidade ─────────────────────────────────────────────────────
    st.divider()
    st.markdown("#### Funil de Onboarding por Cidade")

    funnel_city = []
    for city in CITIES:
        city_ob_c = ob[ob["cidade_norm"] == city]
        if city_ob_c.empty:
            continue
        n = len(city_ob_c)
        funnel_city.append({
            "Cidade": city,
            "Treinados": n,
            "Preparados (Sim)": (city_ob_c["preparado"] == "Sim").sum(),
            "Entendeu ganho (Sim)": (city_ob_c["ganho_claro"] == "Sim").sum(),
            "Sabe suporte (Sim)": (city_ob_c["sabe_suporte"] == "Sim").sum(),
        })

    df_funnel = pd.DataFrame(funnel_city).set_index("Cidade")

    # Convert to % of treinados
    df_pct = df_funnel.copy()
    for col in ["Preparados (Sim)", "Entendeu ganho (Sim)", "Sabe suporte (Sim)"]:
        df_pct[col] = (df_funnel[col] / df_funnel["Treinados"] * 100).round(1)

    df_melt = df_pct.drop(columns="Treinados").reset_index().melt(id_vars="Cidade", var_name="Etapa", value_name="% de Treinados")

    fig_city_funnel = px.bar(
        df_melt, x="Cidade", y="% de Treinados", color="Etapa",
        barmode="group", text="% de Treinados",
        color_discrete_sequence=["#1d4ed8", "#f59e0b", "#dc2626"],
    )
    fig_city_funnel.update_traces(texttemplate="%{text}%", textposition="outside")
    fig_city_funnel.update_layout(
        yaxis=dict(range=[0, 115]),
        margin=dict(t=10, b=10),
        height=360,
        legend_title="",
    )
    st.plotly_chart(fig_city_funnel, use_container_width=True)

    # ── Primeiro turno (somente cidades com dado) ─────────────────────────────
    if fez_turno_total > 0:
        st.divider()
        st.markdown("#### Conversão: Treinamento → Primeiro Turno (BH e Recife)")
        city_turno = (
            disp[disp["fez_primeiro_turno"].notna()]
            .groupby(["cidade_norm", "fez_primeiro_turno"])
            .size()
            .reset_index(name="n")
        )
        fig_turno = px.bar(
            city_turno, x="cidade_norm", y="n", color="fez_primeiro_turno",
            color_discrete_map={"Sim": "#16a34a", "Não": "#dc2626"},
            barmode="stack", text="n",
            labels={"cidade_norm": "", "n": "Agentes", "fez_primeiro_turno": "Fez 1º turno?"},
        )
        fig_turno.update_traces(textposition="inside")
        fig_turno.update_layout(margin=dict(t=10, b=10), height=280)
        st.plotly_chart(fig_turno, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Diagnóstico
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("#### Diagnóstico por Gargalo")
    st.caption("Consolidação dos principais problemas identificados nos dados, por categoria.")

    # ── Resumo numérico ────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)

    pct_prep = round((ob["preparado"] == "Sim").sum() / len(ob) * 100)
    pct_ganho_claro = round((ob["ganho_claro"] == "Sim").sum() / len(ob) * 100)
    pct_suporte = round((ob["sabe_suporte"] == "Sim").sum() / len(ob) * 100)
    pct_ganho_ok = round((disp["ganho_cat"] == "Sim").sum() / disp["ganho_cat"].notna().sum() * 100)
    pct_pontual = round((ob["pontualidade_resp"] == "Sim").sum() / ob["pontualidade_resp"].notna().sum() * 100)

    with col1:
        c = "alert-green" if pct_prep >= 80 else "alert-yellow" if pct_prep >= 60 else "alert-red"
        st.markdown(kpi(f"{pct_prep}%", "Preparados após treinamento", c), unsafe_allow_html=True)
        c = "alert-green" if pct_ganho_claro >= 80 else "alert-yellow" if pct_ganho_claro >= 60 else "alert-red"
        st.markdown(kpi(f"{pct_ganho_claro}%", "Entenderam modelo de ganho", c), unsafe_allow_html=True)
    with col2:
        c = "alert-green" if pct_suporte >= 80 else "alert-yellow" if pct_suporte >= 60 else "alert-red"
        st.markdown(kpi(f"{pct_suporte}%", "Sabem acionar suporte", c), unsafe_allow_html=True)
        c = "alert-green" if pct_ganho_ok >= 60 else "alert-yellow" if pct_ganho_ok >= 40 else "alert-red"
        st.markdown(kpi(f"{pct_ganho_ok}%", "Satisfeitos com ganhos por turno", c), unsafe_allow_html=True)
    with col3:
        c = "alert-green" if pct_pontual >= 80 else "alert-yellow" if pct_pontual >= 60 else "alert-red"
        st.markdown(kpi(f"{pct_pontual}%", "Resp. técnico pontual", c), unsafe_allow_html=True)

        # SP-specific: % sem clareza em ganho
        sp_ob = ob[ob["cidade_norm"] == "São Paulo"]
        pct_sp_parcial = round((sp_ob["preparado"].isin(["Parcialmente", "Não"])).sum() / len(sp_ob) * 100) if len(sp_ob) > 0 else 0
        c = "alert-red" if pct_sp_parcial >= 40 else "alert-yellow"
        st.markdown(kpi(f"{pct_sp_parcial}%", "SP: Parcialmente/Não preparados", c), unsafe_allow_html=True)

    st.divider()

    # ── Gargalos identificados ─────────────────────────────────────────────────
    gargalos = [
        {
            "icon": "🔴",
            "titulo": "Gargalo 1 — App e procedimentos não consolidados no treinamento",
            "texto": (
                "Em São Paulo, 11 agentes reportaram lacunas no treino — principalmente sobre o uso do aplicativo ST, "
                "procedimentos para patinetes 100% descarregados e troca de baterias sem patinete de serviço disponível. "
                "O treinamento foi feito no celular do treinador, não no do agente. "
                "Isso cria um falso positivo de prontidão: o agente diz 'Sim' mas não sabe operar sozinho no campo."
            ),
        },
        {
            "icon": "🔴",
            "titulo": "Gargalo 2 — Baixo ganho percebido desmotiva a manutenção de turnos",
            "texto": (
                "57% dos agentes em SP e BH não sente que está tendo bom ganho por turno. "
                "O principal driver é a distância entre patinetes e armários de bateria, que consome tempo e locomoção não remunerada. "
                "Agentes de SP citam que o valor mínimo de R$3,50/troca é inviável dada a dispersão geográfica. "
                "Sem percepção de ganho sustentável, não há incentivo para regularidade."
            ),
        },
        {
            "icon": "🟡",
            "titulo": "Gargalo 3 — Falta de slots e visibilidade de turnos (BH)",
            "texto": (
                "Em Belo Horizonte, 35% dos agentes aponta 'Falta de slots' como motivo principal para não pegar mais turnos — "
                "o maior percentual entre todas as cidades. Isso sugere que há demanda de trabalho mas a oferta de turnos não está acompanhando, "
                "ou que o sistema de reserva de turnos não está visível/acessível para os agentes."
            ),
        },
        {
            "icon": "🟡",
            "titulo": "Gargalo 4 — Suporte em campo insuficiente ou desconhecido",
            "texto": (
                "39% dos agentes diz 'Parcialmente' saber acionar suporte — variando conforme o tipo de problema. "
                "Em SP, 7 de 16 agentes estão nessa categoria. Isso significa que problemas em campo (app travado, "
                "bateria sem LED, patinete sem sinal) ficam sem resolução, gerando abandono de turno."
            ),
        },
        {
            "icon": "🟡",
            "titulo": "Gargalo 5 — Pagamentos e validação de conta bloqueando início (SP)",
            "texto": (
                "Agentes de SP citam pagamentos como 3º motivo para não pegar mais turnos, e um agente relatou que "
                "sua conta no Todoer não foi validada desde 3 de abril — impedindo completamente o início das operações. "
                "Problemas de onboarding administrativo (conta, acesso ao app) criam uma barreira invisível pré-operação."
            ),
        },
        {
            "icon": "🟢",
            "titulo": "Ponto positivo — Maceió com melhor onboarding",
            "texto": (
                "Maceió se destaca positivamente: 12/12 agentes se sentiram preparados, "
                "11/12 entenderam o modelo de ganho, comunicação do responsável com 100% de aprovação. "
                "O responsável técnico de Maceió pode servir de referência de boas práticas para as demais cidades."
            ),
        },
    ]

    for g in gargalos:
        st.markdown(
            f"""<div class="insight-box">
            <strong>{g['icon']} {g['titulo']}</strong><br>
            {g['texto']}
            </div>""",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Recomendações ─────────────────────────────────────────────────────────
    st.markdown("#### Recomendações prioritárias")
    recs = [
        ("🎯 Ação imediata", "Incluir sessão prática no celular do próprio agente para o app ST. Criar checklist impresso de campo para os 3 cenários críticos: patinete descarregado, bateria sem LED, patinete sem sinal."),
        ("💰 Modelo de ganho", "Revisar a dispersão geográfica de patinetes em SP. Considerar bônus por turno completo ou garantia mínima por deslocamento, especialmente para agentes de transporte público."),
        ("📅 Slots (BH)", "Auditar a disponibilidade de turnos em BH — verificar se há limitação técnica no sistema ou se é questão de comunicação de quando os slots são abertos."),
        ("🛠️ Suporte", "Criar fluxo de escalonamento simplificado e compartilhado em grupo (WhatsApp/Telegram) com casos comuns resolvidos. Responsável técnico deve estar disponível nas primeiras 2 semanas pós-treinamento."),
        ("📋 Ativação administrativa", "Criar SLA de até 48h para validação de conta no Todoer. Criar checklist de 'pronto para operar' (conta validada, app instalado, zona definida) antes de considerar o treinamento concluído."),
        ("🏆 Benchmarking", "Convidar o responsável técnico de Maceió para documentar seu protocolo de treinamento e replicar nas demais cidades."),
    ]

    for title, text in recs:
        st.markdown(f"**{title}:** {text}")
