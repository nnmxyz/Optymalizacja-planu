import math
import random
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
        # Heurystyka: Najdłuższe i największe zajęcia wstawiane jako pierwsze
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


class AlgorytmWyzarzania:
    """Moduł optymalizujący ograniczenia miękkie (SC) z wykorzystaniem Symulowanego Wyżarzania."""
    
    def __init__(self, stan_planu, lista_zajec, prowadzacy_db, sale_db):
        self.stan = stan_planu
        self.lista_zajec = lista_zajec
        self.prowadzacy_db = prowadzacy_db
        self.sale_db = sale_db
        self.dni_tygodnia = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
        
        # Wagi Funkcji Celu (Kalkulatora Kar)
        self.WAGA_OKIENKO = 50
        self.WAGA_ZLY_DZIEN = 150

    def oblicz_koszt(self):
        """Ocenia jakość planu (im mniej punktów, tym lepszy plan)."""
        koszt = 0
        harmonogram_prow = {} # Struktura: prowadzacy_id -> dzien -> lista zajętych godzin
        
        for zajecia in self.lista_zajec:
            prowadzacy = self.prowadzacy_db[zajecia.prowadzacy_id]
            
            # KRYTERIUM 1: Złamanie preferowanego dnia od modelu LLM
            if prowadzacy.preferowane_dni and zajecia.przypisany_dzien not in prowadzacy.preferowane_dni:
                koszt += self.WAGA_ZLY_DZIEN
                
            # Zbieramy godziny do policzenia okienek
            godziny = range(zajecia.przypisany_start_slot, zajecia.przypisany_start_slot + zajecia.wymagane_godziny)
            harmonogram_prow.setdefault(zajecia.prowadzacy_id, {}).setdefault(zajecia.przypisany_dzien, []).extend(godziny)
            
        # KRYTERIUM 2: Liczenie okienek dla kadry naukowej
        for p_id, dni in harmonogram_prow.items():
            for dzien, sloty in dni.items():
                if len(sloty) > 1:
                    max_slot = max(sloty)
                    min_slot = min(sloty)
                    rozpietosc = max_slot - min_slot + 1
                    okienka = rozpietosc - len(sloty)
                    if okienka > 0:
                        koszt += okienka * self.WAGA_OKIENKO
                        
        return koszt

    def optymalizuj(self, temp_pocz=1000.0, temp_konc=1.0, alfa=0.98, iter_na_temp=200):
        """Główna pętla Symulowanego Wyżarzania ulepszająca plan 'w miejscu'."""
        print(f"   -> Start SA: Temp={temp_pocz}, Alfa={alfa}, Iter={iter_na_temp}")
        aktualny_koszt = self.oblicz_koszt()
        najlepszy_koszt = aktualny_koszt
        
        temp = temp_pocz
        historia_kosztow = [] # Do wykresów w Streamlicie
        
        while temp > temp_konc:
            for _ in range(iter_na_temp):
                # 1. MUTACJA: Wybieramy losowe zajęcia do przeniesienia
                zajecia = random.choice(self.lista_zajec)
                
                # Zabezpieczamy obecny stan (do ewentualnego Undo)
                stary_dzien = zajecia.przypisany_dzien
                stary_slot = zajecia.przypisany_start_slot
                stary_sala_id = zajecia.przypisana_sala_id
                stary_prowadzacy_id = zajecia.prowadzacy_id
                stara_sala = next(s for s in self.sale_db if s.id == stary_sala_id)
                prowadzacy = self.prowadzacy_db[stary_prowadzacy_id]
                
                # Usuwamy fizycznie zajęcia z siatki
                self.stan.usun_zajecia(zajecia)
                
                znaleziono_miejsce = False
                # Szybkie szukanie sąsiedztwa: próbujemy 15 losowych miejsc
                for _ in range(15):
                    nowy_dzien = random.choice(self.dni_tygodnia)
                    nowy_slot = random.randint(8, 20 - zajecia.wymagane_godziny)
                    nowa_sala = random.choice(self.sale_db)
                    
                    if self.stan.czy_ruch_jest_legalny(zajecia, nowy_dzien, nowy_slot, nowa_sala, prowadzacy):
                        self.stan.wstaw_zajecia(zajecia, nowy_dzien, nowy_slot, nowa_sala, prowadzacy)
                        znaleziono_miejsce = True
                        break
                        
                if not znaleziono_miejsce:
                    # RUCH ODRZUCONY: Brak alternatywnego miejsca (UNDO)
                    self.stan.wstaw_zajecia(zajecia, stary_dzien, stary_slot, stara_sala, prowadzacy)
                    continue
                    
                # 2. EWALUACJA NOWEGO STANU
                nowy_koszt = self.oblicz_koszt()
                delta = nowy_koszt - aktualny_koszt
                
                # 3. KRYTERIUM AKCEPTACJI METROPOLISA
                if delta < 0 or random.random() < math.exp(-delta / temp):
                    # RUCH ZAAKCEPTOWANY (Zostawiamy zajęcia w nowym miejscu)
                    aktualny_koszt = nowy_koszt
                    if aktualny_koszt < najlepszy_koszt:
                        najlepszy_koszt = aktualny_koszt
                else:
                    # RUCH ODRZUCONY (Funkcja celu zbyt słaba i pech w losowaniu) -> UNDO
                    self.stan.usun_zajecia(zajecia)
                    self.stan.wstaw_zajecia(zajecia, stary_dzien, stary_slot, stara_sala, prowadzacy)
            
            # Chłodzenie systemu
            historia_kosztow.append(aktualny_koszt)
            temp *= alfa 
            
        print(f"   -> Koniec SA. Ostateczny koszt planu: {najlepszy_koszt} pkt. karnych.")
        return historia_kosztow
