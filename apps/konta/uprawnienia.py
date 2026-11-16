"""
Uprawnienia – JEDNO miejsce, w którym ustalamy, kto co może.

Role (grupy):
  - Administrator    – wszystko + nadawanie uprawnień (panel /admin/)
  - Handlowiec       – oferty, klienci, budowy; BEZ danych pracowników
  - BHP              – pracownicy, sprzęt, dokumenty (później IBWR, KZM)
  - Kierownik robót  – tylko budowy, do których jest przypisany

Dodatkowo każde konto może mieć zaznaczone „tylko podgląd” – wtedy
niezależnie od roli nic nie zmieni.

Aby zmienić zasady, wystarczy poprawić słownik MACIERZ poniżej.
"""

ADMINISTRATOR = "Administrator"
HANDLOWIEC = "Handlowiec"
BHP = "BHP"
KIEROWNIK = "Kierownik robót"

ROLE = [ADMINISTRATOR, HANDLOWIEC, BHP, KIEROWNIK]

# moduł -> (role, które widzą, role, które mogą edytować)
MACIERZ = {
    "budowy": ({ADMINISTRATOR, HANDLOWIEC, BHP, KIEROWNIK}, {ADMINISTRATOR, HANDLOWIEC, KIEROWNIK}),
    "klienci": ({ADMINISTRATOR, HANDLOWIEC}, {ADMINISTRATOR, HANDLOWIEC}),
    "bhp": ({ADMINISTRATOR, BHP}, {ADMINISTRATOR, BHP}),
    "oferty": ({ADMINISTRATOR, HANDLOWIEC}, {ADMINISTRATOR, HANDLOWIEC}),
    # Umowy, zakres prac z cenami, aneksy. Kierownik – podgląd tylko swoich budów (filtr budowy_dla).
    "umowy": ({ADMINISTRATOR, HANDLOWIEC, KIEROWNIK}, {ADMINISTRATOR, HANDLOWIEC}),
    # Cennik widzą handlowcy (do kalkulacji), zmienia go administrator.
    "cennik": ({ADMINISTRATOR, HANDLOWIEC}, {ADMINISTRATOR}),
    # Etap 4 – wejście na budowę. Kierownik zawsze tylko swoje budowy (filtr budowy_dla).
    "materialy": ({ADMINISTRATOR, HANDLOWIEC, BHP, KIEROWNIK}, {ADMINISTRATOR}),
    "kzm": ({ADMINISTRATOR, HANDLOWIEC, BHP, KIEROWNIK}, {ADMINISTRATOR, KIEROWNIK}),
    "ibwr": ({ADMINISTRATOR, BHP, KIEROWNIK}, {ADMINISTRATOR, BHP}),
    "checklista": ({ADMINISTRATOR, HANDLOWIEC, BHP, KIEROWNIK}, {ADMINISTRATOR, BHP, KIEROWNIK}),
    "firma": ({ADMINISTRATOR, HANDLOWIEC, BHP}, {ADMINISTRATOR, BHP}),
    "statystyki": ({ADMINISTRATOR, HANDLOWIEC}, set()),
    # Szablony dokumentów Word, ustawienia systemowe.
    "ustawienia": ({ADMINISTRATOR}, {ADMINISTRATOR}),
    "dziennik": ({ADMINISTRATOR}, set()),
}

# Role, które widzą WSZYSTKIE budowy. Pozostali (kierownik) – tylko swoje.
WIDZA_WSZYSTKIE_BUDOWY = {ADMINISTRATOR, HANDLOWIEC, BHP}


def role(user):
    """Zwraca zbiór nazw ról użytkownika (z pamięcią podręczną na czas żądania)."""
    if not user or not user.is_authenticated:
        return set()
    if not hasattr(user, "_role_cache"):
        nazwy = set(user.groups.values_list("name", flat=True))
        if user.is_superuser:
            nazwy.add(ADMINISTRATOR)
        user._role_cache = nazwy
    return user._role_cache


def jest_adminem(user):
    return ADMINISTRATOR in role(user)


def moze_widziec(user, modul):
    widza, _ = MACIERZ[modul]
    return bool(role(user) & widza)


def moze_edytowac(user, modul):
    if not user.is_authenticated or getattr(user, "tylko_podglad", False):
        return False
    _, edytuja = MACIERZ[modul]
    return bool(role(user) & edytuja)


def budowy_dla(user, queryset=None):
    """Budowy, które użytkownik może zobaczyć."""
    from apps.budowy.models import Budowa

    qs = queryset if queryset is not None else Budowa.objects.all()
    r = role(user)
    if r & WIDZA_WSZYSTKIE_BUDOWY:
        return qs
    if KIEROWNIK in r:
        return qs.filter(kierownik=user)
    return qs.none()


def moze_edytowac_budowe(user, budowa):
    if not moze_edytowac(user, "budowy"):
        return False
    r = role(user)
    if r & {ADMINISTRATOR, HANDLOWIEC}:
        return True
    return budowa.kierownik_id == user.pk
