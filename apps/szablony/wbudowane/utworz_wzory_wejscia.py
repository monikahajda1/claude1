"""Tworzy wbudowane wzory KZM (kzm.docx) i IBWR (ibwr.docx).

Uruchomienie (programista): python apps/szablony/wbudowane/utworz_wzory_wejscia.py
Wzory można pobrać w aplikacji, przerobić w Wordzie i wgrać jako własne.
"""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor

NIEBIESKI = RGBColor(0x1F, 0x4E, 0x79)
SZARY = RGBColor(0x88, 0x88, 0x88)
KATALOG = Path(__file__).resolve().parent


def nowy_dokument():
    doc = Document()
    s = doc.sections[0]
    s.left_margin = s.right_margin = Cm(1.8)
    s.top_margin = s.bottom_margin = Cm(1.5)
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10)
    return doc


def akapit(doc, tekst="", pogrubiony=False, rozmiar=None, kolor=None, srodek=False, po=4):
    p = doc.add_paragraph()
    r = p.add_run(tekst)
    r.bold = pogrubiony
    if rozmiar:
        r.font.size = Pt(rozmiar)
    if kolor:
        r.font.color.rgb = kolor
    if srodek:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(po)
    return p


def naglowek(doc, tekst):
    akapit(doc, tekst, pogrubiony=True, rozmiar=11, kolor=NIEBIESKI, po=3)


def etykieta(doc, etyk, wartosc):
    p = doc.add_paragraph()
    p.add_run(etyk).bold = True
    p.add_run(wartosc)
    p.paragraph_format.space_after = Pt(1)


def tabela_petla(doc, naglowki, petla, pola, szerokosci):
    """Tabela: nagłówek, wiersz {%tr for %}, wiersz z polami, wiersz {%tr endfor %}."""
    t = doc.add_table(rows=4, cols=len(naglowki))
    t.style = "Table Grid"
    t.autofit = False
    for i, n in enumerate(naglowki):
        c = t.rows[0].cells[i]
        c.text = ""
        c.paragraphs[0].add_run(n).bold = True
    t.rows[1].cells[0].text = "{%tr " + petla + " %}"
    for i, p in enumerate(pola):
        t.rows[2].cells[i].text = p
    t.rows[3].cells[0].text = "{%tr endfor %}"
    for i, s in enumerate(szerokosci):
        t.columns[i].width = Cm(s)
        for w in t.rows:
            w.cells[i].width = Cm(s)
    akapit(doc, "", po=2)
    return t


def tabela_danych(doc, wiersze, szer=(5, 12)):
    t = doc.add_table(rows=len(wiersze), cols=2)
    t.style = "Table Grid"
    t.autofit = False
    for i, (a, b) in enumerate(wiersze):
        t.rows[i].cells[0].text = ""
        t.rows[i].cells[0].paragraphs[0].add_run(a).bold = True
        t.rows[i].cells[1].text = b
        t.rows[i].cells[0].width = Cm(szer[0])
        t.rows[i].cells[1].width = Cm(szer[1])
    t.columns[0].width = Cm(szer[0])
    t.columns[1].width = Cm(szer[1])
    akapit(doc, "", po=2)


def kzm():
    doc = nowy_dokument()
    akapit(doc, "[Tu wstaw logo i dane swojej firmy]", kolor=SZARY, rozmiar=9)
    akapit(doc, "KARTA ZATWIERDZENIA MATERIAŁU", pogrubiony=True, rozmiar=15, kolor=NIEBIESKI, srodek=True, po=2)
    akapit(doc, "nr {{ numer_kzm }} z dnia {{ data }}", srodek=True, po=10)
    tabela_danych(doc, [
        ("Budowa", "{{ budowa }} ({{ numer_budowy }})"),
        ("Adres", "{{ adres_budowy }}"),
        ("Zamawiający / GW", "{{ klient }}"),
        ("Kierownik robót wykonawcy", "{{ kierownik }} {{ kierownik_telefon }}"),
    ])
    naglowek(doc, "Proponowany materiał")
    tabela_danych(doc, [
        ("Nazwa materiału", "{{ material }}"),
        ("Producent", "{{ producent }}"),
        ("Rodzaj", "{{ rodzaj_materialu }}"),
        ("System posadzki", "{{ system_posadzki }}"),
        ("Zastosowanie / miejsce wbudowania", "{{ zastosowanie }}"),
    ])
    naglowek(doc, "Załączniki")
    tabela_petla(doc, ["Lp.", "Dokument"], "for z in zalaczniki", ["{{ z.lp }}", "{{ z.nazwa }}"], [1.5, 15.5])
    naglowek(doc, "Decyzja")
    akapit(doc, "☐ zatwierdzono     ☐ zatwierdzono z uwagami     ☐ odrzucono", po=6)
    akapit(doc, "Uwagi: ..............................................................................................................................", po=14)
    t = doc.add_table(rows=2, cols=3)
    for i, n in enumerate(["Wykonawca (wnioskujący)", "Kierownik budowy / GW", "Inspektor nadzoru"]):
        t.rows[0].cells[i].text = n
        t.rows[1].cells[i].text = "\n\n.................................\ndata, podpis"
    doc.save(KATALOG / "kzm.docx")


def ibwr():
    doc = nowy_dokument()
    akapit(doc, "[Tu wstaw logo i dane swojej firmy]", kolor=SZARY, rozmiar=9)
    akapit(doc, "INSTRUKCJA BEZPIECZNEGO WYKONYWANIA ROBÓT", pogrubiony=True, rozmiar=15, kolor=NIEBIESKI, srodek=True, po=2)
    akapit(doc, "(IBWR) – roboty posadzkarskie", srodek=True, po=10)
    tabela_danych(doc, [
        ("Budowa", "{{ budowa }} ({{ numer_budowy }})"),
        ("Adres", "{{ adres_budowy }}"),
        ("Zamawiający / GW", "{{ klient }}"),
        ("Termin robót", "{{ termin_od }} – {{ termin_do }}"),
        ("Kierownik robót", "{{ kierownik }}, tel. {{ kierownik_telefon }}"),
        ("Opracował(a)", "{{ opracowal }}, {{ data }}"),
    ])
    naglowek(doc, "1. Zakres robót")
    akapit(doc, "System: {{ system_posadzki }}", po=2)
    tabela_petla(doc, ["Lp.", "Zakres", "Ilość", "J.m."], "for z in zakres",
                 ["{{ z.lp }}", "{{ z.nazwa }}", "{{ z.ilosc }}", "{{ z.jednostka }}"], [1.2, 11, 2.5, 2.3])
    naglowek(doc, "2. Pracownicy")
    tabela_petla(doc, ["Lp.", "Imię i nazwisko", "Stanowisko / firma", "Badania do", "Szkolenie BHP do", "Uprawnienia"], "for p in pracownicy",
                 ["{{ p.lp }}", "{{ p.imie_nazwisko }}", "{{ p.stanowisko }}, {{ p.firma }}", "{{ p.badania_do }}", "{{ p.szkolenie_bhp_do }}", "{{ p.uprawnienia }}"],
                 [1, 3.6, 3.6, 2.3, 2.5, 4])
    naglowek(doc, "3. Sprzęt")
    tabela_petla(doc, ["Lp.", "Nazwa", "Nr", "Przeglądy"], "for s in sprzet",
                 ["{{ s.lp }}", "{{ s.nazwa }}", "{{ s.numer }}", "{{ s.przeglady }}"], [1, 5.5, 2.5, 8])
    naglowek(doc, "4. Materiały chemiczne (karty charakterystyki dostępne na budowie)")
    tabela_petla(doc, ["Lp.", "Materiał", "Producent", "Rodzaj", "Karta charakt."], "for m in materialy",
                 ["{{ m.lp }}", "{{ m.nazwa }}", "{{ m.producent }}", "{{ m.rodzaj }}", "{{ m.karta_charakterystyki }}"], [1, 5, 4.5, 4, 2.5])
    naglowek(doc, "5. Zagrożenia i środki ochrony")
    tabela_petla(doc, ["Lp.", "Zagrożenie", "Środki ochrony / sposób postępowania"], "for z in zagrozenia",
                 ["{{ z.lp }}", "{{ z.nazwa }}", "{{ z.srodki }}"], [1, 6.5, 9.5])
    naglowek(doc, "6. Postępowanie w razie wypadku lub pożaru")
    akapit(doc, "{{ procedury_awaryjne }}", po=10)
    naglowek(doc, "7. Oświadczenie – zapoznałem/am się z instrukcją")
    tabela_petla(doc, ["Lp.", "Imię i nazwisko", "Data", "Podpis"], "for p in pracownicy",
                 ["{{ p.lp }}", "{{ p.imie_nazwisko }}", "", ""], [1, 7, 3.5, 5.5])
    doc.save(KATALOG / "ibwr.docx")


if __name__ == "__main__":
    kzm()
    ibwr()
