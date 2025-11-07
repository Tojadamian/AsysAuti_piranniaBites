# AsysAuti_piranniaBites — WESAD Backend (różne pickli)

Krótki backend Flask do inspekcji danych uczestników zapisanych w plikach .pkl.

## Wymagania

- Python 3.8+
- Zainstaluj zależności z `requirements.txt`:

```powershell
python -m pip install -r requirements.txt
```

# AsysAuti_piranniaBites — WESAD Backend (inspekcja plików .pkl)

Prosty backend napisany we Flask do szybkiej inspekcji danych uczestników zapisanych w plikach `.pkl`.

## Wymagania

- Python 3.8+
- Zainstaluj zależności z `requirements.txt`:

```powershell
python -m pip install -r requirements.txt
```

## Uruchamianie lokalne

Uruchom serwer w katalogu projektu:

```powershell
# (opcjonalnie) zezwól na unpickling w tej sesji:
$env:ALLOW_UNPICKLE = '1'
python .\app.py
```

Serwer domyślnie uruchamia się na `http://127.0.0.1:5000` (tryb developerski).

## Endpointy (krótkie przykłady)

- `GET /` — health check (zwraca tekst informujący, że API działa).
- `GET /data_dir?dir=<path|S2|S3|auto>` — zwraca aktualny katalog danych i listę plików. `dir=auto` lub `reset` usuwa ręczne ustawienie.
- `GET /participants` — lista plików `.pkl` i (opcjonalnie) wykryte subjecty. Jeśli unpickling jest wyłączony, endpoint zwraca tylko listę plików i notkę.
  - Aby włączyć analizę pickli możesz:
    - ustawić zmienną środowiskową `ALLOW_UNPICKLE=1`, lub
    - dodać query param `allow_unpickle=1` do żądania (np. `/participants?allow_unpickle=1`).
- `GET /participant/<subject_id>?n=20&full=1` — zwraca informacje o konkretnym uczestniku (subject, dostępne sygnały, sample etykiet). Wymaga zgody na unpickling (jak wyżej).
  - Dodatkowo API wspiera filtrowanie parametrów kanałów przez query param `params`, np. `?params=TEMP:100,EDA`.

Przykłady użycia (PowerShell / curl):

```powershell
# health
curl.exe -i "http://127.0.0.1:5000/"

# pokaż katalog danych
curl.exe -s -i "http://127.0.0.1:5000/data_dir"

# lista uczestników (wymaga zgody na unpickling)
curl.exe -s -i "http://127.0.0.1:5000/participants?allow_unpickle=1"

# szczegóły uczestnika (bez filtrowania)
curl.exe -s -i "http://127.0.0.1:5000/participant/2?allow_unpickle=1"

# szczegóły z filtrem parametrów (TEMP:100 próbki)
curl.exe -s -i "http://127.0.0.1:5000/participant/2?allow_unpickle=1&params=TEMP:100,EDA"
```

## Testy

Do repo dodałem proste testy jednostkowe i integracyjne używające `pytest`.

Uruchom testy lokalnie:

```powershell
python -m pip install -r requirements.txt
python -m pip install pytest
python -m pytest -q
```

Opis testów:

- `tests/test_app_utils.py` — testy jednostkowe dla `_summarize_object` i `get_data_dir`.
- `tests/test_endpoints.py` — testy uruchamiające endpointy przy użyciu Flask `test_client`; testy używają `monkeypatch` by zamockować ładowanie pickli, dzięki czemu są szybkie i bezpieczne.

## Bezpieczeństwo i uwagi

- Unpickling plików `.pkl` może wykonywać kod — nie włączaj go dla plików z niezaufanych źródeł.
- Domyślnie unpickling jest wyłączony; wymagane jest jawne allow (env lub query param).
- Repo nie powinno przechowywać bardzo dużych plików binarnych. Rozważ użycie Git LFS dla plików >100MB.

## Dalsze kroki

- Możemy dodać testy integracyjne z rzeczywistymi małymi plikami danych, lub rozbudować walidację parametrów `params` (np. dopasowanie fuzzy/regex).

---
