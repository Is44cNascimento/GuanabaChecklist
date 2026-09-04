import json
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Dashboard de Checklists",
    page_icon="🚛",
    layout="wide"
)

# Estilização CSS customizada
st.markdown("""
    <style>
    .main {
        background-color: #FAFAFA;
    }
    div[data-testid="stButton"] > button {
        border: none;
        background: transparent;
        color: #1E293B;
        font-size: 18px;
        font-weight: bold;
        padding: 0;
    }
    div[data-testid="stButton"] > button:hover {
        color: #0284C7;
        background: transparent;
    }
    </style>
""", unsafe_allow_html=True)


col_logo_left, col_logo_center, col_logo_right = st.columns([1, 2, 1])

with col_logo_center:
    try:
        st.image("guanabara.png", use_container_width=True)
    except:
        st.markdown("<h2 style='text-align: center;'>GUANABARA</h2>", unsafe_allow_html=True)


# ==========================================
# 2. CONEXÃO COM O BANCO DE DADOS POSTGRESQL
# ==========================================
@st.cache_resource
def get_db_connection():
    dialect = "postgresql"
    host = "postgres"
    port = "5432"
    database = "checklist"
    username = "Isaac"
    password = "1234"
    
    db_url = f"{dialect}://{username}:{password}@{host}:{port}/{database}"
    
    try:
        engine = create_engine(db_url)
        return engine
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return None

def extract_inconformities_list(checklist_json):
    """
    Retorna uma lista com os nomes de todos os itens do checklist que estão marcados como False (com defeito).
    """
    if not checklist_json:
        return []
    
    if isinstance(checklist_json, str):
        try:
            checklist_json = json.loads(checklist_json)
        except:
            return []
            
    inconformidades = []
    
    if isinstance(checklist_json, dict):
        for key, value in checklist_json.items():
            # Se for booleano False ou string 'nok'/'defeito'
            if value is False or str(value).lower() in ['nok', 'defeito', 'ruim', 'não', 'nao', 'inconforme']:
                inconformidades.append(key)
            elif isinstance(value, dict) and value.get('status') in ['nok', 'defeito', False]:
                inconformidades.append(key)
                
    elif isinstance(checklist_json, list):
        for item in checklist_json:
            if isinstance(item, dict):
                nome_item = item.get('nome') or item.get('item') or item.get('key') or "Item sem nome"
                if item.get('status') in ['nok', 'defeito', False] or item.get('conforme') is False:
                    inconformidades.append(nome_item)
                    
    return inconformidades


def calculate_inconformities(checklist_json):
    """Retorna a quantidade de inconformidades."""
    return len(extract_inconformities_list(checklist_json))


@st.cache_data(ttl=30)
def load_data():
    engine = get_db_connection()
    if not engine:
        return pd.DataFrame()
    
    query = """
        SELECT 
            id,
            operator_name,
            car_prefix,
            checklist,
            started_at,
            submitted_at,
            completed_at
        FROM public.checklist_submissions
        ORDER BY submitted_at DESC NULLS LAST, id DESC
    """
    try:
        df = pd.read_sql(query, engine)
    except Exception as e:
        st.error(f"Erro na consulta SQL: {e}")
        return pd.DataFrame()

    if df.empty:
        return df

    # Trata as datas da tabela
    df['started_at'] = pd.to_datetime(df['started_at'])
    df['submitted_at'] = pd.to_datetime(df['submitted_at'])
    df['ref_date'] = df['submitted_at'].fillna(df['started_at'])
    
    dias_semana = {0: 'Seg', 1: 'Ter', 2: 'Quar', 3: 'Quin', 4: 'Sex', 5: 'Sab', 6: 'Dom'}

    df['ref_date'] = pd.to_datetime(
    df['ref_date'],
    errors='coerce'
)


    df['dia_semana_num'] = df['ref_date'].dt.dayofweek
    df['dia_semana'] = df['dia_semana_num'].map(dias_semana)
    
    # Processa contagem e lista de inconformidades
    df['lista_inconformidades'] = df['checklist'].apply(extract_inconformities_list)
    df['inconformidades'] = df['lista_inconformidades'].apply(len)
    
    return df


# ==========================================
# MODAL / POP-UP (st.dialog)
# ==========================================
@st.dialog("Detalhamento de Inconformidades")
def show_inconformities_modal(car_prefix, operator_name, itens_inconformes):
    st.write(f"**Veículo:** {car_prefix}")
    st.write(f"**Operador:** {operator_name}")
    st.markdown("---")
    
    if not itens_inconformes:
        st.success("✅ Nenhuma inconformidade encontrada para este veículo!")
    else:
        st.markdown("#### 🚨 Itens com problemas (Não Conformes):")
        for item in itens_inconformes:
            st.error(f"❌ {item}")


df = load_data()

if df.empty:
    st.info("Nenhum registro encontrado na tabela public.checklist_submissions.")
    st.stop()


# ==========================================
# 3. FILTRO LATERAL
# ==========================================
st.sidebar.header("Filtros")
operadores = ["Todos"] + sorted(list(df['operator_name'].dropna().unique()))
op_selecionado = st.sidebar.selectbox("Operador", operadores)

if op_selecionado != "Todos":
    df_filtered = df[df['operator_name'] == op_selecionado]
else:
    df_filtered = df.copy()


# ==========================================
# 4. GRÁFICOS PRINCIPAIS
# ==========================================
col_chart1, col_chart2 = st.columns([1, 1])

# --- GRÁFICO 1: Métrica Semanal ---
with col_chart1:
    st.markdown("### Métrica semanal")
    
    ordem_dias = ['Dom', 'Seg', 'Ter', 'Quar', 'Quin', 'Sex', 'Sab']
    map_ordem = {'Dom': 0, 'Seg': 1, 'Ter': 2, 'Quar': 3, 'Quin': 4, 'Sex': 5, 'Sab': 6}
    
    df_weekly = df_filtered.groupby('dia_semana').size().reset_index(name='Carros')
    df_full_days = pd.DataFrame({'dia_semana': ordem_dias, 'ordem': range(7)})
    df_weekly = pd.merge(df_full_days, df_weekly, on='dia_semana', how='left').fillna(0)
    df_weekly = df_weekly.sort_values('ordem')
    
    fig_line = px.line(df_weekly, x='dia_semana', y='Carros', markers=True)
    fig_line.update_traces(
        line_color='#8B5CF6', 
        marker=dict(size=8, color='#8B5CF6'),
        line=dict(width=2)
    )
    fig_line.update_layout(
        xaxis_title="",
        yaxis_title="",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=280,
        margin=dict(l=20, r=20, t=20, b=20),
        yaxis=dict(showgrid=True, gridcolor='#E5E7EB', zeroline=False),
        xaxis=dict(showgrid=False)
    )
    st.plotly_chart(fig_line, use_container_width=True)

# --- GRÁFICO 2: Produção por Operador ---
with col_chart2:
    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    
    df_ops = df_filtered.groupby('operator_name').size().reset_index(name='qtd').sort_values('qtd', ascending=True)
    
    fig_bar = px.bar(df_ops, y='operator_name', x='qtd', orientation='h', text='qtd')
    fig_bar.update_traces(
        marker_color='#0284C7',
        textposition='outside',
        texttemplate='%{text}',
        textfont=dict(color='#0284C7', size=14, family="Arial")
    )
    fig_bar.update_layout(
        xaxis_title="",
        yaxis_title="",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=280,
        margin=dict(l=20, r=40, t=10, b=20),
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=False)
    )
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)


# ==========================================
# 5. LISTA DE VEÍCULOS E INCONFORMIDADES
# ==========================================
col_left, col_right = st.columns([3, 1])

with col_left:
    for idx, row in df_filtered.head(10).iterrows():
        n_inc = int(row['inconformidades'])
        lista_inc = row['lista_inconformidades']
        
        # Define a cor do badge (Verde = 0, Amarelo = 1 a 3, Vermelho = > 3)
        if n_inc == 0:
            badge_color = "#00FF66"
        elif n_inc <= 3:
            badge_color = "#FFFF00"
        else:
            badge_color = "#FF0000"
            
        c_veic, c_inconf, c_badge = st.columns([2, 2, 1])
        
        with c_veic:
            st.markdown(
                f"<div style='font-size: 18px; font-weight: bold; color: #1E293B; margin-top: 5px;'>"
                f"VEÍCULO &nbsp;&nbsp;&nbsp; {row['car_prefix']}</div>", 
                unsafe_allow_html=True
            )
        
        with c_inconf:
            # Botão interativo que substitui o texto estático e abre o Pop-up/Modal ao clicar
            if st.button(f"INCONFORMIDADE    {n_inc}", key=f"btn_inc_{row['id']}"):
                show_inconformities_modal(row['car_prefix'], row['operator_name'], lista_inc)
            
        with c_badge:
            st.markdown(f"""
                <div style="
                    background-color: {badge_color}; 
                    width: 32px; 
                    height: 32px; 
                    border-radius: 4px; 
                    margin-top: 2px;">
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

with col_right:
    st.markdown("""
        <div style="border-left: 2px solid #000; height: 280px; margin-left: 30px;"></div>
    """, unsafe_allow_html=True)