# modules/modul1_parser.py

class Prowadzacy:
    __slots__ = ['id', 'imie_nazwisko', 'kompetencje', 'preferowane_dni', 'zakazane_sloty', 'limit_slotow_tydzien']
    def __init__(self, dane_json):
        self.id = dane_json['id']
        self.imie_nazwisko = dane_json['name']
        self.kompetencje = set(dane_json['subjects']) 
        self.limit_slotow_tydzien = int(dane_json['hours_per_semester'] / 15)
        prefs = dane_json.get('parsed_preferences', {})
        self.preferowane_dni = set(prefs.get('preferred_days', []))
        self.zakazane_sloty = set()
        for zakaz in prefs.get('forbidden_slots', []):
            dzien = zakaz['day']
            for godzina in range(zakaz['from'], zakaz['to']):
                self.zakazane_sloty.add((dzien, godzina))

class Sala:
    __slots__ = ['id', 'typ', 'pojemnosc', 'dostepnosc']
    def __init__(self, dane_json):
        self.id = dane_json['id']
        self.typ = dane_json['type']
        self.pojemnosc = dane_json['capacity']
        self.dostepnosc = set()
        for dzien, godziny in dane_json.get('availability', {}).items():
            for godzina in godziny:
                self.dostepnosc.add((dzien, godzina))

class Przedmiot:
    __slots__ = ['id', 'nazwa', 'typ', 'liczba_studentow', 'wymagane_godziny', 'wymagany_typ_sali']
    def __init__(self, dane_json):
        self.id = dane_json['id']
        self.nazwa = dane_json['name']
        self.typ = dane_json['type']
        self.liczba_studentow = dane_json['students']
        self.wymagane_godziny = dane_json['hours_per_week']
        self.wymagany_typ_sali = dane_json['required_room_type']

class Zajecia:
    __slots__ = ['id', 'przedmiot_id', 'baza_przedmiotu', 'grupa_id', 'liczba_studentow', 
                 'wymagany_typ_sali', 'wymagane_godziny', 'prowadzacy_id', 
                 'przypisany_dzien', 'przypisany_start_slot', 'przypisana_sala_id']
    def __init__(self, przedmiot, id_zajec):
        self.id = id_zajec
        self.przedmiot_id = przedmiot.id
        self.liczba_studentow = przedmiot.liczba_studentow
        self.wymagany_typ_sali = przedmiot.wymagany_typ_sali
        self.wymagane_godziny = przedmiot.wymagane_godziny
        self.baza_przedmiotu = przedmiot.id.rsplit('-', 1)[0]
        self.grupa_id = przedmiot.id 
        self.prowadzacy_id = None 
        self.przypisany_dzien = None
        self.przypisany_start_slot = None
        self.przypisana_sala_id = None

def zbuduj_baze_obiektow(dane_json):
    return (
        {p['id']: Prowadzacy(p) for p in dane_json.get('instructors', [])},
        {s['id']: Sala(s) for s in dane_json.get('rooms', [])},
        {c['id']: Przedmiot(c) for c in dane_json.get('courses', [])}
    )

