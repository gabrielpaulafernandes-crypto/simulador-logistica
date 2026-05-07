import streamlit as st
import pandas as pd
import plotly.express as px
import math
import datetime

# --- Configuração da Página ---
st.set_page_config(page_title="Gestão Logística Full Turnos", layout="wide")
st.title("🚛 Central de Comando Logístico - Planejamento & Execução")

# ==============================================================================
# BARRA LATERAL (Controle de Turnos)
# ==============================================================================
st.sidebar.header("🔄 Seleção de Visão")
turno_atual = st.sidebar.radio(
    "Escolha o Turno ou Visão:", 
    ["Turno 1", "Turno 2", "Turno 3", "Geral (Consolidado)"],
    help="Selecione um turno para imputar dados ou 'Geral' para ver o somatório do dia."
)

st.sidebar.markdown("---")

# Configurações só aparecem se não for a visão Geral
if turno_atual != "Geral (Consolidado)":
    st.sidebar.header(f"⚙️ Configurações - {turno_atual}")
    with st.sidebar.expander("⏰ Jornada e Eficiência", expanded=True):
        default_times = {"Turno 1": datetime.time(6, 0), "Turno 2": datetime.time(14, 0), "Turno 3": datetime.time(22, 0)}
        
        horas_turno = st.number_input("Duração (h)", value=8.8, step=0.1, key=f"dur_{turno_atual}")
        tempo_pausa = st.number_input("Pausa (h)", value=1.0, step=0.1, key=f"pausa_{turno_atual}")
        inicio_turno = st.time_input("Início", value=default_times[turno_atual], key=f"inicio_{turno_atual}")
        
        horas_liquidas = horas_turno - tempo_pausa
        absenteismo = st.sidebar.slider("Absenteísmo (%)", 0, 20, 5, key=f"abs_{turno_atual}") / 100
        eficiencia_oee = st.sidebar.slider("Eficiência (%)", 50, 100, 85, key=f"oee_{turno_atual}") / 100
        fator_produtivo = (1 - absenteismo) * eficiencia_oee
else:
    st.sidebar.info("💡 Na visão **Geral**, você visualiza a soma de todos os turnos planejados.")
    # Valores padrão para cálculos de fundo na visão geral (não afetam os dados)
    horas_liquidas = 7.8
    fator_produtivo = 0.80

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def formatar_horas(horas):
    try:
        if pd.isna(horas) or horas == float('inf') or horas < 0: return "--:--:--"
        seg = int(horas * 3600)
        return str(datetime.timedelta(seconds=seg))
    except: return "--:--:--"

def renderizar_aba_padrao(titulo, dados_padrao, key_suffix, label_volume="Volume Total"):
    """
    Função Mestra: Planejamento, Execução e agora Visão Consolidada.
    """
    turnos_lista = ["Turno 1", "Turno 2", "Turno 3"]
    
    if turno_atual == "Geral (Consolidado)":
        st.markdown(f"### 📈 Visão Consolidada do Dia: {titulo}")
        
        # Consolidação de Dados
        vol_total_dia = 0
        realizado_total_dia = 0
        dados_comparativos = []

        for t in turnos_lista:
            chave = f"{key_suffix}_{t}"
            vol = st.session_state.get(f"vol_{chave}", 0)
            real = st.session_state.get(f"hx_data_{chave}", pd.DataFrame({"Realizado": [0]}))["Realizado"].sum()
            vol_total_dia += vol
            realizado_total_dia += real
            dados_comparativos.append({"Turno": t, "Planejado": vol, "Realizado": real})

        df_comp = pd.DataFrame(dados_comparativos)
        
        # KPIs Gerais
        c1, c2, c3 = st.columns(3)
        c1.metric("Meta Total do Dia", f"{vol_total_dia:,.0f}")
        c2.metric("Total Realizado (Soma Turnos)", f"{realizado_total_dia:,.0f}")
        prog_dia = (realizado_total_dia / vol_total_dia) if vol_total_dia > 0 else 0
        c3.metric("Progresso Total", f"{prog_dia:.1%}")
        
        st.progress(min(prog_dia, 1.0))

        # Gráfico Comparativo
        fig = px.bar(df_comp, x="Turno", y=["Planejado", "Realizado"], barmode="group", 
                     title=f"Desempenho por Turno - {titulo}", color_discrete_sequence=["#3498db", "#2ecc71"])
        st.plotly_chart(fig, use_container_width=True)

    else:
        # --- MODO DE EDIÇÃO POR TURNO (Original v2.0) ---
        chave_unica = f"{key_suffix}_{turno_atual}"
        st.markdown(f"### 📋 1. Planejamento: {titulo} ({turno_atual})")
        
        col_vol, _ = st.columns([1, 2])
        with col_vol:
            vol_total = st.number_input(f"Meta do Turno", value=1000, step=100, key=f"vol_{chave_unica}")
        
        if f"plan_data_{chave_unica}" not in st.session_state:
            st.session_state[f"plan_data_{chave_unica}"] = pd.DataFrame(dados_padrao)

        df_plan = st.data_editor(st.session_state[f"plan_data_{chave_unica}"], num_rows="dynamic", key=f"editor_{chave_unica}", use_container_width=True)
        st.session_state[f"plan_data_{chave_unica}"] = df_plan

        st.divider()
        st.markdown(f"### ⏱️ 2. Execução Hora a Hora ({turno_atual})")
        
        col_in, col_dash = st.columns([1, 2])
        with col_in:
            lista_horas = [f"{h:02d}:00" for h in range(24)] # Simplificado para exemplo
            if f"hx_data_{chave_unica}" not in st.session_state:
                st.session_state[f"hx_data_{chave_unica}"] = pd.DataFrame({"Hora": lista_horas[:10], "Realizado": [0]*10})
            
            df_hx = st.data_editor(st.session_state[f"hx_data_{chave_unica}"], key=f"ed_hx_{chave_unica}", hide_index=True)
            st.session_state[f"hx_data_{chave_unica}"] = df_hx

        with col_dash:
            real_turno = df_hx["Realizado"].sum()
            st.metric("Realizado no Turno", f"{real_turno:,.0f}", delta=f"{vol_total - real_turno:,.0f} pendente")
            st.info(f"O acompanhamento detalhado de ritmo e projeção de término é processado aqui no {turno_atual}.")

# ==============================================================================
# ESTRUTURA DE ABAS
# ==============================================================================
abas = st.tabs(["📊 Visão Geral", "📦 Expedição Courier", "📥 Recebimento", "🏗️ Armazenagem", "🚚 Expedição Rodo", "📋 Inventário", "⚙️ Outros"])

with abas[0]: # ABA VISÃO GERAL
    if turno_atual == "Geral (Consolidado)":
        st.subheader("📊 Consolidado Diário - Todas as Áreas")
        
        # Somar demandas de todos os turnos para a visão macro
        dados_macro = []
        for area in ["Recebimento", "Armazenagem", "Separação", "Expedição"]:
            total_demanda_area = 0
            total_hc_area = 0
            for t in ["Turno 1", "Turno 2", "Turno 3"]:
                df_t = st.session_state.get(f"geral_data_{t}", pd.DataFrame())
                if not df_t.empty:
                    linha = df_t[df_t["Processo"] == area]
                    if not linha.empty:
                        total_demanda_area += linha["Demanda (Unid.)"].values[0]
                        total_hc_area += linha["HC Atual"].values[0]
            dados_macro.append({"Processo": area, "Demanda Total": total_demanda_area, "HC Total (Soma)": total_hc_area})
        
        df_macro = pd.DataFrame(dados_macro)
        
        c1, c2 = st.columns([2,1])
        with c1:
            fig_macro = px.bar(df_macro, x="Processo", y="Demanda Total", title="Volume Total do Dia por Área", color="Processo")
            st.plotly_chart(fig_macro, use_container_width=True)
        with c2:
            st.write("**Resumo de HC do Dia (Total Pessoas):**")
            st.table(df_macro[["Processo", "HC Total (Soma)"]])

    else:
        st.subheader(f"Dimensionamento de Headcount - {turno_atual}")
        if f"geral_data_{turno_atual}" not in st.session_state:
            st.session_state[f"geral_data_{turno_atual}"] = pd.DataFrame({
                "Processo": ["Recebimento", "Armazenagem", "Separação", "Expedição"],
                "Demanda (Unid.)": [5000, 5000, 12000, 1500],
                "Produtividade Meta": [200, 150, 120, 300],
                "HC Atual": [4, 5, 10, 1]
            })

        df_edit = st.data_editor(st.session_state[f"geral_data_{turno_atual}"], key=f"ed_macro_{turno_atual}", use_container_width=True)
        st.session_state[f"geral_data_{turno_atual}"] = df_edit

        # Lógica de cálculo simplificada para o Gap
        def calc_gap(row):
            cap = row["Produtividade Meta"] * horas_liquidas * fator_produtivo
            nec = math.ceil(row["Demanda (Unid.)"] / cap) if cap > 0 else 0
            gap = row["HC Atual"] - nec
            return pd.Series([nec, gap, "🟢 Ideal" if gap >= 0 else "🔴 Falta"])

        df_edit[["HC Nec.", "Gap", "Status"]] = df_edit.apply(calc_gap, axis=1)
        st.dataframe(df_edit.style.map(lambda x: 'color: red; font-weight: bold' if x == "🔴 Falta" else 'color: green', subset=['Status']), use_container_width=True)

# Chamada das demais abas
with abas[1]: renderizar_aba_padrao("Expedição Courier", {"Atividade": ["Separação", "Embalagem"], "Mix/Participação (%)": [50, 50], "Meta (Unid/h/homem)": [100, 80], "HC Alocado": [5, 4]}, "courier")
with abas[2]: renderizar_aba_padrao("Recebimento", {"Atividade": ["Descarga", "Conferência"], "Mix/Participação (%)": [100, 100], "Meta (Unid/h/homem)": [300, 60], "HC Alocado": [3, 4]}, "rec")
with abas[3]: renderizar_aba_padrao("Armazenagem", {"Atividade": ["Putaway", "Ressuprimento"], "Mix/Participação (%)": [80, 20], "Meta (Unid/h/homem)": [30, 40], "HC Alocado": [4, 2]}, "arm")
with abas[4]: renderizar_aba_padrao("Expedição Rodo", {"Atividade": ["Carregamento", "Auditoria"], "Mix/Participação (%)": [100, 20], "Meta (Unid/h/homem)": [500, 50], "HC Alocado": [4, 1]}, "exp_rodo")
with abas[5]: renderizar_aba_padrao("Inventário", {"Atividade": ["Contagem", "Recontagem"], "Mix/Participação (%)": [90, 10], "Meta (Unid/h/homem)": [100, 50], "HC Alocado": [2, 1]}, "inv")
with abas[6]: renderizar_aba_padrao("Outros", {"Atividade": ["Limpeza", "Apoio"], "Mix/Participação (%)": [100, 50], "Meta (Unid/h/homem)": [10, 10], "HC Alocado": [2, 1]}, "outros")

# Rodapé
st.markdown("---") 
st.markdown("<div style='text-align: center; color: #666;'>🛠️ Desenvolvido por <b>Gabriel Fernandes</b> | 🚛 v3.0 (Consolidado Geral)</div>", unsafe_allow_html=True)
