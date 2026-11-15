# CLAUDE.md – pamięć projektu dla kolejnych sesji

## O projekcie
Aplikacja webowa do prowadzenia wielu budów jednocześnie w firmie wykonującej **posadzki żywiczne** –
od oferty do dokumentacji powykonawczej. Główna zasada: **dane wpisuje się raz, program używa ich
wielokrotnie** (np. karta techniczna materiału trafia automatycznie do KZM i do dokumentacji powykonawczej).

Użytkowniczka: kierownik działu handlowego, **nie jest programistką**, pracuje na **Windowsie**.
→ Wszystko tłumacz **po polsku, prostym językiem, krok po kroku**. Interfejs aplikacji po polsku.

## Zasady współpracy (OBOWIĄZKOWE)
1. Przed pisaniem kodu: zadaj pytania, jeśli coś jest niejasne, i przedstaw krótki plan.
2. Buduj **etapami**. Po każdym etapie powiedz, jak sprawdzić w przeglądarce, że działa,
   i **poczekaj na akceptację** przed kolejnym etapem.
3. Używaj gita – każda zmiana ma dać się cofnąć. Małe, opisane commity.

## Poufność danych – BARDZO WAŻNE
- Pracujemy **wyłącznie na fikcyjnych danych testowych** (komenda `dane_testowe`).
- **Nigdy nie proś o prawdziwe dane klientów ani pracowników.** Prawdziwe dane użytkowniczka wpisze sama.
- Szablony dokumentów dostajemy zanonimizowane (z polami typu `{{klient}}`).
- Nazwy w danych testowych nie mogą przypominać prawdziwych firm/marek.
- Hasła i ustawienia tylko w `.env` (nie trafia do gita). Przesłane pliki (skany badań itp.)
  NIE są publiczne – wydaje je widok `pobierz_plik` po sprawdzeniu uprawnień.

## Technologia
- Django 5.2 LTS (Python 3.13) + PostgreSQL 16, Docker Compose (`db` + `web`), gunicorn + whitenoise.
- Ustawienia ze zmiennych środowiskowych / `.env` (django-environ) → łatwe przeniesienie do chmury.
- Bootstrap 5 lokalnie w `static/vendor` (bez CDN). Responsywny interfejs, PWA (`/manifest.webmanifest`, `/sw.js`).
  Service worker celowo NIE przechowuje danych (poufność) – tylko stronę offline.
- Dostęp z telefonu docelowo przez Tailscale do komputera w biurze (opis w `docs/INSTALACJA_WINDOWS.md`, sekcja Tailscale);
  wymaga dopisania adresu do `DJANGO_ALLOWED_HOSTS` i `DJANGO_CSRF_TRUSTED_ORIGINS` oraz `DJANGO_HTTPS=True`.
- Dokumenty Word z szablonów: **docxtpl** (pola `{{klient}}`, `{{adres_budowy}}`, `{{pracownik}}`) – od etapu ofert/IBWR/KZM.
- Dziennik zmian: django-simple-history (`history = HistoricalRecords()` w KAŻDYM nowym modelu) + middleware zapisujący autora.
  Widok: `/system/dziennik-zmian/`.

## Struktura
```
config/            ustawienia, adresy URL
apps/konta/        model Uzytkownik (AUTH_USER_MODEL), role, uprawnienia.py ← JEDYNE miejsce reguł dostępu
apps/budowy/       Klient, Budowa (etapy w Etap, numeracja B/RRRR/NNN), przypisanie ekipy i sprzętu
apps/bhp/          TypDokumentu (słownik), Pracownik, Sprzet, DokumentPracownika/Sprzetu, terminy.py, alerty.py
apps/pulpit/       ekran „Co dziś?” (zadania.py – alerty budów)
apps/core/         wspólne: mixiny uprawnień, formularze, PWA, ochrona plików, dziennik, komenda dane_testowe
templates/         szablony HTML (po polsku)
*.bat, skrypty/    skrypty dla Windows (start, stop, kopia, przywracanie, testy, dane testowe)
docs/              instrukcje dla użytkowniczki
```

## Role i uprawnienia (apps/konta/uprawnienia.py)
- Role = grupy Django: **Administrator**, **Handlowiec**, **BHP**, **Kierownik robót** (tworzone automatycznie po migracji).
- `MACIERZ` moduł → (kto widzi, kto edytuje). Pole `tylko_podglad` na koncie blokuje każdą edycję.
- Handlowiec: bez danych pracowników. BHP: bez klientów. Kierownik: tylko budowy, gdzie `kierownik = on`.
- Widoki dziedziczą po `ModulMixin` (`modul=...`, `edycja=True/False`); budowy zawsze filtruj przez `budowy_dla(user)`.
- Panel `/admin/` – zarządzanie kontami i słownikami (tylko administrator z `is_staff`).

## Alerty BHP
- Progi z `.env`: `ALERT_DNI_OSTRZEZENIE` (30), `ALERT_DNI_PILNE` (7).
- Liczy się **najnowszy** dokument danego rodzaju; wymagany (`TypDokumentu.wymagany`) a brakujący → alert „brak dokumentu”.
- Tylko aktywni pracownicy / sprzęt.

## Plan etapów
1. ✅ (do akceptacji) Instalacja, logowanie i role, lista budów z etapami, BHP (pracownicy, sprzęt, daty ważności), „Co dziś?”.
2. Oferty: kalkulator (m² × system, gruntowanie, cokoliki…), oferta z szablonu Word, statusy, follow-up (7 dni), statystyki skuteczności.
3. Umowa: wygrana oferta → budowa.
4. Wejście na budowę: IBWR i KZM z szablonów, checklista „czego brakuje” per budowa.
5. Rozliczenia miesięczne: m² w miesiącu, % zaawansowania, kwota do faktury, protokół odbioru częściowego.
6. Dokumentacja powykonawcza: jeden PDF ze spisem treści (karty techniczne, DoP, protokoły pomiarów, zdjęcia).
Pomysły na później: blokada po wielu nieudanych logowaniach (django-axes), automatyczne kopie (Harmonogram zadań Windows).

## Komendy (programista / Claude)
```
docker compose up -d --build                    # start
docker compose exec web python manage.py test   # testy (muszą przechodzić przed commitem)
docker compose exec web python manage.py makemigrations && ... migrate
docker compose exec web python manage.py dane_testowe --konta   # fikcyjne dane + konta demo (hasło Demo-haslo-2026)
```
Lokalnie bez Dockera: ustaw `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, `POSTGRES_HOST=localhost` i uruchom `python manage.py ...`.
