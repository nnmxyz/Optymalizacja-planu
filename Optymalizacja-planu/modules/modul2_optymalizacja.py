# modules/modul2_optymalizacja.py
from modules.modul1_parser import Zajecia

class StanPlanu:
    __slots__ = ['zajetosc_sal', 'zajetosc_prowadzacych', 'zajetosc_grup']
    def __init__(self):
        self.zajetosc_sal = {}          
        self.zajetosc_prowadzacych = {} 
        self.zajetosc_grup = {}         

    def czy_ruch_jest_legalny(self, zajecia, proponowany_dzien, start_slot, sala, prowadzacy):
        if sala.pojemnosc < zajecia.liczba_studentow: return False 
        if sala.typ != zajecia.wymagany_typ_sali: return False     
        if zajecia.baza_przedmiotu not in prowadzacy.kompetencje: return False 
        for offset in range(zajecia.wymagane_godziny):
            aktualny_slot = start_slot + offset
            slot_tuple = (proponowany_dzien, aktualny_slot)
            if slot_tuple not in sala.dostepnosc: return False 
            if slot_tuple in self.zajetosc_sal.get(sala.id, set()): return False 
            if slot_tuple in self.zajetosc_prowadzacych.get(prowadzacy.id, set()): return False 
            if slot_tuple in self.zajetosc_grup.get(zajecia.grupa_id, set()): return False 
            if slot_tuple in prowadzacy.zakazane_sloty: return False 
        return True

    def wstaw_zajecia(self, zajecia, dzien, start_slot, sala, prowadzacy):
        zajecia.przypisany_dzien = dzien
        zajecia.przypisany_start_slot = start_slot
        zajecia.przypisana_sala_id = sala.id
        zajecia.prowadzacy_id = prowadzacy.id
        for offset in range(zajecia.wymagane_godziny):
            slot_tuple = (dzien, start_slot + offset)
            self.zajetosc_sal.setdefault(sala.id, set()).add(slot_tuple)
            self.zajetosc_prowadzacych.setdefault(prowadzacy.id, set()).add(slot_tuple)
            self.zajetosc_grup.setdefault(zajecia.grupa_id, set()).add(slot_tuple)

    def usun_zajecia(self, zajecia):
        dzien = zajecia.przypisany_dzien
        start_slot = zajecia.przypisany_start_slot
        if dzien is None or start_slot is None: return 
        for offset in range(zajecia.wymagane_godziny):
            slot_tuple = (dzien, start_slot + offset)
            self.zajetosc_sal[zajecia.przypisana_sala_id].remove(slot_tuple)
            self.zajetosc_prowadzacych[zajecia.prowadzacy_id].remove(slot_tuple)
            self.zajetosc_grup[zajecia.grupa_id].remove(slot_tuple)
        zajecia.przypisany_dzien = None
        zajecia.przypisany_start_slot = None
        zajecia.przypisana_sala_id = None
        zajecia.prowadzacy_id = None

class AlgorytmKonstruktywny:
    def __init__(self, stan_planu, prowadzacy_db, sale_db, przedmioty_db):
        self.stan = stan_planu
        self.prowadzacy_db = prowadzacy_db
        self.sale_db = list(sale_db.values())
        self.dni_tygodnia = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
        self.lista_zajec = []
        for przedmiot in przedmioty_db.values():
            zajecia = Zajecia(przedmiot, id_zajec=f"ZAJ_{przedmiot.id}")
            self.lista_zajec.append(zajecia)
        self.lista_zajec.sort(key=lambda z: (z.wymagane_godziny, z.liczba_studentow), reverse=True)

    def rozwiaz(self):
        return self._backtrack(0)

    def _backtrack(self, indeks_zajec):
        if indeks_zajec == len(self.lista_zajec): return True
        zajecia = self.lista_zajec[indeks_zajec]
        dostepni_prowadzacy = [p for p in self.prowadzacy_db.values() if zajecia.baza_przedmiotu in p.kompetencje]
        
        for prowadzacy in dostepni_prowadzacy:
            for sala in self.sale_db:
                if sala.typ != zajecia.wymagany_typ_sali or sala.pojemnosc < zajecia.liczba_studentow: continue 
                for dzien in self.dni_tygodnia:
                    for start_slot in range(8, 20 - zajecia.wymagane_godziny + 1):
                        if self.stan.czy_ruch_jest_legalny(zajecia, dzien, start_slot, sala, prowadzacy):
                            self.stan.wstaw_zajecia(zajecia, dzien, start_slot, sala, prowadzacy)
                            if self._backtrack(indeks_zajec + 1): return True
                            self.stan.usun_zajecia(zajecia)
        return False

