"""Tworzy wbudowany, przykładowy szablon oferty (oferta.docx).

Uruchomienie (programista): python apps/szablony/wbudowane/utworz_wzor_oferty.py
Użytkownik może pobrać ten plik w aplikacji, przerobić w Wordzie na swój wzór i wgrać z powrotem.
"""

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor

NIEBIESKI = RGBColor(0x1F, 0x4E, 0x79)


def akapit(doc, tekst="", pogrubiony=False, rozmiar=None, wyrownanie=None, kolor=None, odstep_po=4):
    p = doc.add_paragraph()
    run = p.add_run(tekst)
    run.bold = pogrubiony
    if rozmiar:
        run.font.size = Pt(rozmiar)
    if kolor:
        run.font.color.rgb = kolor
    if wyrownanie:
        p.alignment = wyrownanie
    p.paragraph_format.space_after = Pt(odstep_po)
    return p


def etykieta(doc, etyk, wartosc):
    p = doc.add_paragraph()
    p.add_run(etyk).bold = True
    p.add_run(wartosc)
    p.paragraph_format.space_after = Pt(2)


def main():
    doc = Document()
    sekcja = doc.sections[0]
    sekcja.left_margin = sekcja.right_margin = Cm(2)
    sekcja.top_margin = sekcja.bottom_margin = Cm(1.8)
    styl = doc.styles["Normal"]
    styl.font.name = "Calibri"
    styl.font.size = Pt(10)

    akapit(doc, "[Tu wstaw logo i dane swojej firmy]", kolor=RGBColor(0x88, 0x88, 0x88), rozmiar=9)
    akapit(doc, "Testowo, {{ data }}", wyrownanie=WD_ALIGN_PARAGRAPH.RIGHT)

    etykieta(doc, "Zamawiający: ", "{{ klient }}")
    akapit(doc, "{{ klient_adres }}{% if klient_nip %}, NIP {{ klient_nip }}{% endif %}", odstep_po=2)
    akapit(doc, "{% if osoba_kontaktowa %}Do rąk: {{ osoba_kontaktowa }}{% endif %}", odstep_po=12)

    akapit(doc, "OFERTA nr {{ numer_oferty }}", pogrubiony=True, rozmiar=16, kolor=NIEBIESKI,
           wyrownanie=WD_ALIGN_PARAGRAPH.CENTER, odstep_po=12)

    etykieta(doc, "Inwestycja: ", "{{ inwestycja }}")
    etykieta(doc, "Adres: ", "{{ adres_budowy }}")
    akapit(doc, "{% if powierzchnia %}Powierzchnia: {{ powierzchnia }} m²{% endif %}", odstep_po=10)

    akapit(doc, "W odpowiedzi na zapytanie przedstawiamy ofertę wykonania posadzki żywicznej:", odstep_po=8)

    akapit(doc, "{%p for w in warianty %}")
    akapit(doc, "{{ w.nazwa }}", pogrubiony=True, rozmiar=12, kolor=NIEBIESKI, odstep_po=2)
    akapit(doc, "{{ w.opis }}", odstep_po=4)

    tabela = doc.add_table(rows=4, cols=6)
    tabela.style = "Table Grid"
    tabela.alignment = WD_TABLE_ALIGNMENT.CENTER
    naglowki = ["Lp.", "Zakres prac", "J.m.", "Ilość", "Cena netto [zł]", "Wartość netto [zł]"]
    for i, n in enumerate(naglowki):
        c = tabela.rows[0].cells[i]
        c.text = ""
        c.paragraphs[0].add_run(n).bold = True
    tabela.rows[1].cells[0].text = "{%tr for p in w.pozycje %}"
    dane = ["{{ p.lp }}", "{{ p.nazwa }}", "{{ p.jednostka }}", "{{ p.ilosc }}", "{{ p.cena }}", "{{ p.wartosc }}"]
    for i, t in enumerate(dane):
        komorka = tabela.rows[2].cells[i]
        komorka.text = t
        if i >= 3:
            komorka.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    opis = tabela.rows[2].cells[1].add_paragraph()
    r = opis.add_run("{{ p.opis }}")
    r.font.size = Pt(8)
    r.italic = True
    tabela.rows[3].cells[0].text = "{%tr endfor %}"
    szer = [Cm(1), Cm(7.5), Cm(1.3), Cm(1.8), Cm(2.4), Cm(2.8)]
    tabela.autofit = False
    for i, s in enumerate(szer):
        tabela.columns[i].width = s
    for wiersz in tabela.rows:
        for i, s in enumerate(szer):
            wiersz.cells[i].width = s

    akapit(doc, "", odstep_po=2)
    akapit(doc, "{% if jest_rabat %}Suma przed rabatem: {{ w.suma_przed_rabatem }} zł, rabat {{ rabat_procent }}%: -{{ w.rabat }} zł{% endif %}",
           wyrownanie=WD_ALIGN_PARAGRAPH.RIGHT, odstep_po=2)
    akapit(doc, "Razem netto: {{ w.netto }} zł", pogrubiony=True, wyrownanie=WD_ALIGN_PARAGRAPH.RIGHT, odstep_po=2)
    akapit(doc, "VAT {{ vat_procent }}%: {{ w.vat }} zł", wyrownanie=WD_ALIGN_PARAGRAPH.RIGHT, odstep_po=2)
    akapit(doc, "Razem brutto: {{ w.brutto }} zł", pogrubiony=True, wyrownanie=WD_ALIGN_PARAGRAPH.RIGHT, odstep_po=2)
    akapit(doc, "(słownie brutto: {{ w.brutto_slownie }})", wyrownanie=WD_ALIGN_PARAGRAPH.RIGHT, rozmiar=8, odstep_po=12)
    akapit(doc, "{%p endfor %}")

    akapit(doc, "Warunki", pogrubiony=True, rozmiar=12, kolor=NIEBIESKI, odstep_po=4)
    etykieta(doc, "Termin realizacji: ", "{{ termin_realizacji }}")
    etykieta(doc, "Warunki płatności: ", "{{ warunki_platnosci }}")
    etykieta(doc, "Ważność oferty: ", "{{ waznosc_dni }} dni (do {{ wazna_do }})")
    akapit(doc, "{% if uwagi %}Uwagi: {{ uwagi }}{% endif %}", odstep_po=16)

    akapit(doc, "Z poważaniem", wyrownanie=WD_ALIGN_PARAGRAPH.RIGHT, odstep_po=2)
    akapit(doc, "{{ handlowiec }}", pogrubiony=True, wyrownanie=WD_ALIGN_PARAGRAPH.RIGHT, odstep_po=2)
    akapit(doc, "{{ handlowiec_telefon }} {{ handlowiec_email }}", wyrownanie=WD_ALIGN_PARAGRAPH.RIGHT, rozmiar=9)

    doc.save(Path(__file__).resolve().parent / "oferta.docx")


if __name__ == "__main__":
    main()
