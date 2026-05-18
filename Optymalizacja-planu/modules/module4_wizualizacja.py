import streamlit as st
import pandas as pd
from modules import modul1_parser
from modules import modul2_optymalizacja
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

# Konfiguracja strony
st.set_page_config(layout="wide", page_title="OptiPlan - Optymalizacja Planu")

# --- STYLE CSS ---
st.markdown("""
    <style>
    /* Tło całej aplikacji */
    .stApp { background-color: #f4f7f9; }
    
    /* Stylizacja 'kart' dla sekcji */
    div[data-testid="stVerticalBlock"] > div:has(div.element-container) {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    
    /* Ukrycie obramowania tabel */
    .stTable { border: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- MOCK DATA (Przykładowe dane) ---
hours = [f"{h:02d}:00" for h in range(8, 17)]
days = ["Pon", "Wt", "Śr", "Czw", "Pt"]

# --- SIDEBAR (Filtry i wybór perspektywy) ---
with st.sidebar:
    st.title("OptiPlan")
    st.caption("Optymalizacja planu zajęć")
    
    st.subheader("👀 WYBIERZ PERSPEKTYWĘ")
    perspektywa_typ = st.radio("Widok z perspektywy:", ["Grupa", "Prowadzący", "Sala"])
    
    if perspektywa_typ == "Grupa":
        context_name = st.selectbox("Wybierz grupę:", ["G1", "G2", "L1", "L2"])
        context_title = f"Grupy {context_name}"
    elif perspektywa_typ == "Prowadzący":
        context_name = st.selectbox("Wybierz prowadzącego:", ["dr Kowalski", "dr Wiśniewski", "mgr Nowak"])
        context_title = context_name
    else:
        context_name = st.selectbox("Wybierz salę:", ["101", "102", "201", "203"])
        context_title = f"Sali {context_name}"
        
    st.divider()
    
    st.subheader("🔍 DODATKOWE FILTRY")
    st.selectbox("Prowadzący", ["Wszyscy", "dr Kowalski", "dr Wiśniewski"], key="filter_prow")
    st.selectbox("Sala", ["Wszystkie", "101", "102", "201"], key="filter_sala")
    st.selectbox("Grupa", ["Wszystkie", "G1", "G2", "L1"], key="filter_grupa")
    st.selectbox("Typ zajęć", ["Wszystkie", "Wykład", "Ćwiczenia", "Lab"], key="filter_typ")
    
    if st.button("Zastosuj filtry", type="primary"):
        st.success("Zastosowano filtry!")
    st.button("Wyczyść filtry")


# --- FUNKCJE RENDERUJĄCE WIDOKI ---

def render_plan(context):
    st.header(f"📅 Plan zajęć - Widok: {context}")
    
    data = {day: ["---"] * len(hours) for day in days}
    df_plan = pd.DataFrame(data, index=hours)
    
    # Przykładowe wpisy symulujące plan
    df_plan.loc["08:00", "Pon"] = "Algorytmy (W)"
    df_plan.loc["10:00", "Pon"] = "Bazy danych (Ć)"
    df_plan.loc["08:00", "Wt"] = "Matematyka (Ć)"
    df_plan.loc["12:00", "Śr"] = "Fizyka (L)"
    df_plan.loc["14:00", "Czw"] = "Programowanie (L)"
    
    st.table(df_plan)


def render_optimization(context):
    st.header(f"📈 Postęp optymalizacji - Widok: {context}")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Przebieg algorytmów")
        iters = np.linspace(0, 100, 50)
        val_a = 40 * np.exp(-iters/40) + np.random.normal(0, 1, 50)
        val_b = 30 * np.exp(-iters/30) + np.random.normal(0, 1, 50)
        
        fig_opt = go.Figure()
        fig_opt.add_trace(go.Scatter(x=iters, y=val_a, name="Algorytm A", line=dict(color='#1f77b4')))
        fig_opt.add_trace(go.Scatter(x=iters, y=val_b, name="Algorytm B", line=dict(color='#2ca02c')))
        fig_opt.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_opt, use_container_width=True)

    with col2:
        st.subheader("Zaspokojenie ograniczeń")
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = 87,
            title = {'text': "Sukces (%)"},
            gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#007bff"}}
        ))
        fig_gauge.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)
        
    st.divider()
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.subheader("Wykorzystanie sal (Heatmapa)")
        rooms = ["s. 101", "s. 102", "s. 201", "s. 203"]
        usage = np.random.rand(4, 5) * 100
        fig_heat = px.imshow(usage, x=days, y=rooms, color_continuous_scale='Blues')
        fig_heat.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_heat, use_container_width=True)
        
    with col4:
        st.subheader("Obciążenie prowadzących")
        profs = ["dr Kowalski", "dr Wiśniewski", "mgr Nowak", "dr Zielińska"]
        load = [92, 85, 78, 90]
        fig_bar = px.bar(x=load, y=profs, orientation='h', labels={'x':'%', 'y':''}, color_discrete_sequence=['#007bff'])
        fig_bar.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_bar, use_container_width=True)


def render_statistics(context):
    st.header(f"📊 Raport statystyczny - Widok: {context}")
    st.markdown("Szczegółowe dane liczbowe i wykazy w formie tabelarycznej.")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Łączna liczba zajęć", "128")
    c2.metric("Naruszenia twarde", "0", "0", delta_color="off")
    c3.metric("Naruszenia miękkie", "5", "-2")
    c4.metric("Czas ostatniej optymalizacji", "12.4 s")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Wykaz Prowadzących")
        df_prowadzacy = pd.DataFrame({
            "Imię i nazwisko": ["dr Kowalski", "dr Wiśniewski", "mgr Nowak", "dr Zielińska"],
            "Zakład": ["Informatyka", "Matematyka", "Informatyka", "Fizyka"],
            "Liczba godzin (tyg)": [15, 12, 8, 10],
            "Preferencje spełnione": ["Tak", "Tak", "Nie", "Tak"]
        })
        st.dataframe(df_prowadzacy, use_container_width=True, hide_index=True)
        
    with col2:
        st.subheader("Wykaz Sal")
        df_sale = pd.DataFrame({
            "Sala": ["101", "102", "201", "203"],
            "Typ": ["Wykładowa", "Laboratoryjna", "Ćwiczeniowa", "Laboratoryjna"],
            "Pojemność": [120, 15, 30, 20],
            "Zajętość (%)": [95, 80, 65, 90]
        })
        st.dataframe(df_sale, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Wykaz Przedmiotów")
    df_przedmioty = pd.DataFrame({
        "Przedmiot": ["Algorytmy", "Bazy danych", "Matematyka dyskretna", "Sieci komputerowe"],
        "Forma": ["Wykład", "Laboratorium", "Ćwiczenia", "Wykład"],
        "Grupy": ["Wszystkie", "L1, L2", "G1, G2", "Wszystkie"],
        "Status przypisania": ["✅ Zakończone", "✅ Zakończone", "✅ Zakończone", "⚠️ Brak sali"]
    })
    st.dataframe(df_przedmioty, use_container_width=True, hide_index=True)


# --- GŁÓWNE ZAKŁADKI APLIKACJI ---
tab_plan, tab_opt, tab_stat = st.tabs(["📅 Plan zajęć", "📈 Optymalizacja", "📊 Raport statystyczny"])

with tab_plan:
    render_plan(context_title)

with tab_opt:
    render_optimization(context_title)

with tab_stat:
    render_statistics(context_title)
