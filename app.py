import streamlit as st
import pandas as pd
import plotly.express as px
import math
import datetime

# --- Configuração da Página ---
st.set_page_config(page_title="Gestão Logística Full Turnos", layout="wide")
st.title("🚛 Central de Comando Logístico - Planejamento & Execução")

# ==============================================================================
# INICIALIZAÇÃO DE VARIÁVEIS NA MEMÓRIA (Garante que a Visão Geral funcione)
# ==============================================================================
default_times = {"Turno 1": datetime.time(6, 0), "Turno 2": datetime.time(14, 0), "Turno 3": datetime.time(22, 0)}
for t in ["Turno 1", "Turno 2", "Turno 3"]:
    if f"dur_{t}" not in st.session_state: st.session_state[f"dur_{t}"] = 8.8
    if f"pausa_{t}" not in st.session_state: st.session_state[f"pausa_{t}"] = 1.0
    if f"inicio_{t}" not in st.session_state: st.session_state[f"inicio_{t}"] = default_times[t]
    if f"abs_{t}" not in st.session_state: st.session_state[f"abs_{t}"] = 5
    if f"oee_{t}" not in st.session_state: st.session_state[f"oee_{t}"] = 85

# ==============================================================================
# BARRA LATERAL (Controle de Turnos)
# ==============================================================================
st.sidebar.header("🔄 Seleção de Visão")
turno_atual = st.sidebar.radio(
    "Escolha o Turno ou Visão:", 
    ["Turno 1", "Turno 2", "Turno 3", "Visão Geral (Todos os Turnos)"],
    help="Selecione um turno para imputar dados ou 'Visão Geral' para ver o quadro de todos."
)

st.sidebar.markdown("---")

# Configurações do Turno Específico
if turno_atual != "Visão Geral (Todos os Turnos)":
    st.sidebar.header(f"⚙️ Configurações - {turno_atual}")
    with st.sidebar.expander("⏰ Jornada e Eficiência", expanded=True):
        horas_turno = st.number_input("Duração (h)", value=st.session_state[f"dur_{turno_atual}"], step=0.1, key=f"dur_{turno_atual}")
        tempo_pausa = st.number_input("Pausa (h)", value=st.session_state[f"pausa_{turno_atual}"], step=0.1, key=f"pausa_{turno_atual}")
        inicio_turno = st.time_input("Início", value=st.session_state[f"inicio_{turno_atual}"], key=f"inicio_{turno_atual}")
        
        horas_liquidas = horas_turno - tempo_pausa
        st.sidebar.info(f"**Tempo Útil:** {horas_liquidas:.2f}h")

        absenteismo = st.sidebar.slider("Absenteísmo (%)", 0, 20, st.session_state[f"abs_{turno_atual}"], key=f"abs_{turno_atual}") / 100
        eficiencia_oee = st.sidebar.slider("Eficiência (%)", 50, 100, st.session_state[f"oee_{turno_atual}"], key=f"oee_{turno_atual}") / 100
        fator_produtivo = (1 - absenteismo) * eficiencia_oee
else:
    st.sidebar.info("💡 Você está no modo de leitura. Selecione um turno específico acima para editar os dados.")

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def formatar_horas(horas):
    try:
        if pd.isna(horas) or horas == float('inf') or horas < 0: return "--:--:--"
        seg = int(horas * 3600)
        return str(datetime.timedelta(seconds=seg))
    except: return "--:--:--"

def calcular_hora_termino(horas_duracao, inicio_t):
    try:
        if pd.isna(horas_duracao) or horas_duracao == float('inf'): return "--:--:--"
        hoje = datetime.datetime.now().date()
        dt_inicio = datetime.datetime.combine(hoje, inicio_t)
        dt_fim = dt_inicio + datetime.timedelta(hours=horas_duracao)
        return dt_fim.strftime("%H:%M")
    except: return "--:--:--"

def gerar_grade_horaria(inicio, duracao_horas):
    horarios = []
    hoje = datetime.datetime.now().date()
    dt_atual = datetime.datetime.combine(hoje, inicio)
    if dt_atual.minute > 0:
        dt_atual = dt_atual.replace(minute=0, second=0) + datetime.timedelta(hours=1)
    for _ in range(int(math.ceil(duracao_horas)) + 2): 
        horarios.append(dt_atual.strftime("%H:00"))
        dt_atual += datetime.timedelta(hours=1)
    return horarios

def renderizar_aba_padrao(titulo, dados_padrao, key_suffix, label_volume="Volume Total"):
    # Inicializa estado padrao para todos os turnos para não quebrar a Visão Geral
    for t in ["Turno 1", "Turno 2", "Turno 3"]:
        chave_t = f"{key_suffix}_{t}"
        if f"plan_data_{chave_t}" not in st.session_state: st.session_state[f"plan_data_{chave_t}"] = pd.DataFrame(dados_padrao)
        if f"vol_{chave_t}" not in st.session_state: st.session_state[f"vol_{chave_t}"] = 1000

    # ================= MODO: VISÃO GERAL (LEITURA DE TODOS OS TURNOS) =================
    if turno_atual == "Visão Geral (Todos os Turnos)":
        st.markdown(f"### 📋 Quadro Geral: {titulo}")
        
        for t in ["Turno 1", "Turno 2", "Turno 3"]:
            st.markdown(f"#### 🔹 {t}")
            chave = f"{key_suffix}_{t}"
            
            # Resgata variaveis especificas do turno
            vol_t = st.session_state[f"vol_{chave}"]
            fator_prod_t = (1 - (st.session_state[f"abs_{t}"] / 100)) * (st.session_state[f"oee_{t}"] / 100)
            df_plan_t = st.session_state[f"plan_data_{chave}"].copy()
            
            df_validos = df_plan_t.dropna(subset=["Atividade"]).copy()
            df_validos = df_validos[df_validos["Atividade"].astype(str).str.strip() != ""]
            
            if not df_validos.empty:
                def calc_linha_t(row):
                    part = row["Mix/Participação (%)"] if pd.notna(row["Mix/Participação (%)"]) else 0
                    meta = row["Meta (Unid/h/homem)"] if pd.notna(row["Meta (Unid/h/homem)"]) else 0
                    hc = row["HC Alocado"] if pd.notna(row["HC Alocado"]) else 0
                    vol_tarefa = vol_t * (part / 100)
                    cap_hora = meta * hc * fator_prod_t
                    duracao = vol_tarefa / cap_hora if cap_hora > 0 else float('inf')
                    return pd.Series([vol_tarefa, cap_hora, duracao])

                df_validos[["Volume Tarefa", "Capacidade Real/h", "Duração (h)"]] = df_validos.apply(calc_linha_t, axis=1)
                
                # Formatação Segura
                for col in ["Volume Tarefa", "HC Alocado", "Capacidade Real/h", "Duração (h)"]:
                    df_validos[col] = pd.to_numeric(df_validos[col], errors='coerce').fillna(0)
                
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.caption("Planejamento (Leitura)")
                    st.dataframe(df_validos[["Atividade", "Volume Tarefa", "HC Alocado", "Capacidade Real/h", "Duração (h)"]].style.format({
                        "Volume Tarefa": "{:.0f}", "HC Alocado": "{:.0f}", "Capacidade Real/h": "{:.1f}", "Duração (h)": "{:.2f}"
                    }), use_container_width=True)
                
                with c2:
                    st.caption("Acompanhamento Hora a Hora (Resumo)")
                    if f"hx_data_{chave}" in st.session_state:
                        df_hx_t = st.session_state[f"hx_data_{chave}"]
                        df_hx_t["Realizado"] = pd.to_numeric(df_hx_t["Realizado"], errors='coerce').fillna(0)
                        total_realizado = df_hx_t["Realizado"].sum()
                        progresso = min(total_realizado / vol_t, 1.0) if vol_t > 0 else 0
                        st.metric("Total Realizado", f"{total_realizado:,.0f} / {vol_t:,.0f}")
                        st.progress(progresso)
                    else:
                        st.info("Aguardando apontamentos...")
            st.divider()

    # ================= MODO: PREENCHIMENTO POR TURNO =================
    else:
        chave_unica = f"{key_suffix}_{turno_atual}"
        st.markdown(f"### 📋 1. Planejamento: {titulo} ({turno_atual})")
        
        col_vol, col_kpi_plan = st.columns([1, 2])
        with col_vol:
            vol_total = st.number_input(f"Meta ({label_volume})", value=st.session_state[f"vol_{chave_unica}"], step=100, key=f"vol_{chave_unica}")
        
        df_plan = st.data_editor(
            st.session_state[f"plan_data_{chave_unica}"],
            column_config={
                "Mix/Participação (%)": st.column_config.NumberColumn(format="%d%%", max_value=100),
                "Meta (Unid/h/homem)": st.column_config.NumberColumn(format="%d"),
                "HC Alocado": st.column_config.NumberColumn(format="%d", min_value=0),
            },
            num_rows="dynamic", key=f"editor_{chave_unica}", use_container_width=True
        )
        st.session_state[f"plan_data_{chave_unica}"] = df_plan

        df_validos = df_plan.dropna(subset=["Atividade"]).copy()
        df_validos = df_validos[df_validos["Atividade"].astype(str).str.strip() != ""]
        capacidade_hora_total = 0 

        if not df_validos.empty:
            def calcular_linha(row):
                part = row["Mix/Participação (%)"] if pd.notna(row["Mix/Participação (%)"]) else 0
                meta = row["Meta (Unid/h/homem)"] if pd.notna(row["Meta (Unid/h/homem)"]) else 0
                hc = row["HC Alocado"] if pd.notna(row["HC Alocado"]) else 0
                vol_tarefa = vol_total * (part / 100)
                cap_hora = meta * hc * fator_produtivo
                duracao = vol_tarefa / cap_hora if cap_hora > 0 else float('inf')
                return pd.Series([vol_tarefa, cap_hora, duracao])

            df_validos[["Volume Tarefa", "Capacidade Real/h", "Duração (h)"]] = df_validos.apply(calcular_linha, axis=1)
            capacidade_hora_total = df_validos["Capacidade Real/h"].sum()

            with st.expander(f"Detalhes do Planejamento ({turno_atual})", expanded=False):
                display_df = df_validos[["Atividade", "Volume Tarefa", "HC Alocado", "Capacidade Real/h", "Duração (h)"]].copy()
                for col in ["Volume Tarefa", "HC Alocado", "Capacidade Real/h", "Duração (h)"]:
                    display_df[col] = pd.to_numeric(display_df[col], errors='coerce').fillna(0)
                
                st.dataframe(
                    display_df.style.format({
                        "Volume Tarefa": "{:.0f}", "HC Alocado": "{:.0f}",
                        "Capacidade Real/h": "{:.1f}", "Duração (h)": "{:.2f}"
                    }),
                    use_container_width=True
                )
            
            tempo_max_plan = df_validos["Duração (h)"].max()
            if tempo_max_plan != float('inf') and tempo_max_plan > 0:
                termino_plan = calcular_hora_termino(tempo_max_plan, st.session_state[f"inicio_{turno_atual}"])
                with col_kpi_plan:
                    st.info(f"📆 **Previsão:** Terminar às **{termino_plan}** (se mantido o plano).")

        st.divider()
        st.markdown(f"### ⏱️ 2. Execução Hora a Hora ({turno_atual})")
        
        col_in, col_dash = st.columns([1, 2])
        with col_in:
            lista_horas = gerar_grade_horaria(st.session_state[f"inicio_{turno_atual}"], st.session_state[f"dur_{turno_atual}"])
            if f"hx_data_{chave_unica}" not in st.session_state:
                st.session_state[f"hx_data_{chave_unica}"] = pd.DataFrame({"Hora": lista_horas, "Realizado": [0]*len(lista_horas)})
            
            df_hx = st.data_editor(
                st.session_state[f"hx_data_{chave_unica}"],
                column_config={"Realizado": st.column_config.NumberColumn(format="%d")},
                hide_index=True, key=f"ed_hx_{chave_unica}", height=300
            )
            st.session_state[f"hx_data_{chave_unica}"] = df_hx

        with col_dash:
            df_hx["Realizado"] = pd.to_numeric(df_hx["Realizado"], errors='coerce').fillna(0)
            total_realizado = df_hx["Realizado"].sum()
            saldo_pendente = vol_total - total_realizado
            horas_com_apontamento = df_hx[df_hx["Realizado"] > 0].shape[0]
            
            ritmo_atual_medio = total_realizado / horas_com_apontamento if horas_com_apontamento > 0 else 0
            horas_restantes_estimadas = max(0, horas_liquidas - horas_com_apontamento)
            ritmo_necessario = saldo_pendente / horas_restantes_estimadas if horas_restantes_estimadas > 0 else saldo_pendente 

            progresso = min(total_realizado / vol_total, 1.0) if vol_total > 0 else 0
            st.write(f"**Progresso ({turno_atual}):** {progresso:.1%}")
            st.progress(progresso)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Realizado", f"{total_realizado:,.0f}", delta=f"{saldo_pendente:,.0f} pendente", delta_color="inverse")
            c2.metric("Ritmo Atual", f"{ritmo_atual_medio:.0f}/h")
            c3.metric("Ritmo Necessário", f"{ritmo_necessario:.0f}/h", delta=f"{ritmo_atual_medio - ritmo_necessario:.0f}")

            st.subheader("📢 Análise de Decisão")
            if saldo_pendente <= 0:
                st.success("✅ **Meta Batida!**")
            elif ritmo_atual_medio == 0:
                st.info("ℹ️ Insira apontamentos para análise.")
            else:
                horas_para_fim = saldo_pendente / ritmo_atual_medio
                if ritmo_atual_medio >= ritmo_necessario:
                    st.success(f"🚀 **Bom ritmo!** Término projetado em {formatar_horas(horas_para_fim)}.")
                else:
                    st.error("🚨 **Risco de Atraso!** Necessário aumentar o ritmo ou a equipe.")

# ==============================================================================
# ESTRUTURA DE ABAS
# ==============================================================================
abas = st.tabs(["📊 Visão Geral", "📦 Expedição Courier", "📥 Recebimento", "🏗️ Armazenagem", "🚚 Expedição Rodo", "📋 Inventário", "⚙️ Outros"])

# Inicializa Dados Base da Macro
for t in ["Turno 1", "Turno 2", "Turno 3"]:
    if f"geral_data_{t}" not in st.session_state:
        st.session_state[f"geral_data_{t}"] = pd.DataFrame({
            "Processo": ["Recebimento", "Armazenagem", "Separação", "Expedição"],
            "Demanda (Unid.)": [5000, 5000, 12000, 1500],
            "Produtividade Meta": [200, 150, 120, 300],
            "HC Atual": [4, 5, 10, 1]
        })

with abas[0]: 
    if turno_atual == "Visão Geral (Todos os Turnos)":
        st.subheader("📊 Quadro Completo - Todos os Turnos")
        
        for t in ["Turno 1", "Turno 2", "Turno 3"]:
            st.markdown(f"#### 🚛 {t}")
            
            df_t = st.session_state[f"geral_data_{t}"].copy()
            hr_liq_t = st.session_state[f"dur_{t}"] - st.session_state[f"pausa_{t}"]
            fat_prod_t = (1 - (st.session_state[f"abs_{t}"] / 100)) * (st.session_state[f"oee_{t}"] / 100)

            def calc_gap_t(row):
                prod = pd.to_numeric(row["Produtividade Meta"], errors='coerce') if pd.notna(row["Produtividade Meta"]) else 0
                demanda = pd.to_numeric(row["Demanda (Unid.)"], errors='coerce') if pd.notna(row["Demanda (Unid.)"]) else 0
                hc = pd.to_numeric(row["HC Atual"], errors='coerce') if pd.notna(row["HC Atual"]) else 0
                cap = prod * hr_liq_t * fat_prod_t
                nec = math.ceil(demanda / cap) if cap > 0 else 0
                gap = hc - nec
                return pd.Series([nec, gap, "🟢 Ideal" if gap >= 0 else "🔴 Falta"])

            df_t[["HC Nec.", "Gap", "Status"]] = df_t.apply(calc_gap_t, axis=1)
            
            c1, c2 = st.columns([2, 1])
            with c1:
                st.dataframe(
                    df_t[["Processo", "HC Atual", "HC Nec.", "Status"]].style.map(
                        lambda x: 'color: red; font-weight: bold' if x == "🔴 Falta" else 'color: green', subset=['Status']
                    ),
                    use_container_width=True
                )
            with c2:
                # ====== CORREÇÃO DO ERRO DO PLOTLY ======
                df_grafico = df_t.copy()
                df_grafico["HC Atual"] = pd.to_numeric(df_grafico["HC Atual"], errors="coerce").fillna(0).astype(float)
                df_grafico["HC Nec."] = pd.to_numeric(df_grafico["HC Nec."], errors="coerce").fillna(0).astype(float)
                
                fig = px.bar(
                    df_grafico, x="Processo", y=["HC Atual", "HC Nec."], barmode="group", 
                    title=f"HC Real vs Necessário",
                    color_discrete_map={"HC Atual": "#3498db", "HC Nec.": "#e74c3c"},
                    height=250
                )
                st.plotly_chart(fig, use_container_width=True)
            st.divider()

    else:
        st.subheader(f"Dimensionamento Macro - {turno_atual}")
        
        df_edit = st.data_editor(st.session_state[f"geral_data_{turno_atual}"], key=f"ed_macro_{turno_atual}", use_container_width=True)
        st.session_state[f"geral_data_{turno_atual}"] = df_edit

        def calc_gap(row):
            prod = pd.to_numeric(row["Produtividade Meta"], errors='coerce') if pd.notna(row["Produtividade Meta"]) else 0
            demanda = pd.to_numeric(row["Demanda (Unid.)"], errors='coerce') if pd.notna(row["Demanda (Unid.)"]) else 0
            hc = pd.to_numeric(row["HC Atual"], errors='coerce') if pd.notna(row["HC Atual"]) else 0

            cap = prod * horas_liquidas * fator_produtivo
            nec = math.ceil(demanda / cap) if cap > 0 else 0
            gap = hc - nec
            return pd.Series([nec, gap, "🟢 Ideal" if gap >= 0 else "🔴 Falta"])

        df_edit[["HC Nec.", "Gap", "Status"]] = df_edit.apply(calc_gap, axis=1)

        col1, col2 = st.columns([2, 1])
        with col1:
            # ====== CORREÇÃO DO ERRO DO PLOTLY ======
            df_grafico = df_edit.copy()
            df_grafico["HC Atual"] = pd.to_numeric(df_grafico["HC Atual"], errors="coerce").fillna(0).astype(float)
            df_grafico["HC Nec."] = pd.to_numeric(df_grafico["HC Nec."], errors="coerce").fillna(0).astype(float)

            fig = px.bar(
                df_grafico, 
                x="Processo", 
                y=["HC Atual", "HC Nec."], 
                barmode="group", 
                title=f"Equipe: Real vs Necessário ({turno_atual})",
                color_discrete_map={"HC Atual": "#3498db", "HC Nec.": "#e74c3c"}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            gap_total = pd.to_numeric(df_edit["Gap"], errors='coerce').fillna(0).sum()
            st.metric("Gap Total", f"{gap_total:.0f}")
            
            # ====== CORREÇÃO DO APPLYMAP ======
            st.dataframe(
                df_edit[["Processo", "HC Atual", "HC Nec.", "Status"]].style.map(
                    lambda x: 'color: red; font-weight: bold' if x == "🔴 Falta" else 'color: green', subset=['Status']
                ),
                use_container_width=True
            )

# Chamada das demais abas
with abas[1]: renderizar_aba_padrao("Expedição Courier", {"Atividade": ["Separação", "Embalagem"], "Mix/Participação (%)": [50, 50], "Meta (Unid/h/homem)": [100, 80], "HC Alocado": [5, 4]}, "courier")
with abas[2]: renderizar_aba_padrao("Recebimento", {"Atividade": ["Descarga", "Conferência"], "Mix/Participação (%)": [100, 100], "Meta (Unid/h/homem)": [300, 60], "HC Alocado": [3, 4]}, "rec")
with abas[3]: renderizar_aba_padrao("Armazenagem", {"Atividade": ["Putaway", "Ressuprimento"], "Mix/Participação (%)": [80, 20], "Meta (Unid/h/homem)": [30, 40], "HC Alocado": [4, 2]}, "arm")
with abas[4]: renderizar_aba_padrao("Expedição Rodo", {"Atividade": ["Carregamento", "Auditoria"], "Mix/Participação (%)": [100, 20], "Meta (Unid/h/homem)": [500, 50], "HC Alocado": [4, 1]}, "exp_rodo")
with abas[5]: renderizar_aba_padrao("Inventário", {"Atividade": ["Contagem", "Recontagem"], "Mix/Participação (%)": [90, 10], "Meta (Unid/h/homem)": [100, 50], "HC Alocado": [2, 1]}, "inv")
with abas[6]: renderizar_aba_padrao("Outros", {"Atividade": ["Limpeza", "Apoio"], "Mix/Participação (%)": [100, 50], "Meta (Unid/h/homem)": [10, 10], "HC Alocado": [2, 1]}, "outros")

# Rodapé
st.markdown("---") 
st.markdown("<div style='text-align: center; color: #666;'>🛠️ Desenvolvido por <b>Gabriel Fernandes</b> | 🚛 v3.1 (Visualização de Todos os Turnos)</div>", unsafe_allow_html=True)
