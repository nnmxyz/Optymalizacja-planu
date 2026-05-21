import json
import requests
import time


API_URL = "http://149.156.194.192:8088/v1/chat/completions"
TOKEN = "bsk-00a229f80354793ad87e93fea4691b31521e4fb43a2cf8cd3d916fe02b64a010"
INPUT_FILE = "C:\\Users\\kapaw\\Downloads\\py\\dane_nowe.json"
OUTPUT_FILE = "dane_z_siatka.json"

def call_bielik_matrix_api(text):
    """Wysyła zapytanie do modelu Bielik i oczekuje struktury siatki tygodniowej."""
    
    system_prompt = (
        "Jesteś asystentem do analizy danych. Twoim zadaniem jest przetworzenie tekstu preferencji "
        "prowadzącego na ustrukturyzowany JSON reprezentujący siatkę godzinową dla dni: "
        "Mon, Tue, Wed, Thu, Fri. "
        "Dla każdego dnia stwórz listę wartości dla godzin od 8 do 19 (czyli 12 pozycji: indeks 0 to godzina 8, indeks 11 to godzina 19). "
        "Przypisz wartości liczbowe według zasad:\n"
        "0 - NIE MOGĘ (brak dostępności, zakaz, zebrania, badania),\n"
        "1 - MOGĘ W RAZIE POTRZEBY (warunkowo, wolę unikać, w ostateczności),\n"
        "2 - MOGĘ (na pewno, preferowane godziny, idealne rano/popołudniu).\n\n"
        "Format wyjściowy musi wyglądać dokładnie tak:\n"
        "{\n"
        "  \"Mon\": [2, 2, 2, 2, 0, 0, 0, 1, 1, 1, 1, 1],\n"
        "  \"Tue\": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],\n"
        "  ...\n"
        "}\n"
        "Zwróć wyłącznie czysty, poprawny JSON, bez żadnego dodatkowego tekstu czy komentarzy."
    )
    
    payload = {
        "model": "SpeakLeash/bielik-11b-v3.0-instruct:Q4_K_M",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        "temperature": 0.0
    }
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=40)
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            # Czyszczenie kodu ze znaczników markdown, które LLM czasem dodaje
            content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        elif response.status_code == 429:
            print("Przekroczono limit zapytań (429). Czekam na reset...")
            time.sleep(15)
            return None
        else:
            print(f"Błąd serwera Bielik: {response.status_code}")
            return None
    except Exception as e:
        print(f"Błąd połączenia z API: {e}")
        return None

def get_default_matrix():
    """Generuje domyślną bezpieczną siatkę (same jedynki) w razie awarii LLM."""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    return {day: [1] * 12 for day in days}

def main():
    # 1. Wczytanie pliku źródłowego (Moduł 1)
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Błąd: Nie znaleziono pliku {INPUT_FILE} w bieżącym katalogu.")
        return

    print(f"Rozpoczynam generowanie macierzy dostępności dla {len(data['instructors'])} prowadzących...")

    # 2. Przetwarzanie każdego profesora (Moduł 3)
    for i, instructor in enumerate(data['instructors']):
        name = instructor['name']
        text = instructor['preferences_text']
        
        print(f"[{i+1}/{len(data['instructors'])}] Przetwarzam: {name}")
        
        # Wywołanie modelu Bielik
        availability_matrix = call_bielik_matrix_api(text)
        
        # 3. Tryb awaryjny / Fallback offline w razie błędu serwera
        if availability_matrix is None:
            print(f" ! Problem z LLM dla {name}. Generuję siatkę domyślną (tryb offline).")
            availability_matrix = get_default_matrix()
            availability_matrix["offline_fallback"] = True
            
        # Zapisujemy nową siatkę bezpośrednio do danych tego prowadzącego
        instructor['availability_matrix'] = availability_matrix
        
        # Bezpieczny odstęp czasowy, aby nie przekroczyć limitu 60 zapytań na godzinę
        time.sleep(2)

    # 4. Zapisanie nowego pliku JSON dla Inżynierów Algorytmów
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\nSukces! Nowy plik z siatkami godzinowymi zapisany jako: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
