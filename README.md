# AsysAuti_piranniaBites — WESAD Backend (różne pickli)

Krótki backend Flask do inspekcji danych uczestników zapisanych w plikach .pkl.

## Wymagania

- Python 3.8+
- Zainstaluj zależności z `requirements.txt`:

```powershell
python -m pip install -r requirements.txt
```

## Uruchamianie

```powershell
# uruchom lokalnie w trybie deweloperskim
python app.py
```

## Endpointy

- `GET /` — proste sprawdzenie, czy API działa.
- `GET /data_dir?dir=<path|S2|S3|auto>` — pokaż/ustaw katalog danych.
- `GET /participants` — lista plików `.pkl` i (opcjonalnie) wykryte subjecty.
  - Jeśli chcesz, żeby serwer deserializował (unpicklowal) pliki i wykrył subjecty, musisz wyrazić zgodę:
    - ustawić zmienną środowiskową `ALLOW_UNPICKLE=1` lub
    - dodać query param `allow_unpickle=1` do żądania.
- `GET /participant/<subject_id>?n=20&full=1` — szczegóły danego uczestnika.
  - Zwrot pełnych danych (`full=1`) jest ograniczony i nadal wymaga zgody na unpickling (jak wyżej).

## Bezpieczeństwo

Ładowanie (unpickling) plików `.pkl` może wykonywać kod i jest niebezpieczne dla plików pochodzących z niezaufanych źródeł. Domyślnie serwer wymaga jawnego zezwolenia (zmienna env lub query param) aby odczytać zawartość pickli.

## Dalsze kroki (opcjonalne)

- Dodać testy jednostkowe (pytest) dla funkcji pomocniczych.
- Ograniczyć zwracany rozmiar `full` lub udostępnić do pobrania pliki zamiast wysyłać duże JSONy.
- Rozważyć konwersję danych do bezpieczniejszego formatu (np. Parquet/CSV/JSON) i trzymać pickli tylko w zaufanym środowisku.
