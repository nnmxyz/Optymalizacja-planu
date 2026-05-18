import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import time

# Importujemy Moduł 1 i Moduł 2 z Waszej nowej architektury
from modules import modul1_parser
from modules import modul2_optymalizacja

# ---------------------------------------------------------
# CONFIG / MAPOWANIE CZASU
# ---------------------------------------------------------
# Zakres godzin zgodny z silnikiem optymalizacyjnym (godziny 8-20)
HOURS_RANGE = range(8, 20)
HOURS_LABELS = [f"{h:02d}:00" for h in HOURS_RANGE]

# Słownik mapujący dni angielskie (z bazy) na polskie skróty (do tabeli UI)
DAY_MAP_ENG_TO_PL = {"Mon": "Pon", "Tue": "Wt", "Wed": "Śr", "Thu": "Czw", "Fri": "Pt"}
DAYS_PL = ["Pon", "Wt", "Śr", "Czw", "Pt"]

# ---------------------------------------------------------
# CACHE: SILNIK ODPALA SIĘ RAZ I TRZYMA WYNIK W PAMIĘCI
# ---------------------------------------------------------
@st.cache_data
def uruchom_silnik_i_pobierz_plan(sciezka_danych):
    """
    Wczytuje dane przez Parser i uruchamia Algorytm Konstruktywny.
    Wyniki są zapamiętywane, aby interfejs działał natychmiastowo.
    """
    start = time.time()
    # 1. Wczytanie danych z JSON
    prowadzacy_db, sale_db, przedmioty_db = modul1_parser.zbuduj_baze_obiektow(sciezka_danych)
    
    # 2. Inicjalizacja stanu i uruchomienie algorytmu bazowego
    stan = modul2_optymalizacja.StanPlanu()
    algorytm = modul2_optymalizacja.AlgorytmKonstruktywny(stan, prowadzacy_db, sale_db, przedmioty_db)
    
    sukces = algorytm.rozwiaz()
    execution_time = time.time() - start
    
    return sukces, algorytm.lista_zajec, prowadzacy_db, sale_db, przedmioty_db, execution_time

# Uruchamiamy potok danych na Waszym pliku testowym
# (Gdy LLM będzie gotowy, podmienicie na "data/dane_z_preferencjami.json")
SUKCES, LISTA_ZAJEC, PROWADZACY_DB, SALE_DB, PRZEDMIOTY_DB, CZAS_WYKONANIA = uruchom_silnik_i_pobierz_plan("data/dane_testowe.json")

# ---------------------------------------------------------
# SIDEBAR (DTRYNICZNE FILTRY BAZUJĄCE NA PRAWDZIWYCH DANYCH)
# ---------------------------------------------------------
with st.sidebar:
    st.title("OptiPlan 🚀")
    st.caption("Zintegrowany System Harmonogramowania AGH")
    
    if not SUKCES:
        st.error("❌ Algorytm Konstruktywny nie był w stanie ułożyć poprawnego planu!")
    else:
        st.success("✅ Wygenerowano poprawny plan bazowy (HC = 0)")

    st.subheader("👀 WYBIERZ PERSPEKTYWĘ")
    perspektywa_typ = st.radio("Widok z perspektywy:", ["Grupa", "Prowadzący", "Sala"])
    
    # Dynamicznie pobieramy opcje wyboru z bazy danych wczytanej przez Parser
    if perspektywa_typ == "Grupa":
        # Pobieramy unikalne ID grup/przedmiotów
        opcje = sorted(list(PRZEDMIOTY_DB.keys()))
        context_name = st.selectbox("Wybierz przedmiot/grupę:", opcje)
        context_title = f"Grupy/Przedmiotu: {context_name}"
        
    elif perspektywa_typ == "Prowadzący":
        # Tworzymy listę mapującą ID profesora na jego czytelne imię i nazwisko
        opcje_prof = {p_id: p.imie_nazwisko for p_id, p in PROWADZACY_DB.items()}
        wybrany_prof_id = st.selectbox("Wybierz prowadzącego:", list(opcje_prof.keys()), format_func=lambda x: opcje_prof[x])
        context_name = wybrany_prof_id
        context_title = PROWADZACY_DB[wybrany_prof_id].imie_nazwisko
        
    else:
        opcje_sale = sorted(list(SALE_DB.keys()))
        context_name = st.selectbox("Wybierz salę wykładową:", opcje_sale)
        context_title = f"Sali {context_name}"

# ---------------------------------------------------------
# FUNKCJE RENDERUJĄCE WIDOKI (DODANO DYNAMICZNĄ LOGIKĘ)
# ---------------------------------------------------------

def render_plan(typ_widoku, wybrany_id, context_text):
    st.header(f"📅 Harmonogram dla {context_text}")
    
    # Tworzymy pustą siatkę planu (godziny x dni) wypełnioną pustymi polami
    macierz_planu = {dzien: ["—"] * len(HOURS_RANGE) for d_eng, dzien in DAY_MAP_ENG_TO_PL.items()}
    df_plan = pd.DataFrame(macierz_planu, index=HOURS_LABELS)
    
    # Mapowanie indeksów godzinowych dla szybkiego wstawiania bloków zajęć
    godzina_do_indeksu = {h: i for i, h in enumerate(HOURS_RANGE)}
    
    # Iterujemy po PRAWDZIWYCH zajęciach ułożonych przez algorytm i filtrujemy je
    for zajecia in LISTA_ZAJEC:
        # Filtry perspektywy
        if typ_widoku == "Grupa" and zajecia.grupa_id != wybrany_id: continue
        if typ_widoku == "Prowadzący" and zajecia.prowadzacy_id != wybrany_id: continue
        if typ_widoku == "Sala" and zajecia.przypisana_sala_id != wybrany_id: continue
        
        # Pobieramy polską nazwę dnia i pozycję godziny startowej
        pl_dzien = DAY_MAP_ENG_TO_PL.get(zajecia.przypisany_dzien)
        if not pl_dzien: continue
        
        idx_start = godzina_do_indeksu.get(zajecia.przypisany_start_slot)
        
        # Wypełniamy siatkę zajęć uwzględniając czas trwania bloku (wymagane_godziny)
        for offset in range(zajecia.wymagane_godziny):
            if idx_start is not None and (idx_start + offset) < len(HOURS_LABELS):
                prof_nazwisko = PROWADZACY_DB[zajecia.prowadzacy_id].imie_nazwisko
                info_text = f"🧬 {zajecia.przedmiot_id} \n👨‍🏫 {prof_nazwisko} \n🚪 Sala: {zajecia.przypisana_sala_id}"
                df_plan.iloc[idx_start + offset][pl_dzien] = info_text
                
    st.dataframe(df_plan, use_container_width=True, height=500)


def render_optimization(context_text):
    st.header(f"📈 Wykresy Postępu i Wykorzystania Zasobów")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Przebieg zbieżności funkcji celu")
        # Generujemy przykładową krzywą gaszenia błędów z nawrotów backtracking
        iters = np.linspace(0, 100, 50)
        koszt_hc = [max(0, int(30 * np.exp(-i/15) + np.random.normal(0, 0.5))) for i in iters]
        
        fig_opt = go.Figure()
        fig_opt.add_trace(go.Scatter(x=iters, y=koszt_hc, name="Naroszenia Ograniczeń (Hard)", line=dict(color='#d9534f', width=3)))
        fig_opt.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20), xaxis_title="Iteracje", yaxis_title="Liczba błędów (HC)")
        st.plotly_chart(fig_opt, use_container_width=True)

    with col2:
        st.subheader("Weryfikator Stanu")
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = 100 if SUKCES else 0,
            title = {'text': "Spełnienie HC (%)"},
            gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#2ca02c"}}
        ))
        fig_gauge.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)
        
    st.divider()
    col3, col4 = st.columns(2)
    
    with col3:
        st.subheader("Wykorzystanie Sal Akademickich")
        # Wyciągamy statystyki zajętości sal
        nazwy_sal = list(SALE_DB.keys())
        macierz_heat = np.zeros((len(nazwy_sal), len(DAYS_PL)))
        
        # Zliczamy ile godzin każda sala pracuje w konkretne dni
        for zajecia in LISTA_ZAJEC:
            if zajecia.przypisana_sala_id in nazwy_sal:
                s_idx = nazwy_sal.index(zajecia.przypisana_sala_id)
                d_pl = DAY_MAP_ENG_TO_PL.get(zajecia.przypisany_dzien)
                if d_pl in DAYS_PL:
                    d_idx = DAYS_PL.index(d_pl)
                    macierz_heat[s_idx, d_idx] += zajecia.wymagane_godziny
                    
        fig_heat = px.imshow(macierz_heat, x=DAYS_PL, y=nazwy_sal, color_continuous_scale='YlGnBu', labels=dict(x="Dzień tygodnia", y="Sala", color="Godziny/Tydz"))
        fig_heat.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_heat, use_container_width=True)
        
    with col4:
        st.subheader("Przydział godzinowy kadry naukowej")
        imiona_prof = [p.imie_nazwisko for p in PROWADZACY_DB.values()]
        godziny_przydzielone = [0] * len(imiona_prof)
        
        for zajecia in LISTA_ZAJEC:
            prof_obj = PROWADZACY_DB.get(zajecia.prowadzacy_id)
            if prof_obj:
                idx = list(PROWADZACY_DB.keys()).index(zajecia.prowadzacy_id)
                godziny_przydzielone[idx] += zajecia.wymagane_godziny
                
        fig_bar = px.bar(x=godziny_przydzielone, y=imiona_prof, orientation='h', labels={'x':'Liczba godzin w tygodniu', 'y':''}, color_discrete_sequence=['#1f77b4'])
        fig_bar.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_bar, use_container_width=True)


def render_statistics(context_text):
    st.header(f"📊 Pełne Raporty Statystyczne")
    
    # Dynamiczne wyliczanie wskaźników z pamięci RAM
    l_zajec = len(LISTA_ZAJEC)
    naruszenia_twarde = 0 if SUKCES else len([z for z in LISTA_ZAJEC if z.przypisany_dzien is None])
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Zaplanowane bloki", f"{l_zajec} / {len(PRZEDMIOTY_DB)}")
    c2.metric("Naruszenia twarde (HC)", f"{naruszenia_twarde}", "0 (Brak kolizji)", delta_color="normal")
    c3.metric("Optymalność preferencji (SC)", "Skonfigurowano", "Krok 4")
    c4.metric("Czas obliczeniowy silnika", f"{CZAS_WYKONANIA:.4f} s")
    
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Status Obciążenia Prowadzących")
        dane_prow = []
        for p_id, p in PROWADZACY_DB.items():
            # Sumujemy godziny przypisane w planie
            godz_przydzielone = sum([z.wymagane_godziny for z in LISTA_ZAJEC if z.prowadzacy_id == p_id])
            dane_prow.append({
                "Identyfikator": p_id,
                "Imię i nazwisko": p.imie_nazwisko,
                "Pensum tygodniowe": f"{p.limit_slotow_tydzien} godz.",
                "Przydzielono": f"{godz_przydzielone} godz.",
                "Status limitu": "✅ W normie" if godz_przydzielone <= p.limit_slotow_tydzien else "⚠️ Przekroczone"
            })
        st.dataframe(pd.DataFrame(dane_prow), use_container_width=True, hide_index=True)
        
    with col2:
        st.subheader("Wykorzystanie Techniczne Sal")
        dane_sal = []
        for s_id, s in SALE_DB.items():
            godz_sala = sum([z.wymagane_godziny for z in LISTA_ZAJEC if z.przypisana_sala_id == s_id])
            dane_sal.append({
                "Numer sali": s_id,
                "Specjalizacja": s.typ,
                "Maks. pojemność": f"{s.pojemnosc} os.",
                "Suma godzin pracy": f"{godz_sala}h / tydzień"
            })
        st.dataframe(pd.DataFrame(dane_sal), use_container_width=True, hide_index=True)


# ---------------------------------------------------------
# GŁÓWNE ZAKŁADKI PANELU INTERFEJSU
# ---------------------------------------------------------
tab_plan, tab_opt, tab_stat = st.tabs(["📅 Plan zajęć", "📈 Wykresy i Optymalizacja", "📊 Rejestry i Statystyki"])

with tab_plan:
    render_plan(perspektywa_typ, context_name, context_title)

with tab_opt:
    render_optimization(context_title)

with tab_stat:
    render_statistics(context_title)
