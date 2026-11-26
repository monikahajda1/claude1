# Mój Trening 🏃‍♀️💪

Domowa aplikacja treningowa dla początkujących – jedna strona HTML/CSS/JS, działa w przeglądarce telefonu i offline (PWA).

## Co jest w środku

- **Dziś** – trening zaplanowany na dziś, licznik serii i kolejne treningi.
- **Ćwiczenia** – 31 ćwiczeń bez sprzętu w 6 kategoriach (brzuch, pośladki, nogi, ramiona i plecy, całe ciało, rozciąganie). Każde ma animowaną sylwetkę, 3 poziomy trudności, opis krok po kroku, wskazówki i najczęstsze błędy.
- **Treningi** – 7 gotowych sesji (4–20 min) z timerem: odliczanie pracy i przerwy, sygnały dźwiękowe, głos, wibracje, pauza, podgląd następnego ćwiczenia.
- **Plan** – 8 tygodni: bieżnia w pon/śr/pt (interwały marsz + trucht aż do 20 min biegu, w środę marsz pod górę), trening siłowy we wt i sob (coraz trudniej: dłuższa praca, więcej rund, wyższy poziom, nowe ćwiczenia).
- **Dziennik** – kalendarz z zaznaczonymi treningami, seria dni z rzędu, statystyki, ręczne dodawanie wpisów, kopia zapasowa.

Dane zapisują się tylko na Twoim telefonie (localStorage).

## Pliki

| Plik | Do czego |
|---|---|
| `index.html` | cała aplikacja |
| `manifest.webmanifest` | nazwa, kolory i ikony aplikacji na ekranie głównym |
| `sw.js` | praca offline |
| `icons/` | ikony |

## Jak uruchomić na telefonie

Żeby dodać aplikację do ekranu głównego jako PWA, musi być dostępna przez **https**. Najprościej przez GitHub Pages:

1. Na GitHubie wejdź w repozytorium → **Settings** → **Pages**.
2. W „Build and deployment” wybierz **Source: Deploy from a branch**, a jako gałąź tę z aplikacją (np. `main` po scaleniu albo `claude/training-app-pwa-ulmla5`) i folder **/ (root)**. Kliknij **Save**.
3. Po 1–2 minutach strona będzie pod adresem `https://<twoja-nazwa>.github.io/claude1/`.

> Jeśli repozytorium jest prywatne, a konto darmowe, GitHub Pages może być niedostępne. Wtedy ustaw repozytorium jako publiczne albo wrzuć folder z plikami na https://app.netlify.com/drop (przeciągnij folder – dostaniesz adres https).

### Dodanie do ekranu głównego

- **iPhone (Safari):** otwórz adres → przycisk **Udostępnij** (kwadrat ze strzałką) → **Do ekranu początkowego** → **Dodaj**.
- **Android (Chrome):** otwórz adres → menu **⋮** → **Dodaj do ekranu głównego** / **Zainstaluj aplikację**.

Po pierwszym otwarciu aplikacja działa także bez internetu.

## Wskazówki

- Na iPhonie wyłącz przełącznik wyciszenia, żeby słyszeć sygnały timera.
- Datę startu planu zmienisz w zakładce **Plan** (na dole).
- Co jakiś czas zrób **kopię zapasową** w zakładce **Dziennik**.
- Po zmianach w kodzie podnieś numer wersji `CACHE` w `sw.js`, żeby telefon pobrał nową wersję.
