# Task 4 – Snakemake pipeline (PM2.5 + PubMed)

## Opis
Projekt łączy obliczenia stężeń PM2.5 z wcześniejszych zadań z automatycznym mini-przeglądem literatury (PubMed, Biopython) oraz generuje wspólny raport końcowy.  
Pipeline działa inkrementalnie – jeśli wyniki dla danego roku już istnieją i wejścia się nie zmieniły, Snakemake nie uruchamia ponownie obliczeń ani pobierania danych.

---

## Jak uruchomić Task 4
0. Instalacja zależności:
```
pip install -r requirements.txt
```

1. Skonfiguruj parametry w pliku:
```
config/task4.yaml
```

Przykład:
```yaml
years:
  - 2021
  - 2024

cities:
  - Warszawa
  - Katowice

pm25:
  exceedance_limit: 20

pubmed:
  entrez_email: "ka.gozdek@student.uw.edu.pl"
  keyword: "Particulate Matter"
  limit: 1000
  batch_size: 200
  top_journals: 10
```

2. Uruchom pipeline:
```bash
snakemake -s Snakefile_task4 --cores 1
```

Wyniki pojawią się w katalogu:
```
results/
```

---

## Struktura wyników

Dla każdego roku:
```
results/pm25/{Y}/...
results/literature/{Y}/...
```

Raport zbiorczy:
```
results/report_{YEARS}.md
```
Wykresy do raportu:
```
results/report/...
```

---

## Scenariusz działania

### Uruchomienie 1
Config:
```yaml
years: [2021, 2024]
```

Pipeline:
- liczy PM2.5 dla 2021 i 2024,
- pobiera literaturę dla 2021 i 2024,
- generuje raport dla obu lat.

### Uruchomienie 2
Config:
```yaml
years: [2019, 2024]
```

Pipeline:
- liczy tylko 2019,
- pobiera literaturę tylko dla 2019,
- 2024 jest pomijany,
- generuje nowy raport dla {2019, 2024}.



## Unikalne nazewnictwo raportów i wykresów

Aby zachować pełną inkrementalność i uniknąć nadpisywania wyników między różnymi uruchomieniami pipeline, raporty oraz wykresy zbiorcze mają w nazwach listę analizowanych lat.  
Dzięki temu zmiana konfiguracji (np. inne lata) tworzy nowe pliki zamiast modyfikować stare.

Przykładowe artefakty:
- `results/report_{YEARS_STR}.md` – raport końcowy dla wybranych lat
- `results/literature/publications_trend_{YEARS_STR}.png` – trend liczby publikacji
- `results/literature/top_words_compare_{FIRST}_{LAST}.png` – porównanie słów w tytułach (pierwszy vs ostatni rok)


# Co dokładnie liczy pipeline?
## A) Analiza PM2.5 (dane GIOŚ)

Dla każdego roku:

1. pobierane jest archiwum danych PM2.5 z GIOŚ,
2. dane są wczytywane i czyszczone,
3. poprawiane są stare kody stacji,
4. korygowane są daty,
5. dane są łączone z metadanymi (miasta, województwa),
6. obliczane są:
   - **średnie dzienne stężeń PM2.5 dla wybranych w configu miast**,
   - **liczba dni z przekroczeniem normy PM2.5 na rok/miasto**.

Wyniki zapisywane są jako:

```
results/pm25/{YEAR}/daily_means.csv
results/pm25/{YEAR}/exceedance_days.csv
```

## B) Analiza literatury (PubMed)

Dla każdego roku:

1. budowane jest zapytanie PubMed na podstawie słowa kluczowego z configu oraz filtru daty:
   `keyword AND "YEAR"[PDAT]`,
2. Jeśli dla danego zapytania istnieje plik snapshot (zapisane PMID-y oraz total_count), pipeline wykorzystuje zapisane identyfikatory, w przeciwnym wypadku:
- wykonywane jest wyszukiwanie (`Entrez.esearch`) w celu uzyskania pełnej liczby publikacji (Count),
- zapisywana jest lista PMID-ów oraz total_count,
- pobierana jest tylko ograniczona liczba rekordów (`limit`) przy użyciu `Entrez.efetch`
3. z rekordów MEDLINE wyodrębniane są metadane:
   - PMID,
   - tytuł,
   - czasopismo,
   - autorzy,
   - abstrakt,
4. obliczane są agregacje:
   - łączna liczba publikacji w roku (na podstawie pełnego Count),
   - najczęstsze czasopisma (top journals),

5. generowany jest wykres słupkowy rozkładu publikacji po czasopismach.
Wyniki zapisywane są jako:

```
results/literature/{YEAR}/pubmed_papers.csv
results/literature/{YEAR}/summary_by_year.csv
results/literature/{YEAR}/top_journals.csv
results/literature/{YEAR}/papers_by_journal.png
```

Każdy rok zapisywany jest w osobnym katalogu, dzięki czemu pipeline działa inkrementalnie i nie przelicza ponownie lat, które zostały już wcześniej przetworzone.

##  C) Raport zbiorczy

```
results/report_{YEARS}.md
```
Zawiera:
- tabelę liczby dziennych przekroczeń PM2.5 (miasta × lata),
- heatmapę dziennych średnich (wybrane miasta),
- tabelę liczby publikacji na rok,
- tabele top czasopism,
- przykładowe tytuły prac,
- osadzone wykresy.


---

## Jak weryfikuję incrementalność
Sprawdzam logi Snakemake – dla już policzonych lat pojawia się komunikat **Nothing to be done (all requested files are present and up to date).**

---
### Powtarzalność

Pipeline uruchamiany jest z opcją:

snakemake --rerun-triggers checksum

Tryb `checksum` powoduje ponowne wykonanie reguł wtedy, gdy zmieni się rzeczywista zawartość pliku (obliczany jest hash pliku), a nie tylko jego data modyfikacji.

Różnica:
- mtime – sprawdza wyłącznie czas modyfikacji pliku
- checksum – sprawdza faktyczne zmiany danych (bezpieczniejsze i bardziej deterministyczne)

Dzięki temu pipeline jest bardziej powtarzalny i odporny na przypadkowe przebudowy.
Ddatkowo snapshot listy PMID zapewnia deterministyczność względem zestawu analizowanych publikacji.


