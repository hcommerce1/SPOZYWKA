# Skill: oliwa-allegro

Wystawiasz premium oliwy i spożywkę na Allegro (konto "Polska Spiżarnia").
Ten skill przeprowadza Cię przez cały proces: od surowych zdjęć do gotowego produktu w BaseLinker.

Zasada: **zawsze test na 1 produkcie, weryfikacja, potem reszta wariantów.**

---

## FAZA 0 — Wybór sesji + pełny wywiad

Pobierz listę sesji:
```
GET /mcp/sessions
```
Pokaż listę — użytkownik wybiera sesję (UUID) z którą pracujemy.

**Warianty pojemności razem** — jeśli produkt ma kilka wariantów (np. 500ml / 750ml / 1L), pytaj o wszystkie naraz. Hook/grafiki/opis generujemy 1 raz dla marki.

Przeprowadź pełny wywiad. NIE przechodź dalej bez kompletnych odpowiedzi:

```
PRODUKT:
1.  Marka i nazwa produktu?
2.  Pojemności / warianty? (podaj wszystkie naraz)
3.  Cena każdego wariantu? (PLN brutto)
4.  Dostępna ilość każdego wariantu?
5.  EAN każdego wariantu? (jeśli znany)

SZCZEGÓŁY PRODUKTU:
6.  Odmiana oliwki / surowca?
7.  Metoda produkcji? (cold press, first press, temperatura tłoczenia)
8.  Kwasowość lub inne parametry jakości?
9.  Zbiór ręczny czy mechaniczny?
10. Rok zbiorów / kampania?
11. Certyfikaty? (BIO EU, PDO, PGI, Demeter, inne)
12. Filtrowana / niefiltrowana?

PRODUCENT:
13. Nazwa producenta i kraj?
14. Importer / dystrybutor w Polsce? (pełne dane do etykiety)
15. Historia producenta w 2-3 zdaniach?
16. Czy jest logo lub zdjęcie producenta na etykiecie butelki?

ETYKIETA — OBOWIĄZKOWE NA KAŻDEJ PARTII:
17. Data produkcji konkretnej partii? (DD.MM.RRRR)
18. Numer partii (LOT)? (np. PL-2025-04-001)
19. Termin "Należy spożyć przed" (BBD)? (DD.MM.RRRR)
20. Warunki przechowywania? (np. chłodne, ciemne miejsce)

ALLEGRO:
21. Nowy produkt czy aktualizacja istniejącego?
22. Czy będzie parent dla wariantów pojemnościowych?
23. Jakie słowa kluczowe klienci wpisują szukając tego produktu?
24. Główna przewaga vs konkurencja na Allegro?
```

---

## FAZA 0.1 — Aktywny research Claude

Zrób WebSearch i przygotuj propozycję do akceptacji przez użytkownika.
**Nie generuj żadnych grafik przed akceptacją.**

### A) Research regionu i producenta
- Dokładna lokalizacja (region, dolina, wysokość n.p.m., morze)
- Co wyróżnia ten region vs inne (mikroklima, gleba, tradycja)
- Historia i wiek upraw / producenta
- Certyfikaty faktycznie przysługujące (PDO, PGI, BIO EU, UNESCO, Demeter)
- Ciekawostki i detale do storytellingu

### B) Visual brief — unikatowy per producent (nie per partię)
Brief przypisany do **producenta** — Plakias zawsze wygląda jak Plakias.
Przy kolejnych partiach tego samego producenta reużywamy.

```
PROPOZYCJA KLIMATU [nazwa producenta]:
- Paleta kolorów: ...
- Pora dnia / światło: ...
- Elementy sceny: ...
- Nastrój i styl: ...
- UNIKAĆ: ...
```

### C) Hook — 5 wariantów, głos marki producenta
Hook jest unikatowy per producent. Plakias brzmi jak Plakias, Sechii jak Sechii.
Użytkownik wybiera 1 → zapamiętaj, reużywaj przy kolejnych partiach tego producenta.

```
A: "..."
B: "..."
C: "..."
D: "..."
E: "..."
```

### D) Gotowe prompty do grafik (precyzyjne, gotowe do wklejenia)

```
FAL.AI — AI scene (gaj/uprawa/region):
"[szczegółowy prompt: lokalizacja, pora, elementy, styl fotograficzny, hiperrealistyczny, cinematic, f/2.8, 8K]"

PHOTOROOM lifestyle 1 — region/natura:
background.prompt="[...]"

PHOTOROOM lifestyle 2 — kuchnia:
background.prompt="[...]"

PHOTOROOM lifestyle 3 — stół/okazja:
background.prompt="[...]"

PHOTOROOM klimatyczna — charakter produktu (evergreen):
background.prompt="[...]"
```

Użytkownik akceptuje lub modyfikuje → dopiero po akceptacji idź do FAZY 1.

---

## FAZA 1 — Grafiki (Photoroom + Fal.ai + PIL)

Pobierz surowe zdjęcia:
```
GET /mcp/session/{id}/photos
```

Uruchom skrypt: `python scripts/generate_graphics.py --session {id}`

**Kolejność w galerii Allegro — miniaturka ZAWSZE PIERWSZA (klucz "0" w BL):**

| Klucz BL | Poz. | Grafika | Tool |
|---|---|---------|------|
| "0" | **1 — PIERWSZA** | **Miniaturka z ikonami certyfikatów** | Photoroom → PIL |
| "1" | 2 | Hero shot — inne ujęcie | Photoroom |
| "2" | 3 | Lifestyle — region/natura | Photoroom |
| "3" | 4 | Lifestyle — kuchnia | Photoroom |
| "4" | 5 | Lifestyle — stół/okazja | Photoroom |
| "5" | 6 | AI scene (gaj/uprawa) | Fal.ai Flux 1.1 Pro |
| "6" | 7 | Etykieta upscale | Photoroom |
| "7" | 8 | Klimatyczna — charakter produktu | Photoroom |
| "8" | 9 — OSTATNIA | Premium separator (złota linia) | Wygenerowany |

**Miniaturka (klucz "0") — szczegóły:**
- Photoroom: białe tło 2000×2000px, `shadow.mode=ai.soft`, `lighting.mode=ai.auto`
- PIL: ikony certyfikatów nakładane w prawym dolnym rogu, min. 180×180px każda
- Ikony muszą być widoczne z listingu Allegro (thumbnail ~200px) — nie mniejsze
- Format ikon: PNG z transparentnym tłem; źródło: oficjalne SVG UE

**Storage — WhiteSky Object Storage:**
```
spozywka/{session_uuid}/raw/        ← oryginały z apki
spozywka/{session_uuid}/processed/  ← 9 gotowych grafik (publiczne HTTPS URL)
```
Publiczny HTTPS URL z WhiteSky → wysyłany do BaseLinker.
BL pobiera obraz i hostuje własną kopię — to normalne i oczekiwane.

**Po wygenerowaniu:** pokaż wszystkie 9 grafik użytkownikowi do akceptacji zanim przejdziesz dalej.

---

## FAZA 2 — Tytuł (max 75 znaków Allegro)

Format: `[MARKA] [CERTYFIKAT] [PRODUKT] [REGION] [POJEMNOŚĆ]`

Przykład: `Plakias BIO Oliwa Extra Virgin Cold Press Kreta 500ml`

Wygeneruj 3 warianty → użytkownik wybiera 1.

---

## FAZA 3 — Opis HTML premium

**Zasady layoutu (ALLEGRO-SAFE):**
- Logo producenta po lewej + nazwa produktu po prawej (nagłówek)
- Każda sekcja: `<img>` po lewej (`align="left"`) + tekst po prawej
- Separator `<img>` (złota linia 1500×4px) między każdą sekcją
- NIE używaj `<table>` — Allegro blokuje; tabele jako grafika PNG (`<img>`)
- Logo producenta opcjonalnie na dole

**Struktura:**
1. Nagłówek (logo producenta lewo + nazwa prawo)
2. Hook (wybrany w FAZIE 0.1)
3. Separator
4. Storytelling miejsca + mapa regionu jako `<img>`
5. Separator
6. Cechy: certyfikaty jako `<img>`, odmiana, kwasowość, cold press
7. Separator
8. Timeline zbioru/tłoczenia jako `<img>` (infografika)
9. Separator
10. Korzyści zdrowotne (lista)
11. Separator
12. Tabela wartości odżywczych jako `<img>` (nie `<table>`)
13. Separator
14. Zastosowanie kulinarne — szczegółowo:
    - Na zimno: sałatki, pieczywo, tatar, carpaccio, hummus
    - Na ciepło: smażenie, sosy, marynaty
    - Desery: ciasta, lody, czekolada
15. Separator
16. Porównanie z "oliwą z supermarketu" jako `<img>`
17. Certyfikaty i gwarancje (świeżość, zakręcona, polska dostawa)
18. Logo producenta (opcjonalne)

Generuje Claude → zatwierdza użytkownik → dopiero FAZA 4.

---

## FAZA 4 — Parametry Allegro

```bash
node parametry/allegro.mjs suggest "oliwa z oliwek extra virgin"
node parametry/allegro.mjs parameters <categoryId>
```

Kluczowe parametry dla oliwy:
- Typ, Kraj pochodzenia, Pojemność (ml), Marka
- Certyfikat (BIO, PDO, PGI), Odmiana, Kwasowość
- Stan (Nowy), EAN (GTIN-13)

Przedstaw kompletny zestaw parametrów → użytkownik weryfikuje.

---

## FAZA 5 — BaseLinker (inventory Spożywka 99954)

### ZASADY — CZYTAJ DOKŁADNIE, NIE POMIJAJ

**Format zdjęć — JEDYNA poprawna forma:**
```python
images = {
    "0": "url:https://...",   # miniaturka — ZAWSZE PIERWSZA
    "1": "url:https://...",
    "2": "url:https://...",
    # ...do "8"
}
```
- Klucze: string od "0", kolejno
- Prefix `url:` — WYMAGANY, bez niego BL zwróci ERROR_INVALID_DATA
- Tylko HTTPS (WhiteSky zwraca HTTPS)
- Klucz "0" = pierwsza pozycja w galerii = miniaturka z ikonami

**DODAWANIE NOWEGO produktu — metoda `addInventoryProduct`:**
```json
{
  "inventory_id": 99954,
  "parent_id": <ID rodzica jeśli wariant>,
  "name": "...",
  "description": "<html opisu>",
  "description_extra1": "",
  "ean": "<EAN-13>",
  "sku": "<SKU>",
  "manufacturer": "<producent>",
  "category_id": <id kategorii>,
  "prices": {"29": <cena>},
  "tax_rate": 5,
  "weight": <waga w kg>,
  "images": {"0": "url:...", "1": "url:...", ...},
  "extra_field_9332": "1"
}
```

**AKTUALIZACJA istniejącego** — ta sama metoda z `product_id`:
- BL ZASTĘPUJE WSZYSTKIE zdjęcia — wysyłaj pełny zestaw, nie częściowy
- Jeśli dodajesz jedno zdjęcie → pobierz aktualne przez `getInventoryProductsList`, dołącz, wyślij całość

**CZEGO NIE ROBIĆ (sprawdzone błędy):**
- ❌ `["url:https://..."]` — tablica zamiast dict → ERROR_INVALID_DATA
- ❌ `{"1": "url:..."}` — klucz od "1" zamiast "0" → miniaturka nie pierwsza
- ❌ `{"0": "https://..."}` — brak prefix `url:` → ERROR_INVALID_DATA
- ❌ HTTP zamiast HTTPS → BL może odrzucić
- ❌ Aktualizacja częściowa zdjęć → BL kasuje pozostałe
- ❌ Wystawienie bez EAN → Allegro odrzuci ofertę

**Flow per wariant:**
1. Dodaj wariant → sprawdź w BL UI czy: miniaturka pierwsza ✓, wszystkie zdjęcia ✓, EAN ✓
2. Jeśli OK → następny wariant (ta sama marka/opis, inna pojemność i cena)
3. Na końcu sprawdź KAŻDY produkt w inventory 99954
4. Użytkownik wystawia z BaseLinker na Allegro ręcznie

---

## Skrypty pomocnicze

```
scripts/
  generate_graphics.py   ← Photoroom + Fal.ai + PIL ikony certyfikatów
  whitesky_upload.py     ← upload processed/ do WhiteSky Object Storage
  add_cert_icons.py      ← PIL: nakłada ikony certyfikatów na miniaturkę
```

Uruchomienie pełnego pipeline'u:
```bash
python scripts/generate_graphics.py --session <uuid> --producer "Plakias" --certs "bio,pdо"
```

---

## Weryfikacja końcowa (nie pomijaj)

- [ ] Miniaturka pierwsza w galerii BL (klucz "0")
- [ ] Ikony certyfikatów widoczne z listingu (nie za małe)
- [ ] Wszystkie 9 zdjęć załadowanych
- [ ] EAN przypisany do produktu
- [ ] Cena ustawiona per wariant
- [ ] Parametry Allegro kompletne
- [ ] Etykieta PDF: NALEŻY SPOŻYĆ PRZED + DATA PRODUKCJI + NUMER PARTII widoczne i bold
- [ ] Opis HTML bez `<table>` (Allegro blokuje)
- [ ] Hook unikatowy dla producenta (nie generyczny)
