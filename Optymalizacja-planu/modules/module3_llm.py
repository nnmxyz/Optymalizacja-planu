import json
import requests
import time

# --- KONFIGURACJA ---
API_URL = "http://149.156.194.192:8088/v1/chat/completions" # Podmień na IP z UPEL
TOKEN = "bsk-00a229f80354793ad87e93fea4691b31521e4fb43a2cf8cd3d916fe02b64a010" # Twój token
INPUT_FILE = "C:\\Users\\kapaw\\Downloads\\py\\dane_nowe.json"
OUTPUT_FILE = "dane_z_preferencjami.json"

def call_bielik_api(text):
    """Wysyła pojedyncze zapytanie do modelu Bielik."""
    system_prompt = (
        "Jesteś asystentem do analizy danych. Przetwórz tekst preferencji na JSON. "
        "Użyj kluczy: 'preferred_days' (lista skrótów: Mon, Tue, Wed, Thu, Fri, Sat, Sun), "
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
            # Czyszczenie odpowiedzi z ewentualnych znaczników markdown ```json ... ```
            content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        elif response.status_code == 429:
            print("Limit zapytań przekroczony! Czekam 10 sekund...")
            time.sleep(10)
            return None
        else:
            print(f"Błąd API: {response.status_code}")
            return None
    except Exception as e:
        print(f"Błąd połączenia: {e}")
        return None

def main():
    # 1. Wczytanie pliku (Moduł 1: Parser)
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Nie znaleziono pliku {INPUT_FILE}!")
        return

    print(f"Rozpoczynam analizę {len(data['instructors'])} prowadzących...")

    # 2. Iteracja i wzbogacanie danych (Twoje zadanie główne)
    for i, instructor in enumerate(data['instructors']):
        name = instructor['name']
        text = instructor['preferences_text']
        
        print(f"[{i+1}/{len(data['instructors'])}] Analizuję: {name}")
        
        # Wywołanie Bielika
        extracted = call_bielik_api(text)
        
        # 3. Obsługa fallback (Tryb Offline/Błędy)
        if extracted is None:
            print(f" ! Nie udało się pobrać danych dla {name}. Ustawiam puste preferencje.")
            extracted = {
                "preferred_days": [],
                "preferred_hours_start": 8,
                "preferred_hours_end": 20,
                "forbidden_slots": [],
                "error": True
            }
        
        # Dodanie nowej sekcji do oryginalnego obiektu
        instructor['extracted_preferences'] = extracted
        
        # Szanujemy limity (max 60/h -> 1 na minutę, ale tu damy mały odstęp)
        time.sleep(1) 

    # 4. Zapisanie gotowego pliku dla reszty zespołu
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\nSukces! Dane zapisano w pliku: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
