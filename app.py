import streamlit as st
import pandas as pd
import plotly.express as px
import math
import datetime

# --- Configuração da Página ---
st.set_page_config(page_title="Gestão Logística em Tempo Real", layout="wide")
st.title("🚛 Central de Comando Logístico - Planejamento & Execução CD300")

# ==============================================================================
# BARRA LATERAL (Inputs)
# ==============================================================================
st.sidebar.header("⚙️ Configurações Globais")

with st.sidebar.expander("⏰ Jornada e Turno", expanded=True):
    horas_turno = st.number_input("Duração do Turno (h)", value=8.8, step=0.1)
    tempo_pausa = st.number_input("Tempo de Pausa (h)", value=1.0, step=0.1)
    inicio_turno = st.time_input("Início do Turno", value=datetime.time(6, 0))
    
    horas_liquidas = horas_turno - tempo_pausa
    st.sidebar.info(f"**Tempo Útil:** {horas_liquidas:.2f}h")

st.sidebar.markdown("---")
st.sidebar.subheader("Eficiência Padrão")
absenteismo = st.sidebar.slider("Absenteísmo Médio (%)", 0, 20, 5) / 100
eficiencia_oee = st.sidebar.slider("Eficiência (OEE) (%)", 50, 100, 85) / 100
fator_produtivo = (1 - absenteismo) * eficiencia_oee

st.sidebar.caption(f"Fator de Produtividade Global: {fator_produtivo:.0%}")

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def formatar_horas(horas):
    try:
        if pd.isna(horas) or horas == float('inf') or horas < 0: return "--:--:--"
        seg = int(horas * 3600)
        return str(datetime.timedelta(seconds=seg))
    except:
        return "--:--:--"

def calcular_hora_termino(horas_duracao):
    try:
        if pd.isna(horas_duracao) or horas_duracao == float('inf'): return "--:--:--"
        hoje = datetime.datetime.now().date()
        dt_inicio = datetime.datetime.combine(hoje, inicio_turno)
        dt_fim = dt_inicio + datetime.timedelta(hours=horas_duracao)
        return dt_fim.strftime("%H:%M")
    except:
        return "--:--:--"

def gerar_grade_horaria(inicio, duracao_horas):
    """Gera uma lista de horários. Corrigido erro de formatação do Windows."""
    horarios = []
    hoje = datetime.datetime.now().date()
    dt_atual = datetime.datetime.combine(hoje, inicio)
    
    if dt_atual.minute > 0:
        dt_atual = dt_atual.replace(minute=0, second=0) + datetime.timedelta(hours=1)
        
    for _ in range(int(math.ceil(duracao_horas)) + 2): 
        # CORREÇÃO: Usamos formatação simples para evitar erro %0
        horarios.append(dt_atual.strftime("%H:00"))
        dt_atual += datetime.timedelta(hours=1)
    return horarios

def renderizar_aba_padrao(titulo, dados_padrao, key_suffix, label_volume="Volume Total"):
    """
    Função Mestra: Gera Planejamento + Execução Hora a Hora
    """
    # --- BLOCO 1: PLANEJAMENTO ---
    st.markdown(f"### 📋 1. Planejamento: {titulo}")
    
    col_vol, col_kpi_plan = st.columns([1, 2])
    with col_vol:
        vol_total = st.number_input(
            f"Meta do Dia ({label_volume})", 
            value=1000, step=100, key=f"vol_{key_suffix}"
        )
    
    df_base = pd.DataFrame(dados_padrao)

    # Tabela Editável de Planejamento
    df_plan = st.data_editor(
        df_base,
        column_config={
            "Mix/Participação (%)": st.column_config.NumberColumn(format="%d%%", max_value=100),
            "Meta (Unid/h/homem)": st.column_config.NumberColumn(format="%d"),
            "HC Alocado": st.column_config.NumberColumn(format="%d", min_value=0),
        },
        num_rows="dynamic",
        key=f"editor_{key_suffix}",
        use_container_width=True
    )

    # Tratamento de linhas vazias (Segurança)
    # Removemos linhas onde a atividade não foi preenchida para não poluir o visual
    df_validos = df_plan.dropna(subset=["Atividade"]).copy()
    # Removemos strings vazias também
    df_validos = df_validos[df_validos["Atividade"].astype(str).str.strip() != ""]
    
    capacidade_hora_total = 0 
    
    if not df_validos.empty:
        # Lógica de cálculo linha a linha
        def calcular_linha(row):
            # Usamos 'get' ou verificação de NaN para garantir que nunca seja None
            part = row["Mix/Participação (%)"] if pd.notna(row["Mix/Participação (%)"]) else 0
            meta = row["Meta (Unid/h/homem)"] if pd.notna(row["Meta (Unid/h/homem)"]) else 0
            hc = row["HC Alocado"] if pd.notna(row["HC Alocado"]) else 0
            
            vol_tarefa = vol_total * (part / 100)
            cap_hora = meta * hc * fator_produtivo
            duracao = vol_tarefa / cap_hora if cap_hora > 0 else float('inf')
            
            return pd.Series([vol_tarefa, cap_hora, duracao])

        df_validos[["Volume Tarefa", "Capacidade Real/h", "Duração (h)"]] = df_validos.apply(calcular_linha, axis=1)
        
        capacidade_hora_total = df_validos["Capacidade Real/h"].sum()

        # --- EXIBIÇÃO SEGURA DA TABELA ---
        with st.expander("Ver Detalhes do Planejamento (Por Atividade)", expanded=False):
            # Prepara o dataframe para exibição
            display_df = df_validos[["Atividade", "Volume Tarefa", "HC Alocado", "Capacidade Real/h", "Duração (h)"]].copy()
            
            # CORREÇÃO CRÍTICA: Preenche vazios com 0 antes de formatar para evitar erro TypeError
            display_df = display_df.fillna(0)
            
            st.dataframe(
                display_df.style.format({
                    "Volume Tarefa": "{:.0f}",
                    "HC Alocado": "{:.0f}",
                    "Capacidade Real/h": "{:.1f}",
                    "Duração (h)": "{:.2f}"
                }),
                use_container_width=True
            )
        
        # KPI Principal do Planejamento
        tempo_max_plan = df_validos["Duração (h)"].max()
        if tempo_max_plan != float('inf') and tempo_max_plan > 0:
            termino_plan = calcular_hora_termino(tempo_max_plan)
            with col_kpi_plan:
                st.info(f"📆 **Previsão (Planejado):** Terminar às **{termino_plan}** com a equipe atual.")
        else:
            with col_kpi_plan:
                st.warning("⚠️ Defina HC e Metas para calcular previsão.")

    st.divider()

    # --- BLOCO 2: EXECUÇÃO HORA A HORA ---
    st.markdown(f"### ⏱️ 2. Execução: Acompanhamento Hora a Hora")
    
    col_input, col_dashboard = st.columns([1, 2])

    with col_input:
        st.caption("Insira a produção realizada a cada hora:")
        
        # Gera a lista de horas corrigida
        lista_horas = gerar_grade_horaria(inicio_turno, horas_turno)
        
        if f"hx_data_{key_suffix}" not in st.session_state:
            st.session_state[f"hx_data_{key_suffix}"] = pd.DataFrame({
                "Hora": lista_horas,
                "Realizado": [0] * len(lista_horas),
                "Observação": [""] * len(lista_horas)
            })

        df_hx = st.data_editor(
            st.session_state[f"hx_data_{key_suffix}"],
            column_config={"Realizado": st.column_config.NumberColumn(format="%d")},
            hide_index=True,
            key=f"editor_hx_{key_suffix}",
            height=300
        )

    # --- CÁLCULOS DO GESTOR (DECISÃO) ---
    with col_dashboard:
        # Garante que seja numérico e substitui None por 0
        df_hx["Realizado"] = pd.to_numeric(df_hx["Realizado"], errors='coerce').fillna(0)
        
        total_realizado = df_hx["Realizado"].sum()
        saldo_pendente = vol_total - total_realizado
        
        horas_com_apontamento = df_hx[df_hx["Realizado"] > 0].shape[0]
        
        if horas_com_apontamento > 0:
            ritmo_atual_medio = total_realizado / horas_com_apontamento
        else:
            ritmo_atual_medio = 0
            
        horas_totais_turno = horas_liquidas
        horas_restantes_estimadas = max(0, horas_totais_turno - horas_com_apontamento)
        
        if horas_restantes_estimadas > 0:
            ritmo_necessario = saldo_pendente / horas_restantes_estimadas
        else:
            ritmo_necessario = saldo_pendente 

        # --- EXIBIÇÃO DO COCKPIT ---
        progresso = min(total_realizado / vol_total, 1.0) if vol_total > 0 else 0
        st.write(f"**Progresso Global:** {progresso:.1%}")
        st.progress(progresso)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Realizado", f"{total_realizado:,.0f}", delta=f"{saldo_pendente:,.0f} Pendente", delta_color="inverse")
        c2.metric("Ritmo Atual (Média)", f"{ritmo_atual_medio:.0f}/h")
        
        delta_ritmo = ritmo_atual_medio - ritmo_necessario
        c3.metric("Ritmo Necessário (Meta)", f"{ritmo_necessario:.0f}/h", delta=f"{delta_ritmo:.0f}")

        st.divider()

        st.subheader("📢 Análise para Tomada de Decisão")
        
        if saldo_pendente <= 0:
            st.success("✅ **Meta Batida!** Operação finalizada com sucesso.")
        elif ritmo_atual_medio == 0:
            st.info("ℹ️ Insira apontamentos na tabela ao lado para gerar análise.")
        else:
            if ritmo_atual_medio > 0:
                horas_para_fim_real = saldo_pendente / ritmo_atual_medio
                
                # Projeção de horário
                hoje = datetime.datetime.now()
                hora_projetada = (hoje + datetime.timedelta(hours=horas_para_fim_real)).strftime("%H:%M")
                
                if ritmo_atual_medio >= ritmo_necessario:
                    st.success(f"🚀 **Vem tranquilo!** Nesse ritmo, terminamos em {formatar_horas(horas_para_fim_real)}.")
                else:
                    total_hc_plan = df_validos["HC Alocado"].sum() if not df_validos.empty else 0
                    prod_per_capita = capacidade_hora_total / total_hc_plan if total_hc_plan > 0 else 0
                    
                    deficit_produtividade = ritmo_necessario - ritmo_atual_medio
                    if prod_per_capita > 0:
                        pessoas_extras = math.ceil(deficit_produtividade / prod_per_capita)
                        st.error(f"🚨 **RISCO DE ATRASO!** Projetado terminar só às {hora_projetada}.")
                        st.markdown(f"""
                        **Sugestões de Ação:**
                        1. Aumentar ritmo em **{abs(delta_ritmo):.0f} peças/h**.
                        2. Ou alocar **+{pessoas_extras} pessoas** imediatamente.
                        """)
                    else:
                        st.warning("Preencha o HC no planejamento para receber sugestão de contratação.")

# ==============================================================================
# ESTRUTURA DE ABAS
# ==============================================================================
abas = st.tabs([
    "📊 Visão Geral", 
    "📦 Expedição Courier", 
    "📥 Recebimento", 
    "🏗️ Armazenagem", 
    "🚚 Expedição Rodo", 
    "📋 Inventário", 
    "⚙️ Outros"
])

# ==============================================================================
# ABA 1: VISÃO GERAL
# ==============================================================================
with abas[0]:
    st.subheader("Dimensionamento de Headcount (Macro)")
    st.caption("Visão consolidada de todas as áreas (Insira os totais aqui).")

    dados_iniciais = {
        "Processo": ["Recebimento", "Armazenagem", "Separação", "Expedição"],
        "Demanda (Unid.)": [5000, 5000, 12000, 1500],
        "Produtividade Meta": [200, 150, 120, 300],
        "HC Atual": [4, 5, 10, 1]
    }
    df = pd.DataFrame(dados_iniciais)

    df_editavel = st.data_editor(
        df,
        column_config={
            "Demanda (Unid.)": st.column_config.NumberColumn(format="%d"),
            "HC Atual": st.column_config.NumberColumn(format="%d"),
        },
        num_rows="dynamic",
        key="editor_geral_original",
        use_container_width=True
    )

    def calcular_cenario(row):
        # Proteção contra nulos
        prod = row["Produtividade Meta"] if pd.notna(row["Produtividade Meta"]) else 0
        demanda = row["Demanda (Unid.)"] if pd.notna(row["Demanda (Unid.)"]) else 0
        hc = row["HC Atual"] if pd.notna(row["HC Atual"]) else 0

        cap_dia_pessoa = prod * horas_liquidas * fator_produtivo
        
        if cap_dia_pessoa > 0:
            hc_nec = math.ceil(demanda / cap_dia_pessoa)
        else:
            hc_nec = 0
            
        gap = hc - hc_nec
        
        if gap < 0: status = "🔴 Falta"
        elif gap == 0: status = "🟢 Ideal"
        else: status = "🔵 Sobra"
        
        return pd.Series([cap_dia_pessoa, hc_nec, gap, status])

    # Aplica cálculo
    df_editavel[["Cap. Real/Dia", "HC Nec.", "Gap", "Status"]] = df_editavel.apply(calcular_cenario, axis=1)

    # Exibe Gráfico e KPIs
    col1, col2 = st.columns([2, 1])
    with col1:
        # Prepara dados para o gráfico (Garante que não tenha None)
        df_grafico = df_editavel.fillna(0)
        fig = px.bar(
            df_grafico, 
            x="Processo", 
            y=["HC Atual", "HC Nec."], 
            barmode="group", 
            title="Planejado vs Necessário",
            color_discrete_map={"HC Atual": "#3498db", "HC Nec.": "#e74c3c"}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        gap_total = df_editavel["Gap"].fillna(0).sum()
        st.metric("Gap Total de Pessoas", f"{gap_total:.0f}")
        
        # Dataframe colorido com proteção
        display_geral = df_editavel[["Processo", "HC Atual", "HC Nec.", "Status"]].fillna(0)
        st.dataframe(
            display_geral.style.applymap(
                lambda x: 'color: red; font-weight: bold' if x == "🔴 Falta" else 'color: green' if x == "🟢 Ideal" else None, 
                subset=['Status']
            ),
            use_container_width=True
        )

# ==============================================================================
# ABAS OPERACIONAIS
# ==============================================================================
with abas[1]: # Courier
    dados = {"Atividade": ["Separação", "Embalagem"], "Mix/Participação (%)": [50, 50], "Meta (Unid/h/homem)": [100, 80], "HC Alocado": [5, 4]}
    renderizar_aba_padrao("Expedição Courier", dados, "courier", label_volume="Peças")

with abas[2]: # Recebimento
    dados = {"Atividade": ["Descarga", "Conferência"], "Mix/Participação (%)": [100, 100], "Meta (Unid/h/homem)": [300, 60], "HC Alocado": [3, 4]}
    renderizar_aba_padrao("Recebimento", dados, "rec", label_volume="peças")

with abas[3]: # Armazenagem
    dados = {"Atividade": ["Putaway", "Ressuprimento"], "Mix/Participação (%)": [80, 20], "Meta (Unid/h/homem)": [30, 40], "HC Alocado": [4, 2]}
    renderizar_aba_padrao("Armazenagem", dados, "arm", label_volume="peças")

with abas[4]: # Expedição Rodo
    dados = {"Atividade": ["Carregamento", "Auditoria"], "Mix/Participação (%)": [100, 20], "Meta (Unid/h/homem)": [500, 50], "HC Alocado": [4, 1]}
    renderizar_aba_padrao("Expedição Rodo", dados, "exp_rodo", label_volume="peças")

with abas[5]: # Inventário
    dados = {"Atividade": ["Contagem Cíclica", "Recontagem"], "Mix/Participação (%)": [90, 10], "Meta (Unid/h/homem)": [100, 50], "HC Alocado": [2, 1]}
    renderizar_aba_padrao("Inventário", dados, "inv", label_volume="Posições")

with abas[6]: # Outros
    dados = {"Atividade": ["Limpeza", "Apoio"], "Mix/Participação (%)": [100, 50], "Meta (Unid/h/homem)": [10, 10], "HC Alocado": [2, 1]}
    renderizar_aba_padrao("Outros", dados, "outros", label_volume="Geral")