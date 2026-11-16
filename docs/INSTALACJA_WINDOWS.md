# Instalacja i uruchomienie na Windowsie – krok po kroku

Ta instrukcja prowadzi od zera do działającej aplikacji na komputerze w biurze.
Za pierwszym razem zajmie to ok. 30–60 minut (głównie czekanie na pobieranie).

> **Słowniczek**
> - **Docker** – program, który uruchamia aplikację i bazę danych w odizolowanych „pudełkach” (kontenerach).
>   Dzięki temu nie trzeba ręcznie instalować Pythona ani PostgreSQL.
> - **Git** – program, który pobiera kod aplikacji i pamięta historię każdej zmiany (można cofnąć).
> - **Skrypt .bat** – plik, który uruchamiasz dwuklikiem; wykonuje za Ciebie polecenia.

---

## Krok 0. Sprawdź komputer

- Windows 10 (wersja 22H2) lub Windows 11, Home albo Pro.
- Co najmniej 8 GB RAM (lepiej 16 GB) i ok. 15 GB wolnego miejsca na dysku.
- Konto z **uprawnieniami administratora** (instalacja programów wymaga zgody administratora).

## Krok 1. Zainstaluj Git

1. Wejdź na stronę **https://git-scm.com/download/win** – pobieranie zacznie się samo.
2. Uruchom pobrany plik `Git-....exe`.
3. Klikaj **Next** – domyślne ustawienia są dobre. Na końcu **Install**, potem **Finish**.

## Krok 1a. Włącz WSL (podsystem Linux – potrzebny Dockerowi)

1. Kliknij **Start**, wpisz `PowerShell`.
2. Na wyniku **Windows PowerShell** kliknij **prawym** przyciskiem → **Uruchom jako administrator** → **Tak**.
3. W niebieskim oknie wpisz (lub wklej prawym przyciskiem myszy) i naciśnij Enter:
   ```
   wsl --install --no-distribution
   ```
   Jeśli zamiast instalacji pojawi się długa lista opcji (starszy Windows), wpisz samo `wsl --install`.
4. Poczekaj na komunikat o zakończeniu i **uruchom ponownie komputer**.
5. Jeśli po restarcie otworzy się okno „Ubuntu” z prośbą o nazwę użytkownika – możesz je po prostu zamknąć
   (aplikacja go nie potrzebuje).

## Krok 2. Zainstaluj Docker Desktop

1. Wejdź na **https://www.docker.com/products/docker-desktop/** i kliknij
   **Download for Windows** (zwykle wersja „AMD64”).
2. Uruchom pobrany plik `Docker Desktop Installer.exe`.
3. Zostaw zaznaczoną opcję **Use WSL 2 instead of Hyper-V** i kliknij **OK**.
4. Po instalacji **uruchom ponownie komputer**, jeśli instalator o to poprosi.
5. Uruchom **Docker Desktop** (ikonka wieloryba w menu Start).
   - Zaakceptuj warunki licencji. Docker Desktop jest bezpłatny dla firm, które mają
     **mniej niż 250 pracowników i mniej niż 10 mln USD rocznego przychodu**. Większe firmy potrzebują płatnej subskrypcji.
   - Logowanie do konta Docker możesz pominąć (**Skip**).
6. Poczekaj, aż w lewym dolnym rogu okna Dockera pojawi się zielony napis **Engine running**.
7. (Zalecane) W Docker Desktop: **Settings → General → zaznacz „Start Docker Desktop when you sign in”**.
   Dzięki temu aplikacja sama wystartuje po włączeniu komputera.

> Jeśli Docker pokaże błąd o **WSL**: kliknij Start, wpisz `PowerShell`, kliknij prawym przyciskiem
> **Uruchom jako administrator**, wpisz `wsl --update`, naciśnij Enter, a po zakończeniu uruchom ponownie komputer.

## Krok 3. Pobierz aplikację

1. Kliknij Start, wpisz **cmd** i otwórz **Wiersz polecenia**.
2. Wpisz (lub wklej prawym przyciskiem myszy) i naciśnij Enter:

   ```
   git clone -b claude/sweet-meitner-uz15iq https://github.com/monikahajda1/claude1.git C:\Posadzki
   ```

3. Za pierwszym razem otworzy się okno logowania do GitHuba – zaloguj się (repozytorium jest prywatne).
4. Aplikacja jest teraz w folderze **C:\Posadzki**.

## Krok 4. Uruchom aplikację

1. Otwórz w Eksploratorze plików folder **C:\Posadzki**.
2. Kliknij dwukrotnie **start.bat**.
   - Jeśli Windows pokaże „System Windows ochronił ten komputer”: kliknij **Więcej informacji → Uruchom mimo to**.
   - Za pierwszym razem pobieranie i budowanie trwa kilka minut. Skrypt sam utworzy plik ustawień `.env`
     z losowymi, bezpiecznymi hasłami.
3. Gdy zobaczysz **Gotowe!**, przeglądarka sama otworzy **http://localhost:8000**.

## Krok 5. Załóż swoje konto administratora

1. W folderze **C:\Posadzki\skrypty** kliknij dwukrotnie **utworz-administratora.bat**.
2. Podaj login (np. `monika`), e-mail (możesz pominąć Enterem) i dwa razy hasło
   (min. 10 znaków; podczas wpisywania nic się nie wyświetla – to normalne).
3. Zaloguj się tym kontem na **http://localhost:8000**.

## Krok 6. (Do testów) Wczytaj dane przykładowe

Kliknij dwukrotnie **skrypty\dane-testowe.bat**. Wczyta się 10 wymyślonych budów, klienci, pracownicy,
sprzęt i dokumenty – część celowo przeterminowana, żeby było widać alerty.

Powstaną też konta demonstracyjne (hasło dla wszystkich: **Demo-haslo-2026**):

| Login | Rola | Co zobaczy |
|---|---|---|
| `admin_demo` | Administrator | wszystko |
| `handlowiec_demo` | Handlowiec | budowy i klientów, **bez** pracowników |
| `bhp_demo` | BHP | pracowników, sprzęt, alerty; bez klientów |
| `kierownik_demo` | Kierownik robót | tylko swoje budowy |
| `podglad_demo` | Administrator – tylko podgląd | wszystko, ale nic nie zmieni |

> **Przed wpisaniem prawdziwych danych** usuń bazę testową: **skrypty\wyczysc-baze.bat**
> (usuwa WSZYSTKO), potem **start.bat** i **skrypty\utworz-administratora.bat**.

---

## Codzienna obsługa

| Co chcesz zrobić | Co kliknąć |
|---|---|
| Uruchomić aplikację | `start.bat` |
| Zatrzymać aplikację | `stop.bat` |
| Zrobić kopię zapasową | `kopia-zapasowa.bat` → pliki w folderze `kopie` |
| Przywrócić kopię | `przywroc-kopie.bat` |
| Pobrać nową wersję aplikacji | `skrypty\aktualizuj.bat` |
| Zobaczyć komunikaty / błędy | `skrypty\logi.bat` |
| Uruchomić testy automatyczne | `skrypty\testy.bat` |

**Kopie zapasowe:** rób je regularnie (np. w piątek) i kopiuj folder `kopie` poza komputer
(dysk zewnętrzny, firmowa chmura). Kopia na tym samym dysku nie chroni przed awarią dysku.

**Konta i uprawnienia:** menu **Administracja → Użytkownicy**. Rolę nadajesz w polu **Grupy**
(Administrator / Handlowiec / BHP / Kierownik robót). Pole **tylko podgląd** blokuje edycję.
Kierownikowi przypisujesz budowy w edycji budowy (pole „kierownik robót”).

**Rodzaje dokumentów BHP** (badania, szkolenia, przeglądy): **Administracja → Typy dokumentów**.
Możesz dodać nowe, oznaczyć jako „wymagany zawsze” i ustawić typowy okres ważności.

**Cennik:** menu **Więcej → Cennik**. Wpisz swoje prawdziwe ceny dopiero po usunięciu danych testowych.
Pole „koszt własny” jest opcjonalne – służy tylko do liczenia marży, nigdy nie trafia do oferty dla klienta.

**Własny szablon oferty (Word):** menu **Więcej → Szablon oferty (Word)** – tam jest instrukcja krok po kroku,
wzór do pobrania i lista wszystkich pól.

---

## Na przyszłość: dostęp z telefonu na budowie (Tailscale) – NIE rób tego teraz

Aplikacja jest na to przygotowana. Gdy przyjdzie czas, zrobimy to razem:

1. Zainstaluj **Tailscale** na komputerze w biurze i na telefonie, zaloguj się tym samym kontem.
2. Na komputerze w biurze polecenie `tailscale serve --bg 8000` udostępni aplikację pod adresem
   w rodzaju `https://biuro-pc.nazwa.ts.net` – **tylko** urządzeniom w Twojej sieci Tailscale.
3. W pliku `.env` dopiszesz ten adres:
   ```
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,biuro-pc.nazwa.ts.net
   DJANGO_CSRF_TRUSTED_ORIGINS=https://biuro-pc.nazwa.ts.net
   DJANGO_HTTPS=True
   ```
   i uruchomisz ponownie `start.bat`.
4. Na telefonie otworzysz ten adres i wybierzesz **„Dodaj do ekranu głównego”** – pojawi się ikonka aplikacji.

Komputer w biurze musi być wtedy włączony (i nie może usypiać).

---

## Gdy coś nie działa

| Objaw | Co zrobić |
|---|---|
| „Docker nie działa” | Uruchom Docker Desktop i poczekaj na „Engine running”. |
| Strona się nie otwiera | Uruchom `skrypty\logi.bat`, skopiuj ostatnie linie i prześlij. |
| „Port is already allocated” | Coś innego używa portu 8000. W `.env` zmień `PORT=8000` na `PORT=8080` i otwieraj `http://localhost:8080`. |
| Zapomniane hasło administratora | Uruchom `skrypty\utworz-administratora.bat` i załóż nowe konto administratora. |
