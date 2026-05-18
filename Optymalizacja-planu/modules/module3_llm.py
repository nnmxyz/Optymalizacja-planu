# modules/modul3_llm.py
import json
import requests
import time
import copy

# --- KONFIGURACJA API ---
API_URL = "http://149.156.194.192:8088/v1/chat/completions" # IP z UPEL
TOKEN = "bsk-00a229f80354793ad87e93fea4691b31521e4fb43a2cf8cd3d916fe02b64a010"

def _call_bielik_api(text):
    """Wysyła pojedyncze zapytanie do modelu Bielik (funkcja wewnętrzna)."""
    system_prompt = (
        "Jesteś asystentem do analizy danych. Przetwórz tekst preferencji na JSON. "
        "Użyj kluczy: 'preferred_days' (lista skrótów: Mon, Tue, Wed, Thu, Fri), "
        "'preferred_hours_start' (int), 'preferred_hours_end' (int), "
        "'forbidden_slots' (lista obiektów {'day': skrót, 'from': int, 'to': int}). "
        "Zwróć wyłącznie czysty JSON, bez komentarzy."
    )
    
    payload = {
        "model": "SpeakLeash/bielik-11b-v3.0-instruct:Q4_K_M",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        "temperature": 0.1 # Niska temperatura dla większej precyzji
    }
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            # Czyszczenie odpowiedzi z ewentualnych znaczników markdown
            content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        elif response.status_code == 429:
            print("   [UWAGA] Limit zapytań API przekroczony! Czekam 10 sekund...")
            time.sleep(10)
            return None
        else:
            print(f"   [BŁĄD] Odpowiedź API: {response.status_code}")
            return None
    except Exception as e:
        print(f"   [BŁĄD] Problem z połączeniem: {e}")
        return None

def przeanalizuj_preferencje(surowe_dane_json, tryb_offline=True):
    """
    Moduł 3: Ekstrakcja preferencji.
    Główny interfejs wejściowy wywoływany przez nasz główny system.
    """
    print("\n-> MODUŁ 3 (LLM): Rozpoczęto analizę preferencji...")
    
    # 1. Obsługa Trybu Offline (dla szybkiego testowania UI / algorytmów)
    if tryb_offline:
        print("   [INFO] Przełącznik tryb_offline=True. Pomijam łączenie z serwerem UPEL.")
        return surowe_dane_json
        
    # Kopiujemy dane, żeby nie nadpisywać oryginału zanim nie skończymy
    wzbogacone_dane = copy.deepcopy(surowe_dane_json)
    instructors = wzbogacone_dane.get('instructors', [])
    
    print(f"   [INFO] Zaczynam wysyłać zapytania dla {len(instructors)} prowadzących...")

    # 2. Iteracja i wzbogacanie danych
    for i, instructor in enumerate(instructors):
        name = instructor.get('name', 'Nieznany')
        text = instructor.get('preferences_text', '')
        
        # Jeśli profesor nie wpisał żadnych preferencji
        if not text:
            continue
            
        print(f"   [{i+1}/{len(instructors)}] API Bielik przetwarza: {name}...")
        
        extracted = _call_bielik_api(text)
        
        # 3. Obsługa fallback (Tryb awaryjny dla konkretnego profesora)
        if extracted is None:
            print(f"   [UWAGA] Nie udało się pobrać danych dla {name}. Ustawiam puste preferencje.")
            extracted = {
                "preferred_days": [],
                "preferred_hours_start": 8,
                "preferred_hours_end": 20,
                "forbidden_slots": []
            }
        
        # 4. Zapisujemy pod kluczem ZGODNYM z naszym Parserem (Moduł 1)
        instructor['parsed_preferences'] = extracted
        
        # Szanujemy limity serwera
        time.sleep(1) 

    # 5. Zapisanie kopii zapasowej (cache) do pliku w folderze data/
    cache_path = "data/dane_z_preferencjami_cache.json"
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(wzbogacone_dane, f, indent=2, ensure_ascii=False)
        print(f"   [INFO] Kopia zapasowa pobranych danych zapisana w: {cache_path}")
    except Exception as e:
        print(f"   [UWAGA] Nie udało się zapisać pliku cache: {e}")

    print("-> MODUŁ 3 (LLM): Zakończono z sukcesem.")
    return wzbogacone_dane
