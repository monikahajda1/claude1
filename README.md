# Posadzki – Budowy

Aplikacja do prowadzenia wielu budów posadzek żywicznych jednocześnie – od oferty do dokumentacji powykonawczej.

**Instalacja na Windowsie krok po kroku:** [docs/INSTALACJA_WINDOWS.md](docs/INSTALACJA_WINDOWS.md)

Skrót (gdy wszystko jest już zainstalowane):

1. `start.bat` – uruchamia aplikację → http://localhost:8000
2. `skrypty\utworz-administratora.bat` – pierwsze konto
3. `skrypty\dane-testowe.bat` – fikcyjne dane do wypróbowania (konta demo, hasło `Demo-haslo-2026`)

## Co już działa (etap 1)
- Logowanie, role (Administrator, Handlowiec, BHP, Kierownik robót), tryb „tylko podgląd”, dziennik zmian
- Lista budów z etapami (oferta → umowa → przygotowanie → realizacja → rozliczenie → dokumentacja → zakończona)
- Klienci
- BHP: pracownicy i sprzęt z dokumentami i datami ważności, skany/zdjęcia, przypisanie ekipy do budowy
- Ekran „Co dziś?” z alertami (wygasłe, brakujące, wygasające w ciągu 7 i 30 dni; terminy budów)
- Kopie zapasowe i przywracanie jednym kliknięciem; wygląd na telefonie; przygotowanie jako PWA

## Etap 2 – oferty
- Cennik (systemy posadzek, przygotowanie podłoża, pozycje dodatkowe) z opcjonalnym kosztem do liczenia marży
- Kalkulator ofert z wariantami, rabatem, VAT; szybkie wstawianie m²; działa na telefonie
- Oferta jako plik Word z szablonu (wbudowany wzór albo własny – Więcej → Szablon oferty)
- Statusy, wersje po negocjacjach, notatki z kontaktów, przypomnienia po 7 dniach na „Co dziś?”
- Statystyki skuteczności: miesiące, handlowcy, systemy, powody przegranych

## Etap 3 – umowy
- Przycisk „Utwórz budowę z oferty” w wygranej ofercie – dane i zakres prac przenoszą się same
- Dane umowy: numer, wartość, sposób rozliczenia (obmiar / ryczałt), gwarancja, kaucja, kary, skan PDF
- Aneksy aktualizują wartość i termin budowy
- „Co dziś?” przypomina o braku skanu, zwrocie kaucji i końcu gwarancji

## Etap 4 – wejście na budowę
- Biblioteka materiałów: karta techniczna, DoP, karta charakterystyki, atest – wgrywane raz, używane wszędzie
- Materiały budowy uzupełniają się same z zakresu prac (systemy z cennika ↔ materiały)
- KZM: jedna na materiał, statusy, karta w Wordzie + osobno paczka ZIP z dokumentami materiału
- IBWR z ekipą, sprzętem, materiałami chemicznymi i biblioteką zagrożeń (Word)
- Checklista „czego brakuje” na każdej budowie (punkty automatyczne i ręczne), dokumenty firmy (polisa OC…)
- „Co dziś?”: budowy startujące z niepełną checklistą, wygasające dokumenty firmy i materiałów

Opis techniczny projektu i zasad: [CLAUDE.md](CLAUDE.md)

Wszystkie dane w repozytorium są **fikcyjne**.
