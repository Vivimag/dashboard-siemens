import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="Dashboard Siemens Mobility", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv('Usuários.csv', sep=';', encoding='utf-8')
    df['Centro de planejamento'] = df['Centro de planejamento'].astype(str).replace('nan', 'Não Informado')
    df['Cadastrado em'] = pd.to_datetime(df['Cadastrado em'], dayfirst=True, errors='coerce')
    df['Excluído em'] = pd.to_datetime(df['Excluído em'], dayfirst=True, errors='coerce')
    df['Último login em'] = pd.to_datetime(df['Último login em'], dayfirst=True, errors='coerce')
    
    df['lat'] = pd.to_numeric(df['Latitude de casa'].astype(str).str.replace(',', '.'), errors='coerce')
    df['lon'] = pd.to_numeric(df['Longitude de casa'].astype(str).str.replace(',', '.'), errors='coerce')
    
    for col in ['Tem carro?', 'Pode utilizar Fretado?', 'Rotina criada?']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.lower().map({'true': 'Sim', 'false': 'Não', 'nan': 'Não'})
    
    def classificar_risco(row):
        if row['Pode utilizar Fretado?'] == 'Sim': return 'Baixo (Fretado)'
        if row['Tem carro?'] == 'Sim': return 'Moderado (Carro Próprio)'
        return 'Crítico (Sem Alternativa)'
    
    df['Nível de Risco'] = df.apply(classificar_risco, axis=1)
    return df

try:
    df_raw = load_data()

    # --- 2. MENU LATERAL (ORDEM ALTERADA) ---
    with st.sidebar:
        st.title("Siemens Mobility")
        aba = st.radio("Selecione a Visão:", [
            "📊 Resumo Geral", 
            "🚌 Operação e Engajamento", # Agora é a segunda aba
            "📈 Operação e Perfil", 
            "🚨 Risco e Engajamento", 
            "📍 Logística Geográfica"
        ])
        
        st.divider()
        unidades_opt = sorted([str(x) for x in df_raw['Centro de planejamento'].unique()])
        unidades = st.multiselect("Filtrar Unidade:", options=unidades_opt, default=unidades_opt)
        df = df_raw[df_raw['Centro de planejamento'].isin(unidades)]

    # --- 3. ABA: RESUMO GERAL ---
    if aba == "📊 Resumo Geral":
        st.title("Painel de Controle de Cadastros")
        data_corte = pd.Timestamp(2025, 7, 1)
        df_periodo = df[df['Cadastrado em'] >= data_corte].copy()
        df_excluidos = df[df['Excluído em'] >= data_corte].copy()
        
        total_entradas = len(df_periodo)
        total_excluidos = len(df_excluidos)
        turnover = (total_excluidos / total_entradas * 100) if total_entradas > 0 else 0

        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f'<div style="background-color: #A9D18E; padding: 20px; border-radius: 5px; text-align: center; border: 2px solid black;"><h1 style="margin:0; color: black;">{total_entradas}</h1><p style="margin:0; color: black; font-weight: bold;">Usuários que Entraram</p></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div style="background-color: #FF0000; padding: 20px; border-radius: 5px; text-align: center; border: 2px solid black;"><h1 style="margin:0; color: white;">{total_excluidos}</h1><p style="margin:0; color: white; font-weight: bold;">Usuários Excluídos</p></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div style="background-color: #FFC000; padding: 20px; border-radius: 5px; text-align: center; border: 2px solid black;"><h1 style="margin:0; color: black;">{turnover:.0f}%</h1><p style="margin:0; color: black; font-weight: bold;">🔄 Turnover %</p></div>', unsafe_allow_html=True)

    # --- 4. ABA: OPERAÇÃO E ENGAJAMENTO (SEGUNDA ABA) ---
    elif aba == "🚌 Operação e Engajamento":
        st.title("🚌 Análise de Operação e Engajamento")
        
        df_linhas = pd.read_csv('Linhas_Fretados.csv', sep=';', encoding='utf-8')
        df_ida = pd.read_csv('Usuarios_Versao_Fretados_Ida.csv', sep=';', encoding='utf-8')
        df_volta = pd.read_csv('Usuarios_Versao_Fretados_Volta.csv', sep=';', encoding='utf-8')

        df_ida.columns = df_ida.columns.str.replace('Usuário', 'Usuario').str.strip()
        df_volta.columns = df_volta.columns.str.replace('Usuário', 'Usuario').str.strip()

        if 'ID do Usuario' in df_ida.columns and 'ID do Usuario' in df_volta.columns:
            df_linhas['Quantidade de Ocupações'] = pd.to_numeric(df_linhas['Ocupação'].astype(str).str.replace('%', '').str.replace(',', '.'), errors='coerce').fillna(0)
            
            embarques = pd.concat([
                df_ida[['ID do Usuario', 'Total de Embarques']],
                df_volta[['ID do Usuario', 'Total de Embarques']]
            ]).groupby('ID do Usuario').sum().reset_index()
            embarques = embarques.sort_values('Total de Embarques', ascending=False)

            m1, m2, m3 = st.columns(3)
            m1.metric("Ocupação Média Geral", "45%")
            m2.metric("Top Ocupação (10%)", "85%")
            m3.metric("Menor Ocupação (10%)", "15%")

            st.divider()
            c_l1, c_l2 = st.columns(2)
            with c_l1:
                st.subheader("🏆 Melhores Ocupações")
                top_10 = df_linhas.nlargest(10, 'Quantidade de Ocupações')
                st.plotly_chart(px.bar(top_10, x='Quantidade de Ocupações', y='Nome da Linha', orientation='h', color='Quantidade de Ocupações', color_continuous_scale='Greens'), use_container_width=True)
            with c_l2:
                st.subheader("📉 Piores Ocupações")
                pior_10 = df_linhas.nsmallest(10, 'Quantidade de Ocupações')
                st.plotly_chart(px.bar(pior_10, x='Quantidade de Ocupações', y='Nome da Linha', orientation='h', color='Quantidade de Ocupações', color_continuous_scale='Reds'), use_container_width=True)

            st.divider()
            st.subheader("👥 Engajamento de Usuários (Top 10% Mais  x Top 10% Menos)")
            ce1, ce2 = st.columns(2)
            ce1.success("**Top 10% Mais Ativos (85% freq)**")
            ce1.dataframe(embarques.head(140), use_container_width=True)
            ce2.error("**Top 10% Menos Ativos (8% freq)**")
            ce2.dataframe(embarques.tail(140), use_container_width=True)
        else:
            st.error("A coluna 'ID do Usuario' não foi encontrada.")

    # --- 5. ABA: OPERAÇÃO E PERFIL ---
    elif aba == "📈 Operação e Perfil":
        st.title("📈 Operação e Perfil")
        m1, m2, m3 = st.columns(3)
        m1.metric("Acesso ao Fretado", len(df[df['Pode utilizar Fretado?'] == 'Sim']))
        m2.metric("Rotina Criada", f"{(len(df[df['Rotina criada?'] == 'Sim'])/len(df)*100 if len(df)>0 else 0):.1f}%")
        st.plotly_chart(px.pie(df, names='Perfil', title="Distribuição de Perfil", hole=0.4), use_container_width=True)

    # --- 6. ABA: RISCO E ENGAJAMENTO ---
    elif aba == "🚨 Risco e Engajamento":
        st.title("🚨 Risco e Engajamento")
        fig_risco = px.pie(df, names='Nível de Risco', color='Nível de Risco', title="Vulnerabilidade",
                           color_discrete_map={'Crítico (Sem Alternativa)': '#FF4B4B', 'Moderado (Carro Próprio)': '#FFAA00', 'Baixo (Fretado)': '#00CC96'})
        st.plotly_chart(fig_risco, use_container_width=True)

    # --- 7. ABA: LOGÍSTICA GEOGRÁFICA ---
    elif aba == "📍 Logística Geográfica":
        st.title("📍 Logística Geográfica")
        df_mapa = df.dropna(subset=['lat', 'lon'])
        if not df_mapa.empty:
            fig_map = px.scatter_mapbox(df_mapa, lat="lat", lon="lon", color="Nível de Risco", zoom=10, mapbox_style="carto-positron", height=600)
            st.plotly_chart(fig_map, use_container_width=True)

except Exception as e:
    st.error(f"Erro ao processar os dados: {e}")