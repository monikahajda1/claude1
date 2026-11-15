from django.conf import settings



def uprawnienia(request):  # noqa: F811 – nazwa używana w ustawieniach
    from apps.konta import uprawnienia as u

    user = request.user
    if not user.is_authenticated:
        return {"NAZWA_APLIKACJI": settings.NAZWA_APLIKACJI}
    return {
        "NAZWA_APLIKACJI": settings.NAZWA_APLIKACJI,
        "moje_role": sorted(u.role(user)),
        "widzi": {m: u.moze_widziec(user, m) for m in u.MACIERZ},
        "edytuje": {m: u.moze_edytowac(user, m) for m in u.MACIERZ},
        "jest_adminem": u.jest_adminem(user),
    }
