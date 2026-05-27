# modules/modul3_llm.py
import json
import requests
import time
import copy

# --- KONFIGURACJA API ---
API_URL = "http://149.156.194.192:8088/v1/chat/completions" 
TOKEN = "bsk-00a229f80354793ad87e93fea4691b31521e4fb43a2cf8cd3d916fe02b64a010"

def _call_bielik_api_batch(lista_danych):
    """Wysyła JEDNO ZBIORCZE zapytanie do modelu Bielik i zwraca siatki (0, 1, 2) dla wszystkich."""
    
    system_prompt = (
        "Jesteś zaawansowanym systemem ekstrakcji danych uczelnianych. Otrzymasz tablicę obiektów z ID wykładowcy i jego tekstem preferencji. "
        "Twoim zadaniem jest przetworzenie wszystkich na raz i zwrócenie JEDNEGO połączonego obiektu JSON, w którym kluczem jest 'id' wykładowcy.\n\n"
        
        "Dla każdego wykładowcy stwórz siatkę godzinową dla dni: Mon, Tue, Wed, Thu, Fri. "
        "Dla każdego dnia stwórz listę wartości dla godzin od 8 do 19 (czyli 12 pozycji: indeks 0 to godzina 8, indeks 11 to godzina 19).\n"
        "Przypisz wartości liczbowe według zasad:\n"
        "0 - NIE MOGĘ (brak dostępności, zakaz, zebrania, badania),\n"
        "1 - MOGĘ W RAZIE POTRZEBY (warunkowo, wolę unikać, w ostateczności),\n"
        "2 - MOGĘ (na pewno, preferowane godziny, idealne rano/popołudniu).\n\n"
        
        "### WYMAGANY SCHEMAT WYJŚCIA:\n"
        "{\n"
        "  \"ID_WYKLADOWCY_1\": {\n"
        "    \"Mon\": [2, 2, 2, 2, 0, 0, 0, 1, 1, 1, 1, 1],\n"
        "    \"Tue\": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],\n"
        "    ... (pozostałe dni)\n"
        "  },\n"
        "  \"ID_WYKLADOWCY_2\": { ... }\n"
        "}\n\n"
        "Zwróć WYŁĄCZNIE poprawny składniowo JSON. Nie dodawaj znaczników ```json ani tekstu pobocznego."
    )
    
    payload = {
        "model": "SpeakLeash/bielik-11b-v3.0-instruct:Q4_K_M",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(lista_danych, ensure_ascii=False)}
        ],
        "temperature": 0.0
    }
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=90)
        
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            content = content.replace("```json", "").replace("```", "").strip()
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            if start_idx != -1 and end_idx != -1:
                content = content[start_idx:end_idx+1]
                
            return json.loads(content)
        
        elif response.status_code == 429:
            # OPTYMALIZACJA: Jeśli serwer odrzuci nas ze względu na limit, 
            # wymuszamy solidny delay, zanim system spróbuje cokolwiek ponowić
            print("   [UWAGA] Przekroczono limit zapytań (429). Wymuszam opóźnienie 30 sekund...")
            time.sleep(30)
            return None
        else:
            print(f"   [BŁĄD] Odpowiedź API: {response.status_code}")
            return None
    except Exception as e:
        print(f"   [BŁĄD] Problem z połączeniem/parsowaniem: {e}")
        return None

def get_default_matrix():
    """Generuje domyślną bezpieczną siatkę (same jedynki) w razie awarii LLM."""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    return {day: [1] * 12 for day in days}

def przeanalizuj_preferencje(surowe_dane_json, tryb_offline=False, delay_seconds=3):
    print("\n-> MODUŁ 3 (LLM): Rozpoczęto analizę preferencji (tryb BATCH + MATRIX)...")
    
    if tryb_offline:
        print("   [INFO] Tryb offline. Automatyczne generowanie siatek domyślnych.")
        wzbogacone_dane = copy.deepcopy(surowe_dane_json)
        for inst in wzbogacone_dane.get('instructors', []):
            inst['availability_matrix'] = get_default_matrix()
        return wzbogacone_dane
        
    wzbogacone_dane = copy.deepcopy(surowe_dane_json)
    instructors = wzbogacone_dane.get('instructors', [])
    
    paczka_do_analizy = []
    for inst in instructors:
        if inst.get('preferences_text'):
            paczka_do_analizy.append({
                "id": inst['id'],
                "text": inst['preferences_text']
            })
            
    if not paczka_do_analizy:
        print("   [INFO] Brak preferencji do analizy.")
        return wzbogacone_dane
        
    # DODANE OPTYMALIZACYJNE OPÓŹNIENIE (Polityka bezpieczeństwa przed strzałem do API)
    if delay_seconds > 0:
        print(f"   [DANE] Wymuszam zapobiegawczy delay: {delay_seconds}s przed wysłaniem paczki...")
        time.sleep(delay_seconds)
        
    print(f"   [INFO] Wysyłam 1 ZBIORCZE zapytanie dla {len(paczka_do_analizy)} prowadzących...")
    
    wyniki_llm = _call_bielik_api_batch(paczka_do_analizy)
    
    if wyniki_llm is None:
        print("   [UWAGA] Zapytanie zbiorcze nie powiodło się. Uruchamiam fallback.")
        wyniki_llm = {}
        
    # Przypisywanie macierzy liczbowych do profesorów
    for inst in instructors:
        inst_id = inst['id']
        if inst_id in wyniki_llm:
            inst['availability_matrix'] = wyniki_llm[inst_id]
            print(f"   [OK] Wygenerowano macierz dla: {inst.get('name')}")
        else:
            print(f"   [UWAGA] Brak macierzy dla {inst.get('name')}. Ustawiam domyślną.")
            inst['availability_matrix'] = get_default_matrix()

    # Zapis do Cache dla zespołu
    cache_path = "data/dane_z_preferencjami_cache.json"
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(wzbogacone_dane, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    print("-> MODUŁ 3 (LLM): Zakończono z sukcesem.")
    return wzbogacone_dane
# --- PRODUKCYJNA SEKCJA URUCHAMIAJĄCA (ZAPIS DO PLIKU) ---
if __name__ == "__main__":
    INPUT_FILE = r"C:\Users\Natalka\Downloads\Optymalizacja-planu-master\Optymalizacja-planu-master\Optymalizacja-planu\data\dane_testowe.json"
    OUTPUT_FILE = "dane_z_siatka.json"

    print(f"1. Wczytuję surowy plik z dysku: {INPUT_FILE}...")
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            surowe_dane = json.load(f)
    except FileNotFoundError:
        print(f"[BŁĄD] Nie znaleziono pliku {INPUT_FILE}! Upewnij się, że leży w tym samym folderze co skrypt.")
        exit()

    print("2. Wysyłam zapytanie zbiorcze (Batch) do modelu Bielik...")
    # tryb_offline=False, żeby faktycznie połączyć się z serwerem uczelni
    wzbogacone_dane = przeanalizuj_preferencje(surowe_dane, tryb_offline=False, delay_seconds=3)

    print(f"3. Zapisuję gotowe macierze do nowego pliku: {OUTPUT_FILE}...")
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(wzbogacone_dane, f, indent=2, ensure_ascii=False)
        print(f"\n[SUKCES] Sukces! Plik '{OUTPUT_FILE}' pojawił się na Twoim komputerze.")
        print("Możesz go teraz otworzyć lub wysłać reszcie zespołu.")
    except Exception as e:
        print(f"[BŁĄD] Nie udało się zapisać pliku na dysku: {e}")