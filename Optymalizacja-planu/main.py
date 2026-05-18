import os
import sys
import json
import time
import subprocess

# Importujemy nasze moduły
from modules import modul1_parser
from modules import modul2_optymalizacja
from modules import modul3_llm
# Modułu 4 (Wizualizacji) nie importujemy bezpośrednio, bo odpala się go przez Streamlit

# ==========================================
# KONFIGURACJA GŁÓWNA SYSTEMU
# ==========================================
PLIK_WEJSCIOWY = "data/dane_testowe.json"

# Przełącznik dla API: 
# True  = szybki test na wbudowanych danych (nie wysyła zapytań do UPEL)
# False = łączy się z serwerem i modelem Bielik 11b
TRYB_OFFLINE_LLM = True  

def uruchom_system():
    print("="*60)
    print(" 🚀 START SYSTEMU HARMONOGRAMOWANIA OPTIPLAN (AGH)")
    print("="*60)
    
    start_time = time.time()
    
    # --- ETAP 1: Wczytanie danych wejściowych ---
    print("\n[1/4] Wczytywanie surowych danych wejściowych...")
    if not os.path.exists(PLIK_WEJSCIOWY):
        print(f"❌ BŁĄD KRYTYCZNY: Nie znaleziono pliku '{PLIK_WEJSCIOWY}'!")
        print("Upewnij się, że masz folder 'data' z odpowiednim plikiem JSON.")
        sys.exit(1)
        
    with open(PLIK_WEJSCIOWY, 'r', encoding='utf-8') as f:
        surowe_dane = json.load(f)

    # --- ETAP 2: Moduł 3 (LLM) ---
    print("\n[2/4] Uruchamianie Modułu 3 (Analiza Preferencji LLM)...")
    dane_z_preferencjami = modul3_llm.przeanalizuj_preferencje(surowe_dane, tryb_offline=TRYB_OFFLINE_LLM)

    # --- ETAP 3: Moduł 1 (Parser) ---
    print("\n[3/4] Uruchamianie Modułu 1 (Budowa Struktur Danych)...")
    prowadzacy_db, sale_db, przedmioty_db = modul1_parser.zbuduj_baze_obiektow(dane_z_preferencjami)

    # --- ETAP 4: Moduł 2 (Optymalizacja / Algorytm Bazowy) ---
    print("\n[4/4] Uruchamianie Modułu 2 (Silnik Optymalizacji)...")
    stan_bazowy = modul2_optymalizacja.StanPlanu()
    algorytm = modul2_optymalizacja.AlgorytmKonstruktywny(stan_bazowy, prowadzacy_db, sale_db, przedmioty_db)
    
    czy_sukces = algorytm.rozwiaz()
    czas_dzialania = time.time() - start_time
    
    # --- PODSUMOWANIE W KONSOLI ---
    print("\n" + "="*60)
    if czy_sukces:
        print(f" ✅ SUKCES! Znaleziono poprawny plan bazowy (HC = 0).")
        print(f" ⏱️ Czas weryfikacji i układania: {czas_dzialania:.3f} sekund")
        print(f" 📊 Zaplanowano zajęć: {len(algorytm.lista_zajec)}")
    else:
        print(" ❌ PORAŻKA: Algorytm Konstruktywny nie znalazł legalnego ułożenia!")
    print("="*60)

    # --- ETAP 5: Uruchomienie interfejsu graficznego (Streamlit) ---
    print("\nCzy chcesz uruchomić graficzny interfejs (Dashboard Streamlit)?")
    wybor = input("Wpisz 'T' (Tak) lub 'N' (Nie) i wciśnij Enter: ").strip().upper()
    
    if wybor == 'T':
        print("\nUruchamianie serwera wizualizacji... (Za chwilę w przeglądarce otworzy się nowa karta)")
        # Ten kod wyręcza Was z wpisywania komendy w terminalu!
        subprocess.Popen(["streamlit", "run", "modules/modul4_wizualizacja.py"])
    else:
        print("\nZakończono pracę programu.")

if __name__ == "__main__":
    uruchom_system()
