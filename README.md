# Lista zadań

Prosta aplikacja webowa do zapisywania zadań do wykonania z podziałem na kategorie.

## Uruchomienie

Otwórz plik `index.html` w przeglądarce — nie wymaga instalacji ani serwera.
Dane zapisywane są lokalnie w przeglądarce (`localStorage`).

## Funkcje

- **Kategorie** — dodawanie (z wyborem koloru), zmiana nazwy (dwuklik), usuwanie.
  Na start dostępne są: Dom, Praca, Zakupy.
- **Zadania** — tytuł, kategoria, priorytet (niski / średni / wysoki) i opcjonalny termin.
- Oznaczanie zadań jako zrobione, edycja tytułu, usuwanie.
- Filtrowanie po kategorii i statusie (wszystkie / do zrobienia / zrobione) oraz wyszukiwanie.
- Licznik otwartych zadań przy każdej kategorii, wyróżnienie zadań po terminie.
- Jasny i ciemny motyw (zgodnie z ustawieniami systemu), widok mobilny.

## Pliki

- `index.html` — struktura strony
- `style.css` — wygląd
- `app.js` — logika aplikacji
