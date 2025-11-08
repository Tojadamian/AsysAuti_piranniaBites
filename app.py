from flask import Flask, jsonify, request
import pandas as pd
import pickle
import os
import glob
import re
import json
import math
from datetime import datetime

# optional requests - jeśli nie ma, użyjemy urllib
try:
    import requests
except Exception:
    requests = None

app = Flask(__name__)
try:
    # opcjonalne CORS dla wywołań z frontendu (Vite/localhost inny port)
    from flask_cors import CORS  # type: ignore
    # Rozszerzono zakres CORS aby umożliwić wybranie katalogu danych z ekranu logowania (endpoint /data_dir)
    # oraz pobieranie uczestnika i stanu stresu bez błędów CORS.
    CORS(app, resources={
        r"/api/*": {"origins": "*"},
        r"/data_dir*": {"origins": "*"},
        r"/participant*": {"origins": "*"},
        r"/participants*": {"origins": "*"},
        r"/api/stress_state*": {"origins": "*"},
    })
except Exception:
    # jeśli flask_cors nie jest zainstalowany – API nadal działa lokalnie (przeglądarka może blokować zapytania)
    pass

# Fallback: jeśli flask_cors nie jest zainstalowany, dodajemy prosty after_request,
# który ustawia nagłówki CORS dla wszystkich odpowiedzi. Pozwala to na szybkie
# prototypowanie bez instalowania dodatkowych zależności.
@app.after_request
def _add_cors_headers(response):
    try:
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    except Exception:
        pass
    return response

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# globalnie ustawiany katalog danych (można zmienić przez /data_dir?dir=)
CURRENT_DATA_DIR = None

# Ścieżki do katalogów z danymi (najpierw 'data_wesad', jeśli brak — 'S2')
DATA_DIR_CANDIDATES = ['S2', 'S3']
# Max number of items allowed to include as 'full' in summaries when slicing ranges
MAX_FULL_IN_SUMMARY = 200000

# ===================== KLASYFIKACJA STRESU / STANU EMOCJONALNEGO =====================
# Funkcje progowe dostarczone przez użytkownika – przeniesione do backendu.

def is_stress(f):
    return (
        (f.get('mean_eda') is not None and f['mean_eda'] > 0.761343)
        or (f.get('hr') is not None and f['hr'] > 66.870546)
        or (f.get('hrv') is not None and f['hrv'] < 325.906461)
        or (f.get('temp') is not None and f['temp'] < 31.217497)
        or (f.get('acc_rms') is not None and f['acc_rms'] > 1.015106)
    )

def is_pleasure(f):
    return (
        (f.get('mean_eda') is not None and f['mean_eda'] < 0.557787)
        and (f.get('hr') is not None and f['hr'] < 59.803059)
        and (f.get('hrv') is not None and f['hrv'] > 371.946967)
        and (f.get('temp') is not None and f['temp'] > 31.238812)
        and (f.get('acc_rms') is not None and f['acc_rms'] < 1.011331)
    )

def is_neutral(f):
    return (
        (f.get('mean_eda') is not None and 0.557787 <= f['mean_eda'] <= 0.761343)
        and (f.get('hr') is not None and 59.803059 <= f['hr'] <= 66.870546)
        and (f.get('hrv') is not None and 325.906461 <= f['hrv'] <= 371.946967)
        and (f.get('temp') is not None and 31.217497 <= f['temp'] <= 31.238812)
        and (f.get('acc_rms') is not None and 1.011331 <= f['acc_rms'] <= 1.015106)
    )

def classify(f):
    if is_stress(f):
        return 'stres'
    elif is_pleasure(f):
        return 'zadowolenie'
    elif is_neutral(f):
        return 'neutralny'
    else:
        return 'nieokreślony'

def _safe_mean(seq):
    try:
        if seq is None:
            return None
        if hasattr(seq, 'tolist'):
            seq = seq.tolist()
        seq = [float(x) for x in seq if x is not None]
        if not seq:
            return None
        return sum(seq) / len(seq)
    except Exception:
        return None

def _rms(seq):
    try:
        if seq is None:
            return None
        if hasattr(seq, 'tolist'):
            seq = seq.tolist()
        vals = [float(x) for x in seq if x is not None]
        if not vals:
            return None
        return math.sqrt(sum(x*x for x in vals) / len(vals))
    except Exception:
        return None

def _extract_features_from_signals(raw_signals):
    """Próbuje wydobyć metryki: mean_eda, hr, hrv, temp, acc_rms.

    Obsługuje strukturę jak w participant['signal']:
      {'chest': {'EDA': [...], 'TEMP': [...], 'HR': [...], 'HRV': [...]}, 'wrist': {...}}
    Szuka nazw kanałów (case-insensitive) zawierających odpowiednie fragmenty.
    Jeśli brak – zwraca None dla danej cechy.
    """
    features = {
        'mean_eda': None,
        'hr': None,
        'hrv': None,
        'temp': None,
        'acc_rms': None,
    }
    # Jeśli surowe sygnały są DataFrame'em z kolumnami typu EDA/HR/TEMP itp.
    try:
        import pandas as _pd
        if isinstance(raw_signals, _pd.DataFrame):
            cols_lower = {c.lower(): c for c in raw_signals.columns}
            # proste dopasowania nazw kolumn
            if 'eda' in cols_lower:
                features['mean_eda'] = _safe_mean(raw_signals[cols_lower['eda']])
            if 'hr' in cols_lower:
                features['hr'] = _safe_mean(raw_signals[cols_lower['hr']])
            if 'hrv' in cols_lower:
                features['hrv'] = _safe_mean(raw_signals[cols_lower['hrv']])
            elif 'rr' in cols_lower:  # przybliżenie HRV ze zmienności RR
                try:
                    seq = [float(x) for x in list(raw_signals[cols_lower['rr']]) if x is not None]
                    if len(seq) > 1:
                        m = sum(seq)/len(seq)
                        var = sum((x-m)**2 for x in seq)/(len(seq)-1)
                        features['hrv'] = math.sqrt(var)
                except Exception:
                    pass
            if 'temp' in cols_lower:
                features['temp'] = _safe_mean(raw_signals[cols_lower['temp']])
            # akcelerometr może mieć wiele osi; spróbuj ACC_X, ACC_Y, ACC_Z lub ACC
            acc_candidates = [c for c in raw_signals.columns if c.lower().startswith('acc')]
            if acc_candidates:
                try:
                    # jeśli wiele osi: RMS po wszystkich; jeśli jedna: RMS po niej
                    if len(acc_candidates) > 1:
                        # zbuduj listę RMS per wiersz, potem średnia RMS (globalna)
                        sq_sum = None
                        count_cols = 0
                        for c in acc_candidates:
                            try:
                                vals = [float(v) for v in raw_signals[c].tolist() if v is not None]
                            except Exception:
                                vals = []
                            if not vals:
                                continue
                            if sq_sum is None:
                                sq_sum = [0.0]*len(vals)
                            # Dopasuj długość jeśli różna — pomiń
                            if len(vals) != len(sq_sum):
                                continue
                            for i, v in enumerate(vals):
                                sq_sum[i] += v*v
                            count_cols += 1
                        if sq_sum and count_cols:
                            rms_seq = [math.sqrt(x/count_cols) for x in sq_sum]
                            features['acc_rms'] = _safe_mean(rms_seq)
                    else:
                        features['acc_rms'] = _rms(raw_signals[acc_candidates[0]])
                except Exception:
                    pass
            return features
    except Exception:
        pass
    # Jeżeli to nie jest dict, spróbujemy potraktować jako pojedynczy kontener sygnałów
    # i zeskalować przez iterację po sub-kanałach (DataFrame/Series/list/ndarray)
    if not isinstance(raw_signals, dict):
        # potraktuj jak jedną lokację bez nazw kanałów – jeśli DataFrame, obsłużymy kolumny
        try:
            import pandas as _pd
            if isinstance(raw_signals, _pd.DataFrame):
                # już obsłużone na początku – zwróć wynik
                return features
        except Exception:
            pass
        # nie wiemy jak nazwać kanał – spróbuj użyć RMS/mean tam gdzie ma sens
        maybe = _safe_mean(raw_signals)
        if maybe is not None and features['mean_eda'] is None:
            features['mean_eda'] = maybe
        return features

    # uniwersalny, rekurencyjny iterator po drzewie sygnałów
    def _iter_channels(obj, path=""):
        try:
            import numpy as _np
            import pandas as _pd
        except Exception:
            _np = None
            _pd = None
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_path = f"{path}/{k}" if path else str(k)
                yield from _iter_channels(v, new_path)
        else:
            # liść: DataFrame/Series/list/tuple/ndarray lub pojedyncza wartość
            try:
                if _pd is not None and isinstance(obj, _pd.DataFrame):
                    for col in obj.columns:
                        yield (f"{path}:{col}", obj[col])
                    return
                if _pd is not None and isinstance(obj, _pd.Series):
                    yield (path, obj)
                    return
            except Exception:
                pass
            try:
                if isinstance(obj, (list, tuple)):
                    yield (path, obj)
                    return
            except Exception:
                pass
            try:
                if _np is not None and isinstance(obj, _np.ndarray):
                    yield (path, obj)
                    return
            except Exception:
                pass
            # fallback – pojedyncza wartość
            yield (path, [obj])

    # Zbieraj kandydatów i specjalnie potraktuj ACC (może mieć wiele osi)
    acc_axes = {}
    for name, values in _iter_channels(raw_signals):
        lname = (name or "").lower()
        # heurystyki dopasowania nazw
        if 'eda' in lname and features['mean_eda'] is None:
            features['mean_eda'] = _safe_mean(values)
            continue
        if (lname == 'hr') or ('/hr' in lname) or (':hr' in lname) or (' heartrate' in lname) or lname.endswith('/hr'):
            if features['hr'] is None:
                features['hr'] = _safe_mean(values)
            continue
        if 'hrv' in lname and features['hrv'] is None:
            features['hrv'] = _safe_mean(values)
            continue
        if re.search(r'(^|[/:_\-])rr($|[/:_\-])', lname) and features['hrv'] is None:
            # przybliż HRV z RR jako odchylenie standardowe
            try:
                seq = list(values) if not hasattr(values, 'tolist') else values.tolist()
                seq = [float(x) for x in seq if x is not None]
                if len(seq) > 1:
                    m = sum(seq)/len(seq)
                    var = sum((x-m)**2 for x in seq)/(len(seq)-1)
                    features['hrv'] = math.sqrt(var)
            except Exception:
                pass
            continue
        if 'temp' in lname and features['temp'] is None:
            features['temp'] = _safe_mean(values)
            continue
        if 'acc' in lname:
            # spróbuj zebrać osie (x/y/z) do wspólnego RMS
            axis = None
            m = re.search(r'acc[^a-z0-9]?([xyz])', lname)
            if m:
                axis = m.group(1)
            try:
                seq = list(values) if not hasattr(values, 'tolist') else values.tolist()
                seq = [float(x) for x in seq if x is not None]
                if axis:
                    acc_axes[axis] = seq
                else:
                    # pojedynczy kanał acc — policz rms bez osi
                    if features['acc_rms'] is None:
                        features['acc_rms'] = _rms(seq)
            except Exception:
                pass

    # jeśli mamy wiele osi akcelerometru i jeszcze nie policzono acc_rms
    if features['acc_rms'] is None and len(acc_axes) >= 2:
        # znajdź minimalną wspólną długość i policz RMS po osiach dla każdej próbki
        try:
            L = min(len(v) for v in acc_axes.values() if isinstance(v, list) and v)
            if L and L > 0:
                axes = [acc_axes.get('x'), acc_axes.get('y'), acc_axes.get('z')]
                axes = [a for a in axes if isinstance(a, list) and a]
                if axes:
                    rms_seq = []
                    for i in range(L):
                        s = 0.0
                        c = 0
                        for a in axes:
                            try:
                                v = float(a[i])
                                s += v*v
                                c += 1
                            except Exception:
                                pass
                        if c:
                            rms_seq.append(math.sqrt(s / c))
                    if rms_seq:
                        features['acc_rms'] = _safe_mean(rms_seq)
        except Exception:
            pass

    return features


def get_data_dir():
    """Zwraca aktualny katalog danych.
    - jeśli CURRENT_DATA_DIR ustawiony i istnieje — zwraca go
    - inaczej zwraca pierwszy istniejący z DATA_DIR_CANDIDATES
    - fallback: pierwsza pozycja z listy (może nie istnieć)
    """
    global CURRENT_DATA_DIR
    if CURRENT_DATA_DIR and os.path.isdir(CURRENT_DATA_DIR):
        return CURRENT_DATA_DIR
    for d in DATA_DIR_CANDIDATES:
        # sprawdź bezwzględną i relatywną ścieżkę względem projektu
        if os.path.isabs(d) and os.path.isdir(d):
            return d
        rel = os.path.join(BASE_DIR, d)
        if os.path.isdir(rel):
            return rel
        if os.path.isdir(d):
            return d
    # fallback — zwraca pierwszy, nawet jeśli nie istnieje (błąd będzie później)
    # zwróć ścieżkę relatywną do projektu
    return os.path.join(BASE_DIR, DATA_DIR_CANDIDATES[0])

def _safe_pickle_load(f, allow_unpickle=True):
    """Próbuje bezpiecznie załadować pickle.

    Jeśli allow_unpickle==False to rzuca RuntimeError — mechanizm pozwala kontrolować
    czy aplikacja ma prawo wykonywać unpickling (bezpieczniejsza konfiguracja).
    """
    if not allow_unpickle:
        raise RuntimeError('Unpickling disabled (allow_unpickle=False). Set ALLOW_UNPICKLE=1 or pass allow_unpickle=1 in query params to enable loading pickli.')

    try:
        return pickle.load(f)
    except (UnicodeDecodeError, ValueError, pickle.UnpicklingError):
        try:
            f.seek(0)
            return pickle.load(f, encoding='latin1')
        except TypeError:
            # starsze wersje pickle mogą nie akceptować encoding param — rzuć oryginalny wyjątek
            f.seek(0)
            return pickle.load(f)
    except Exception:
        f.seek(0)
        return pickle.load(f)


def load_participant_data(subject_id):
    """Wczytuje dane uczestnika z obsługą kompatybilności pickle (Py2 -> Py3)."""
    data_dir = get_data_dir()
    # domyślnie zezwalamy na unpickling; jeśli endpoint chce zablokować ładowanie,
    # powinien przekazać allow_unpickle=False (lub endpoint sprawdzi uprawnienia przed wywołaniem)
    allow_unpickle = True
    target_name = f'S{subject_id}'
    # 1) próba dedykowanego pliku
    pkl_path = os.path.join(data_dir, f'{target_name}.pkl')
    if os.path.exists(pkl_path):
        with open(pkl_path, 'rb') as f:
            return _safe_pickle_load(f, allow_unpickle=allow_unpickle)

    # 2) spróbuj dopasować wzorzec S{subject_id}*.pkl
    matches = glob.glob(os.path.join(data_dir, f'{target_name}*.pkl'))
    if matches:
        with open(matches[0], 'rb') as f:
            return _safe_pickle_load(f, allow_unpickle=allow_unpickle)

    # 3) jeśli nie znaleziono w bieżącym katalogu danych, spróbuj przeszukać
    # pozostałe kandydackie katalogi (DATA_DIR_CANDIDATES), np. S2, S3.
    for cand in DATA_DIR_CANDIDATES:
        # znormalizuj ścieżkę względem BASE_DIR jeśli nie jest absolutna
        cand_path = cand if os.path.isabs(cand) else os.path.join(BASE_DIR, cand)
        # pomiń już sprawdzany katalog
        try:
            if os.path.abspath(cand_path) == os.path.abspath(data_dir):
                continue
        except Exception:
            pass
        if not os.path.isdir(cand_path):
            continue
        # sprawdź dedykowany plik
        alt_pkl = os.path.join(cand_path, f'{target_name}.pkl')
        if os.path.exists(alt_pkl):
            with open(alt_pkl, 'rb') as f:
                return _safe_pickle_load(f, allow_unpickle=allow_unpickle)
        # spróbuj dopasować wzorzec
        alt_matches = glob.glob(os.path.join(cand_path, f'{target_name}*.pkl'))
        if alt_matches:
            with open(alt_matches[0], 'rb') as f:
                return _safe_pickle_load(f, allow_unpickle=allow_unpickle)

    # 3) jeśli powyżej nie ma — załaduj pierwszy plik .pkl w katalogu (np. S2.pkl) i wyszukaj w nim
    all_pkls = glob.glob(os.path.join(data_dir, '*.pkl'))
    if not all_pkls:
        dir_contents = os.listdir(data_dir) if os.path.isdir(data_dir) else 'brak katalogu'
        raise FileNotFoundError(f'Brak plików .pkl w katalogu danych. Zawartość: {dir_contents}')

    with open(all_pkls[0], 'rb') as f:
        container = _safe_pickle_load(f, allow_unpickle=allow_unpickle)

    # jeśli container jest dict i ma klucz typu 'S1' lub '1'
    if isinstance(container, dict):
        # bezpośredni klucz S{n}
        if target_name in container:
            return container[target_name]
        # klucz jako liczba lub string '1'
        if str(subject_id) in container:
            return container[str(subject_id)]
        # spróbuj znaleźć elementy gdzie wartość ma pole 'subject'
        for k, v in container.items():
            try:
                if isinstance(v, dict) and v.get('subject') in (target_name, subject_id, str(subject_id)):
                    return v
            except Exception:
                continue

    # jeśli lista uczestników
    if isinstance(container, (list, tuple)):
        for item in container:
            try:
                if isinstance(item, dict) and item.get('subject') in (target_name, subject_id, str(subject_id)):
                    return item
            except Exception:
                continue

    # jeśli pandas DataFrame
    try:
        import pandas as _pd
        if isinstance(container, _pd.DataFrame):
            if 'subject' in container.columns:
                sel = container[container['subject'].isin([target_name, subject_id, str(subject_id)])]
                if not sel.empty:
                    return sel
    except Exception:
        pass

    # jeśli nic nie znaleziono — zwróć pomocniczy błąd z listą plików
    raise FileNotFoundError(f'Nie znaleziono danych dla {target_name} w plikach: {", ".join(os.path.basename(p) for p in all_pkls)}')

@app.route('/')
def home():
    return "WESAD Backend API działa"

@app.route('/data_dir', methods=['GET'])
def data_dir_info():
    """Zwraca/ustawia katalog danych i listę plików.
    Query params:
      - dir=<nazwa_katalogu|ścieżka|auto>:
          * jeśli podane i istnieje — ustawia CURRENT_DATA_DIR na tę ścieżkę
          * jeśli 'auto' lub 'reset' — usuwa ustawienie (wraca do automatycznego wyboru)
      - example: /data_dir?dir=S3 lub /data_dir?dir=/full/path/to/S3
    """
    global CURRENT_DATA_DIR
    d = request.args.get('dir')
    resolved = None

    if d:
        # reset do automatycznego wyboru
        if d.lower() in ('auto', 'reset', ''):
            CURRENT_DATA_DIR = None
        else:
            # sprawdź bezwzględną ścieżkę lub względną względem BASE_DIR
            candidate = d if os.path.isabs(d) else os.path.join(BASE_DIR, d)
            # jeśli nie istnieje pod tą relatywną ścieżką, spróbuj dokładnie tak jak wpisano (może już jest absolutna lub w CWD)
            if not os.path.isdir(candidate) and os.path.isdir(d):
                candidate = d
            if not os.path.isdir(candidate):
                return jsonify({'error': f'Katalog nie istnieje: {d}'}), 400
            CURRENT_DATA_DIR = candidate

    # użyj aktualnej/resolved ścieżki
    data_dir = get_data_dir()
    files = []
    if os.path.isdir(data_dir):
        files = sorted(os.listdir(data_dir))
    return jsonify({'data_dir': data_dir, 'files': files})

def _summarize_object(obj, n=20, include_full=False, max_full=100000):
    """Zwraca bezpieczne podsumowanie obiektu (length, dtype, sample, opcjonalnie full)."""
    try:
        import numpy as _np
        import pandas as _pd
    except Exception:
        _np = None
        _pd = None

    summary = {'type': type(obj).__name__}

    # pandas Series
    if _pd is not None and isinstance(obj, _pd.Series):
        length = len(obj)
        summary.update({'length': int(length), 'dtype': str(obj.dtype)})
        try:
            summary['sample'] = obj.iloc[:n].tolist()
        except Exception:
            summary['sample'] = list(obj.iloc[:n].astype(str))
        if include_full and length <= max_full:
            try:
                summary['full'] = obj.tolist()
            except Exception:
                pass
        return summary

    # pandas DataFrame
    if _pd is not None and isinstance(obj, _pd.DataFrame):
        length = len(obj)
        summary.update({'length': int(length), 'columns': list(obj.columns)})
        try:
            summary['sample_rows'] = obj.head(n).to_dict(orient='records')
        except Exception:
            summary['sample_rows'] = []
        if include_full and length <= max_full:
            try:
                summary['full_rows'] = obj.to_dict(orient='records')
            except Exception:
                pass
        return summary

    # numpy array
    if _np is not None and isinstance(obj, _np.ndarray):
        length = obj.size
        summary.update({'length': int(length), 'dtype': str(obj.dtype)})
        try:
            summary['sample'] = obj.flatten()[:n].tolist()
        except Exception:
            summary['sample'] = []
        if include_full and length <= max_full:
            try:
                summary['full'] = obj.flatten().tolist()
            except Exception:
                pass
        return summary

    # list/tuple
    if isinstance(obj, (list, tuple)):
        length = len(obj)
        summary.update({'length': int(length)})
        try:
            summary['sample'] = [x if isinstance(x, (int, float, str, bool, type(None))) else str(x) for x in list(obj)[:n]]
        except Exception:
            summary['sample'] = []
        if include_full and length <= max_full:
            try:
                summary['full'] = [x if isinstance(x, (int, float, str, bool, type(None))) else str(x) for x in list(obj)]
            except Exception:
                pass
        return summary

    # other iterables
    try:
        length = len(obj)
        summary.update({'length': int(length)})
    except Exception:
        summary.update({'length': None})

    # try slicing / tolist
    try:
        s = obj[:n]
        try:
            summary['sample'] = s.tolist()
        except Exception:
            summary['sample'] = [str(x) for x in s]
    except Exception:
        # fallback single value
        try:
            summary['sample'] = [obj]
        except Exception:
            summary['sample'] = [str(obj)]

    return summary


def _is_unpickle_allowed():
    """Sprawdza, czy unpickling jest dozwolony globalnie (env) lub dla bieżącego żądania (query param).

    Zwraca True jeśli:
      - zmienna środowiskowa ALLOW_UNPICKLE jest ustawiona na '1'|'true' (case-insensitive)
      OR
      - w query-param żądania przekazano allow_unpickle=1/true
    Jeśli funkcja wywołana poza kontekstem żądania Flask, tylko sprawdza zmienną środowiskową.
    """
    env = os.environ.get('ALLOW_UNPICKLE', '0').lower() in ('1', 'true')
    try:
        # request może działać tylko w kontekście Flask
        q = request.args.get('allow_unpickle', '0').lower() in ('1', 'true')
    except Exception:
        q = False
    return env or q

@app.route('/participant/<subject_id>', methods=['GET'])
def get_participant_info(subject_id):
    """Zwraca rozszerzone informacje o uczestniku.
    Query params:
      - n: liczba próbek w polu 'sample' (domyślnie 20)
      - full: jeśli 1, spróbuje dołączyć pełne dane (ale tylko jeśli nie za duże)
    """
    try:
        n = int(request.args.get('n', 20))
    except Exception:
        n = 20
    include_full = request.args.get('full', '0') in ('1', 'true', 'True')
    # optional range slicing: 'start:end' (both inclusive/exclusive semantics like python slicing start:end)
    range_spec = request.args.get('range')
    range_slice = None
    if range_spec:
        try:
            parts = range_spec.split(':')
            if len(parts) == 2:
                start = int(parts[0]) if parts[0] != '' else None
                end = int(parts[1]) if parts[1] != '' else None
                range_slice = (start, end)
        except Exception:
            range_slice = None

    # bezpieczeństwo unpicklingu: wymagaj zgody przez env lub query param
    if not _is_unpickle_allowed():
        return jsonify({'error': 'Unpickling jest wyłączony. Ustaw zmienną środowiskową ALLOW_UNPICKLE=1 lub dodaj query param allow_unpickle=1.'}), 403

    try:
        data = load_participant_data(subject_id)
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # subject
    subject = None
    try:
        subject = data.get('subject', f'S{subject_id}')
    except Exception:
        subject = f'S{subject_id}'

    # signals - staramy się obsłużyć różne formaty
    # Nowość: obsługa query param `params` w formatach:
    #   - params=TEMP,EDA
    #   - params=TEMP:100,EDA:50
    # Jeśli params podane, zwracamy tylko dopasowane kanały (porównanie case-insensitive)
    params_spec = request.args.get('params')
    requested_params = {}
    if params_spec:
        for part in params_spec.split(','):
            part = part.strip()
            if not part:
                continue
            if ':' in part:
                name, val = part.split(':', 1)
                try:
                    requested_params[name.strip().lower()] = int(val)
                except Exception:
                    requested_params[name.strip().lower()] = n
            else:
                requested_params[part.strip().lower()] = None

    signals = {}
    truncated_channels = []
    try:
        raw_signals = data.get('signal', {})
    except Exception:
        raw_signals = data  # czasem cały obiekt to sygnały

    found_params = set()
    # prepared JSON-return for requested params when include_full is True
    requested_params_json = None

    if isinstance(raw_signals, dict):
        # oczekujemy keys: 'chest' i 'wrist' ale dopuszczamy inne
        for loc, loc_val in raw_signals.items():
            # jeśli loc_val jest dict: map channel->data
            if isinstance(loc_val, dict):
                signals[loc] = {}
                for ch_name, ch_val in loc_val.items():
                    key_lower = str(ch_name).lower()
                    # jeśli użytkownik podał filtrowanie parametrów — pomin inne
                    if requested_params and key_lower not in requested_params:
                        continue
                    # użyj długości określonej dla parametru jeśli podana, inaczej globalne n
                    per_n = requested_params.get(key_lower) if requested_params.get(key_lower) is not None else n
                    # jeśli podano range_slice, spróbuj przyciąć ch_val (pandas Series/DataFrame, list, numpy array)
                    if range_slice:
                        sstart, send = range_slice
                        try:
                            # pandas objects
                            import pandas as _pd
                            import numpy as _np
                            if isinstance(ch_val, _pd.Series) or isinstance(ch_val, _pd.DataFrame):
                                ch_val_s = ch_val.iloc[sstart:send]
                                try:
                                    slen = len(ch_val_s)
                                except Exception:
                                    slen = None
                                show_full = include_full or (slen is not None and slen <= MAX_FULL_IN_SUMMARY)
                                per_n_use = slen if (slen is not None and show_full) else per_n
                                signals[loc][ch_name] = _summarize_object(ch_val_s, n=per_n_use, include_full=show_full)
                                found_params.add(key_lower)
                                continue
                            if isinstance(ch_val, list) or isinstance(ch_val, tuple):
                                ch_val_s = list(ch_val)[sstart:send]
                                try:
                                    slen = len(ch_val_s)
                                except Exception:
                                    slen = None
                                show_full = include_full or (slen is not None and slen <= MAX_FULL_IN_SUMMARY)
                                per_n_use = slen if (slen is not None and show_full) else per_n
                                signals[loc][ch_name] = _summarize_object(ch_val_s, n=per_n_use, include_full=show_full)
                                found_params.add(key_lower)
                                continue
                            if isinstance(ch_val, _np.ndarray):
                                ch_val_s = ch_val[sstart:send]
                                try:
                                    slen = int(ch_val_s.shape[0]) if hasattr(ch_val_s, 'shape') else len(ch_val_s)
                                except Exception:
                                    try:
                                        slen = len(ch_val_s)
                                    except Exception:
                                        slen = None
                                show_full = include_full or (slen is not None and slen <= MAX_FULL_IN_SUMMARY)
                                per_n_use = slen if (slen is not None and show_full) else per_n
                                signals[loc][ch_name] = _summarize_object(ch_val_s, n=per_n_use, include_full=show_full)
                                found_params.add(key_lower)
                                continue
                        except Exception:
                            # fallback to original processing below
                            pass
                    # If client requested full data, try to convert raw object to JSON-friendly
                    try:
                        import numpy as _np
                        import pandas as _pd
                    except Exception:
                        _np = None
                        _pd = None

                    def _to_jsonable(obj):
                        # pandas
                        try:
                            if _pd is not None and isinstance(obj, _pd.DataFrame):
                                return obj.to_dict(orient='records')
                            if _pd is not None and isinstance(obj, _pd.Series):
                                return obj.tolist()
                        except Exception:
                            pass
                        # numpy
                        try:
                            if _np is not None and isinstance(obj, _np.ndarray):
                                return obj.tolist()
                        except Exception:
                            pass
                        # list/tuple
                        try:
                            if isinstance(obj, (list, tuple)):
                                return list(obj)
                        except Exception:
                            pass
                        # dict -> try to make values JSONable
                        try:
                            if isinstance(obj, dict):
                                out = {}
                                for k, v in obj.items():
                                    try:
                                        out[k] = _to_jsonable(v)
                                    except Exception:
                                        out[k] = str(v)
                                return out
                        except Exception:
                            pass
                        # fallback to string
                        try:
                            return str(obj)
                        except Exception:
                            return None

                    if include_full:
                        # determine sliced value if requested
                        try:
                            if range_slice:
                                sstart, send = range_slice
                                try:
                                    if _pd is not None and (isinstance(ch_val, _pd.Series) or isinstance(ch_val, _pd.DataFrame)):
                                        ch_val_use = ch_val.iloc[sstart:send]
                                    elif isinstance(ch_val, (list, tuple)):
                                        ch_val_use = list(ch_val)[sstart:send]
                                    elif _np is not None and isinstance(ch_val, _np.ndarray):
                                        ch_val_use = ch_val[sstart:send]
                                    else:
                                        ch_val_use = ch_val
                                except Exception:
                                    ch_val_use = ch_val
                            else:
                                ch_val_use = ch_val
                        except Exception:
                            ch_val_use = ch_val

                        # compute length if possible without materializing full list
                        slen = None
                        try:
                            if _pd is not None and (isinstance(ch_val_use, _pd.Series) or isinstance(ch_val_use, _pd.DataFrame)):
                                slen = len(ch_val_use)
                            elif isinstance(ch_val_use, (list, tuple)):
                                slen = len(ch_val_use)
                            elif _np is not None and isinstance(ch_val_use, _np.ndarray):
                                slen = int(ch_val_use.shape[0]) if hasattr(ch_val_use, 'shape') else len(ch_val_use)
                        except Exception:
                            slen = None

                        # if too large, truncate and mark
                        if slen is not None and slen > MAX_FULL_IN_SUMMARY:
                            try:
                                if _pd is not None and (isinstance(ch_val_use, _pd.Series) or isinstance(ch_val_use, _pd.DataFrame)):
                                    truncated = ch_val_use.iloc[:MAX_FULL_IN_SUMMARY].to_dict(orient='records') if hasattr(ch_val_use, 'to_dict') else list(ch_val_use.iloc[:MAX_FULL_IN_SUMMARY])
                                elif _np is not None and isinstance(ch_val_use, _np.ndarray):
                                    truncated = ch_val_use[:MAX_FULL_IN_SUMMARY].tolist()
                                else:
                                    truncated = list(ch_val_use)[:MAX_FULL_IN_SUMMARY]
                            except Exception:
                                truncated = _to_jsonable(ch_val_use)[:MAX_FULL_IN_SUMMARY] if isinstance(_to_jsonable(ch_val_use), list) else _to_jsonable(ch_val_use)
                            signals[loc][ch_name] = {'data': truncated, 'truncated': True, 'total_length': slen}
                            truncated_channels.append(f"{loc}/{ch_name}")
                        else:
                            signals[loc][ch_name] = _to_jsonable(ch_val_use)
                    else:
                        signals[loc][ch_name] = _summarize_object(ch_val, n=per_n, include_full=include_full)
                    found_params.add(key_lower)
            else:
                # pojedynczy obiekt pod 'chest' np. DataFrame/ndarray
                # Jeśli podano filtrowanie, spróbuj dopasować nazwę lokacji jako parametr
                if requested_params and str(loc).lower() not in requested_params:
                    continue
                per_n = requested_params.get(str(loc).lower()) if requested_params.get(str(loc).lower()) is not None else n
                # apply range_slice to the whole loc_val if possible
                if range_slice:
                    sstart, send = range_slice
                    try:
                        import pandas as _pd
                        import numpy as _np
                        if isinstance(loc_val, _pd.DataFrame) or isinstance(loc_val, _pd.Series):
                            loc_val_s = loc_val.iloc[sstart:send]
                            try:
                                slen = len(loc_val_s)
                            except Exception:
                                slen = None
                            show_full = include_full or (slen is not None and slen <= MAX_FULL_IN_SUMMARY)
                            per_n_use = slen if (slen is not None and show_full) else per_n
                            signals[loc] = _summarize_object(loc_val_s, n=per_n_use, include_full=show_full)
                            found_params.add(str(loc).lower())
                            continue
                        if isinstance(loc_val, list) or isinstance(loc_val, tuple):
                            loc_val_s = list(loc_val)[sstart:send]
                            try:
                                slen = len(loc_val_s)
                            except Exception:
                                slen = None
                            show_full = include_full or (slen is not None and slen <= MAX_FULL_IN_SUMMARY)
                            per_n_use = slen if (slen is not None and show_full) else per_n
                            signals[loc] = _summarize_object(loc_val_s, n=per_n_use, include_full=show_full)
                            found_params.add(str(loc).lower())
                            continue
                        if isinstance(loc_val, _np.ndarray):
                            loc_val_s = loc_val[sstart:send]
                            try:
                                slen = int(loc_val_s.shape[0]) if hasattr(loc_val_s, 'shape') else len(loc_val_s)
                            except Exception:
                                try:
                                    slen = len(loc_val_s)
                                except Exception:
                                    slen = None
                            show_full = include_full or (slen is not None and slen <= MAX_FULL_IN_SUMMARY)
                            per_n_use = slen if (slen is not None and show_full) else per_n
                            signals[loc] = _summarize_object(loc_val_s, n=per_n_use, include_full=show_full)
                            found_params.add(str(loc).lower())
                            continue
                    except Exception:
                        pass
                # if client requested full for the whole location, try to return raw JSONable content
                try:
                    import numpy as _np
                    import pandas as _pd
                except Exception:
                    _np = None
                    _pd = None

                def _to_jsonable_loc(obj):
                    try:
                        if _pd is not None and isinstance(obj, _pd.DataFrame):
                            return obj.to_dict(orient='records')
                        if _pd is not None and isinstance(obj, _pd.Series):
                            return obj.tolist()
                    except Exception:
                        pass
                    try:
                        if _np is not None and isinstance(obj, _np.ndarray):
                            return obj.tolist()
                    except Exception:
                        pass
                    try:
                        if isinstance(obj, (list, tuple)):
                            return list(obj)
                    except Exception:
                        pass
                    try:
                        if isinstance(obj, dict):
                            return obj
                    except Exception:
                        pass
                    try:
                        return str(obj)
                    except Exception:
                        return None

                if include_full:
                    # use slicing already applied (loc_val_s) if present, else loc_val
                    try:
                        if range_slice:
                            sstart, send = range_slice
                            if _pd is not None and (isinstance(loc_val, _pd.DataFrame) or isinstance(loc_val, _pd.Series)):
                                loc_val_use = loc_val.iloc[sstart:send]
                            elif isinstance(loc_val, (list, tuple)):
                                loc_val_use = list(loc_val)[sstart:send]
                            elif _np is not None and isinstance(loc_val, _np.ndarray):
                                loc_val_use = loc_val[sstart:send]
                            else:
                                loc_val_use = loc_val
                        else:
                            loc_val_use = loc_val
                    except Exception:
                        loc_val_use = loc_val

                    # compute slen and possibly truncate
                    slen = None
                    try:
                        if _pd is not None and (isinstance(loc_val_use, _pd.DataFrame) or isinstance(loc_val_use, _pd.Series)):
                            slen = len(loc_val_use)
                        elif isinstance(loc_val_use, (list, tuple)):
                            slen = len(loc_val_use)
                        elif _np is not None and isinstance(loc_val_use, _np.ndarray):
                            slen = int(loc_val_use.shape[0]) if hasattr(loc_val_use, 'shape') else len(loc_val_use)
                    except Exception:
                        slen = None

                    if slen is not None and slen > MAX_FULL_IN_SUMMARY:
                        try:
                            if _pd is not None and (isinstance(loc_val_use, _pd.DataFrame) or isinstance(loc_val_use, _pd.Series)):
                                truncated = loc_val_use.iloc[:MAX_FULL_IN_SUMMARY].to_dict(orient='records') if hasattr(loc_val_use, 'to_dict') else list(loc_val_use.iloc[:MAX_FULL_IN_SUMMARY])
                            elif _np is not None and isinstance(loc_val_use, _np.ndarray):
                                truncated = loc_val_use[:MAX_FULL_IN_SUMMARY].tolist()
                            else:
                                truncated = list(loc_val_use)[:MAX_FULL_IN_SUMMARY]
                        except Exception:
                            truncated = _to_jsonable_loc(loc_val_use)
                            if isinstance(truncated, list):
                                truncated = truncated[:MAX_FULL_IN_SUMMARY]
                        signals[loc] = {'data': truncated, 'truncated': True, 'total_length': slen}
                        truncated_channels.append(loc)
                    else:
                        signals[loc] = _to_jsonable_loc(loc_val_use)
                else:
                    signals[loc] = _summarize_object(loc_val, n=per_n, include_full=include_full)
                found_params.add(str(loc).lower())
    else:
        # raw_signals nie jest dict — zrób proste podsumowanie całego obiektu
        # jeśli podano parametry i żadna pasuje, zostaw puste
        if requested_params:
            signals = {}
        else:
            signals = {'signal_container': _summarize_object(raw_signals, n=n, include_full=include_full)}

    # If client requested full data, rebuild `signals` from raw_signals to avoid mixed summaries/full
    if include_full:
        def _convert_and_maybe_truncate(obj):
            try:
                import numpy as _np
                import pandas as _pd
            except Exception:
                _np = None
                _pd = None

            # apply range slice if present
            obj_use = obj
            if range_slice:
                sstart, send = range_slice
                try:
                    if _pd is not None and (isinstance(obj, _pd.Series) or isinstance(obj, _pd.DataFrame)):
                        obj_use = obj.iloc[sstart:send]
                    elif isinstance(obj, (list, tuple)):
                        obj_use = list(obj)[sstart:send]
                    elif _np is not None and isinstance(obj, _np.ndarray):
                        obj_use = obj[sstart:send]
                except Exception:
                    obj_use = obj

            # determine length
            slen = None
            try:
                if _pd is not None and (isinstance(obj_use, _pd.Series) or isinstance(obj_use, _pd.DataFrame)):
                    slen = len(obj_use)
                elif isinstance(obj_use, (list, tuple)):
                    slen = len(obj_use)
                elif _np is not None and isinstance(obj_use, _np.ndarray):
                    slen = int(obj_use.shape[0]) if hasattr(obj_use, 'shape') else len(obj_use)
            except Exception:
                slen = None

            # if too large, truncate
            try:
                if slen is not None and slen > MAX_FULL_IN_SUMMARY:
                    if _pd is not None and (isinstance(obj_use, _pd.DataFrame) or isinstance(obj_use, _pd.Series)):
                        truncated = obj_use.iloc[:MAX_FULL_IN_SUMMARY].to_dict(orient='records') if hasattr(obj_use, 'to_dict') else list(obj_use.iloc[:MAX_FULL_IN_SUMMARY])
                    elif _np is not None and isinstance(obj_use, _np.ndarray):
                        truncated = obj_use[:MAX_FULL_IN_SUMMARY].tolist()
                    else:
                        truncated = list(obj_use)[:MAX_FULL_IN_SUMMARY]
                    return {'data': truncated, 'truncated': True, 'total_length': slen}
                # else convert fully
                if _pd is not None and isinstance(obj_use, _pd.DataFrame):
                    return obj_use.to_dict(orient='records')
                if _pd is not None and isinstance(obj_use, _pd.Series):
                    return obj_use.tolist()
                if _np is not None and isinstance(obj_use, _np.ndarray):
                    return obj_use.tolist()
                if isinstance(obj_use, (list, tuple)):
                    return list(obj_use)
                if isinstance(obj_use, dict):
                    out = {}
                    for k, v in obj_use.items():
                        try:
                            out[k] = _convert_and_maybe_truncate(v)
                        except Exception:
                            out[k] = str(v)
                    return out
                return str(obj_use)
            except Exception:
                return str(obj_use)

        # rebuild signals and found_params strictly from raw_signals
        signals = {}
        found_params = set()
        # prepare structure to return requested params as JSON
        requested_params_json = {}
        if isinstance(raw_signals, dict):
            for loc, loc_val in raw_signals.items():
                if isinstance(loc_val, dict):
                    signals[loc] = {}
                    for ch_name, ch_val in loc_val.items():
                        key_lower = str(ch_name).lower()
                        if requested_params and key_lower not in requested_params:
                            continue
                        signals[loc][ch_name] = _convert_and_maybe_truncate(ch_val)
                        # collect requested params JSON mapping
                        if requested_params and key_lower in requested_params:
                            # store under location
                            requested_params_json.setdefault(key_lower, {})[loc] = signals[loc][ch_name]
                        found_params.add(key_lower)
                else:
                    if requested_params and str(loc).lower() not in requested_params:
                        continue
                    signals[loc] = _convert_and_maybe_truncate(loc_val)
                    if requested_params and str(loc).lower() in requested_params:
                        requested_params_json.setdefault(str(loc).lower(), {})[loc] = signals[loc]
                    found_params.add(str(loc).lower())
        else:
            # raw_signals is a single object
            signals = {'signal_container': _convert_and_maybe_truncate(raw_signals)}
            if requested_params:
                # if user requested the whole container as a param, include it
                for p in requested_params.keys():
                    requested_params_json.setdefault(p, signals['signal_container'])
    missing_params = []
    if requested_params:
        for p in requested_params.keys():
            if p not in found_params:
                missing_params.append(p)

    # labels
    labels_sample = []
    try:
        labels = data.get('label', [])
        try:
            # pandas Series / numpy / list
            labels_sample = _summarize_object(labels, n=n, include_full=False).get('sample', [])
        except Exception:
            labels_sample = []
    except Exception:
        labels_sample = []

    # dodatkowe metadane (wyklucz podstawowe klucze)
    metadata = {}
    try:
        for k, v in getattr(data, 'items', lambda: {})():
            if k in ('subject', 'signal', 'label'):
                continue
            # mały podgląd wartości/metadanych
            try:
                metadata[k] = {'type': type(v).__name__, 'preview': _summarize_object(v, n=5, include_full=False).get('sample')}
            except Exception:
                metadata[k] = {'type': type(v).__name__}
    except Exception:
        # jeśli data nie jest dict-like, pomiń
        pass

    info = {
        'subject': subject,
        'available_signals': signals,
        'labels_sample': labels_sample,
        'metadata_preview': metadata
    }
    if requested_params_json:
        info['requested_params'] = requested_params_json
    # if any channels were truncated, include a note
    if truncated_channels:
        info['truncated_channels'] = truncated_channels
        info['note'] = f"Returned first {MAX_FULL_IN_SUMMARY} items for some channels — to nie wszystko."
    # Final sanitization: if client requested full data, ensure available_signals contains
    # only full JSON-friendly arrays/records or truncated objects (no 'sample'/'length' summaries).
    if include_full:
        try:
            import numpy as _np
            import pandas as _pd
        except Exception:
            _np = None
            _pd = None

        def _make_json_full(obj):
            # apply range_slice if present
            obj_use = obj
            if range_slice:
                try:
                    sstart, send = range_slice
                    if _pd is not None and (isinstance(obj, _pd.Series) or isinstance(obj, _pd.DataFrame)):
                        obj_use = obj.iloc[sstart:send]
                    elif isinstance(obj, (list, tuple)):
                        obj_use = list(obj)[sstart:send]
                    elif _np is not None and isinstance(obj, _np.ndarray):
                        obj_use = obj[sstart:send]
                except Exception:
                    obj_use = obj

            # compute length
            slen = None
            try:
                if _pd is not None and (isinstance(obj_use, _pd.Series) or isinstance(obj_use, _pd.DataFrame)):
                    slen = len(obj_use)
                elif isinstance(obj_use, (list, tuple)):
                    slen = len(obj_use)
                elif _np is not None and isinstance(obj_use, _np.ndarray):
                    slen = int(obj_use.shape[0]) if hasattr(obj_use, 'shape') else len(obj_use)
            except Exception:
                slen = None

            try:
                if slen is not None and slen > MAX_FULL_IN_SUMMARY:
                    if _pd is not None and (isinstance(obj_use, _pd.DataFrame) or isinstance(obj_use, _pd.Series)):
                        truncated = obj_use.iloc[:MAX_FULL_IN_SUMMARY].to_dict(orient='records') if hasattr(obj_use, 'to_dict') else list(obj_use.iloc[:MAX_FULL_IN_SUMMARY])
                    elif _np is not None and isinstance(obj_use, _np.ndarray):
                        truncated = obj_use[:MAX_FULL_IN_SUMMARY].tolist()
                    else:
                        truncated = list(obj_use)[:MAX_FULL_IN_SUMMARY]
                    return {'data': truncated, 'truncated': True, 'total_length': slen}

                if _pd is not None and isinstance(obj_use, _pd.DataFrame):
                    return obj_use.to_dict(orient='records')
                if _pd is not None and isinstance(obj_use, _pd.Series):
                    return obj_use.tolist()
                if _np is not None and isinstance(obj_use, _np.ndarray):
                    return obj_use.tolist()
                if isinstance(obj_use, (list, tuple)):
                    return list(obj_use)
                if isinstance(obj_use, dict):
                    out = {}
                    for k, v in obj_use.items():
                        try:
                            out[k] = _make_json_full(v)
                        except Exception:
                            out[k] = str(v)
                    return out
                return str(obj_use)
            except Exception:
                return str(obj_use)

        # Walk available_signals and replace any summary-like dicts
        def _sanitize_signals(sig_tree, raw_tree):
            if isinstance(sig_tree, dict):
                # detect summary dict by presence of 'sample'/'length'/'type' keys
                if any(k in sig_tree for k in ('sample', 'length', 'type', 'sample_rows', 'full', 'full_rows')):
                    # replace with full conversion from raw_tree when possible
                    try:
                        return _make_json_full(raw_tree)
                    except Exception:
                        return sig_tree
                out = {}
                for k, v in sig_tree.items():
                    raw_sub = None
                    try:
                        if isinstance(raw_tree, dict):
                            raw_sub = raw_tree.get(k)
                    except Exception:
                        raw_sub = None
                    # if no corresponding raw, keep existing
                    if raw_sub is None:
                        out[k] = _sanitize_signals(v, raw_sub)
                    else:
                        out[k] = _sanitize_signals(v, raw_sub)
                return out
            else:
                return sig_tree

        try:
            info['available_signals'] = _sanitize_signals(info.get('available_signals', {}), raw_signals)
        except Exception:
            pass
        # Wrap top-level locations (e.g., 'chest', 'wrist') under a 'full' tag so the client
        # receives data consistently as {'full': ...} when full=1 is requested.
        try:
            av = info.get('available_signals', {})
            wrapped = {}
            for loc, val in av.items():
                # if already wrapped, keep as-is
                if isinstance(val, dict) and 'full' in val and len(val) == 1:
                    wrapped[loc] = val
                else:
                    wrapped[loc] = {'full': val}
            info['available_signals'] = wrapped
        except Exception:
            pass
    return jsonify(info)

def discover_subjects_in_file(pkl_path):
    """Zwraca listę subjectów obecnych w pliku .pkl.
    Obsługuje:
      - plik będący jedną strukturą uczestnika (top-level 'subject')
      - dict z kluczami typu 'S2' lub '1'
      - lista słowników z polem 'subject'
      - pandas.DataFrame z kolumną 'subject'
    """
    subjects = set()
    # domyślnie pozwalamy na unpickling; jeśli wywołujący chce zablokować, powinien
    # przekazać allow_unpickle=False (parametr może być dodany później).
    with open(pkl_path, 'rb') as f:
        try:
            container = _safe_pickle_load(f)
        except Exception as e:
            raise RuntimeError(f'Błąd ładowania {os.path.basename(pkl_path)}: {e}')

    # jeśli plik to pojedynczy obiekt uczestnika: top-level 'subject'
    if isinstance(container, dict) and 'subject' in container:
        s = container.get('subject')
        if s is not None:
            return [str(s)]

    # dict: klucze typu 'S1' lub numeryczne, oraz wartości z polem 'subject'
    if isinstance(container, dict):
        for k, v in container.items():
            try:
                ks = str(k)
                # dopasuj dokładnie 'S' + number lub samą liczbę
                if re.match(r'^[sS]\d+$', ks):
                    subjects.add(ks.upper())
                elif re.match(r'^\d+$', ks):
                    subjects.add(f"S{ks}")
            except Exception:
                pass
            try:
                if isinstance(v, dict):
                    s = v.get('subject')
                    if s is not None:
                        subjects.add(str(s))
            except Exception:
                pass

    # lista słowników
    if isinstance(container, (list, tuple)):
        for item in container:
            try:
                if isinstance(item, dict):
                    s = item.get('subject')
                    if s is not None:
                        subjects.add(str(s))
            except Exception:
                pass

    # pandas DataFrame
    try:
        import pandas as _pd
        if isinstance(container, _pd.DataFrame):
            if 'subject' in container.columns:
                vals = container['subject'].unique().tolist()
                for v in vals:
                    subjects.add(str(v))
    except Exception:
        pass

    return sorted(subjects)

@app.route('/participants', methods=['GET'])
def participants_list():
    """Zwraca listę dostępnych uczestników (przeszukuje .pkl w aktualnym katalogu danych).
    Opcjonalnie: ?file=<filename> aby sprawdzić tylko jeden plik.
    """
    # Allow searching across all DATA_DIR_CANDIDATES when requested
    search_all = request.args.get('search_all', '0').lower() in ('1', 'true')
    file_filter = request.args.get('file')

    if search_all:
        subjects_by_file = {}
        files_list = []
        for cand in DATA_DIR_CANDIDATES:
            cand_path = cand if os.path.isabs(cand) else os.path.join(BASE_DIR, cand)
            if not os.path.isdir(cand_path):
                continue
            pkls = glob.glob(os.path.join(cand_path, '*.pkl'))
            if file_filter:
                pkls = [p for p in pkls if os.path.basename(p) == file_filter or p == file_filter]
            for p in sorted(pkls):
                key = f"{os.path.basename(cand_path)}/{os.path.basename(p)}"
                files_list.append(key)
                try:
                    subjects = discover_subjects_in_file(p)
                    subjects_by_file[key] = subjects
                except Exception as e:
                    subjects_by_file[key] = {'error': str(e)}

        if not files_list:
            return jsonify({'data_dir_candidates': DATA_DIR_CANDIDATES, 'files': [], 'subjects_by_file': {}, 'note': 'Brak plików .pkl w żadnym z katalogów'}), 200

        if not _is_unpickle_allowed():
            return jsonify({'data_dir_candidates': DATA_DIR_CANDIDATES, 'files': files_list, 'subjects_by_file': {}, 'note': 'Unpickling jest wyłączony. Ustaw ALLOW_UNPICKLE=1 lub dodaj allow_unpickle=1 by zobaczyć subjecty.'})

        return jsonify({'data_dir_candidates': DATA_DIR_CANDIDATES, 'files': files_list, 'subjects_by_file': subjects_by_file})

    # default: search only current data_dir
    data_dir = get_data_dir()
    if not os.path.isdir(data_dir):
        return jsonify({'error': f'Katalog danych nie istnieje: {data_dir}'}), 400

    all_pkls = glob.glob(os.path.join(data_dir, '*.pkl'))
    if file_filter:
        # dopasuj nazwę pliku dokładnie lub basename
        matches = [p for p in all_pkls if os.path.basename(p) == file_filter or p == file_filter]
        all_pkls = matches

    if not all_pkls:
        return jsonify({'data_dir': data_dir, 'files': [], 'subjects_by_file': {}, 'note': 'Brak plików .pkl w katalogu'}), 200

    # jeśli unpickling jest wyłączony — zwróć tylko listę plików i informację
    if not _is_unpickle_allowed():
        return jsonify({
            'data_dir': data_dir,
            'files': sorted([os.path.basename(p) for p in all_pkls]),
            'subjects_by_file': {},
            'note': 'Unpickling jest wyłączony. Ustaw ALLOW_UNPICKLE=1 lub dodaj allow_unpickle=1 by zobaczyć subjecty.'
        })

    subjects_by_file = {}
    for p in sorted(all_pkls):
        try:
            subjects = discover_subjects_in_file(p)
            subjects_by_file[os.path.basename(p)] = subjects
        except Exception as e:
            subjects_by_file[os.path.basename(p)] = {'error': str(e)}

    return jsonify({
        'data_dir': data_dir,
        'files': sorted([os.path.basename(p) for p in all_pkls]),
        'subjects_by_file': subjects_by_file
    })

def _find_default_subject():
    """Spróbuje automatycznie znaleźć jedynego uczestnika w aktualnym katalogu danych.
    Zwraca (subject_str, None) lub (None, info) — info to komunikat lub dict z wykrytymi subjectami.
    """
    data_dir = get_data_dir()
    if not os.path.isdir(data_dir):
        return None, 'Katalog danych nie istnieje'
    pkls = glob.glob(os.path.join(data_dir, '*.pkl'))
    if not pkls:
        return None, 'Brak plików .pkl w katalogu'

    subjects = set()
    subjects_by_file = {}
    for p in pkls:
        try:
            subs = discover_subjects_in_file(p)
        except Exception:
            subs = []
        subjects_by_file[os.path.basename(p)] = subs
        for s in subs:
            subjects.add(s)

    # jeśli dokładnie jeden subject — zwróć go
    if len(subjects) == 1:
        return next(iter(subjects)), None

    # jeśli nie znaleziono subjectów, ale jest tylko jeden plik .pkl — użyj nazwy pliku (bez rozszerzenia)
    if not subjects and len(pkls) == 1:
        fn = os.path.splitext(os.path.basename(pkls[0]))[0]
        if fn:
            return fn, None

    return None, {'note': 'wiele_subjectów', 'subjects_by_file': subjects_by_file}


def _get_chat_api_key():
    """Pobiera klucz API dla usługi czatu.

    Kolejność:
      1) zmienna środowiskowa OPENAI_API_KEY
      2) plik `chat_key.txt` w katalogu projektu (BASE_DIR) — jeśli istnieje, odczytaj pierwszą linię
      3) None jeśli brak klucza
    """
    key = os.environ.get('OPENAI_API_KEY')
    if key:
        return key
    # spróbuj odczytać plik chat_key.txt w katalogu projektu
    try:
        p = os.path.join(BASE_DIR, 'chat_key.txt')
        if os.path.isfile(p):
            with open(p, 'r', encoding='utf-8') as f:
                line = f.readline().strip()
                if line:
                    return line
    except Exception:
        pass
    return None


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Prosty proxy do OpenAI (chat completions). Oczekuje JSON { message: str }.

    Zwraca JSON { reply: str } lub odpowiedni kod błędu.
    Uwaga: trzymanie klucza po stronie serwera jest bezpieczniejsze niż w front-endzie.
    """
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({'error': 'Niepoprawny JSON w ciele żądania.'}), 400

    if not payload or 'message' not in payload:
        return jsonify({'error': "Oczekiwany JSON: { 'message': '...' }"}), 400

    user_message = str(payload.get('message', '')).strip()
    if not user_message:
        return jsonify({'error': 'Pusta wiadomość'}), 400

    # opcjonalne parametry modelu/temperatury z payload
    requested_model = str(payload.get('model', '')).strip() or None
    requested_temperature = payload.get('temperature', None)
    requested_max_tokens = payload.get('max_tokens', None)
    # opcjonalna rola/system prompt
    assistant_role = payload.get('assistant_role')
    custom_system = payload.get('system')

    api_key = _get_chat_api_key()
    if not api_key:
        return jsonify({'error': 'Brak klucza API. Ustaw OPENAI_API_KEY lub utwórz chat_key.txt w katalogu projektu.'}), 500

    # przygotuj zapytanie do OpenAI Chat Completions z walidacją parametrów
    ALLOWED_MODELS = ['gpt-3.5-turbo', 'gpt-4', 'gpt-5-pro']
    # model default
    model = 'gpt-3.5-turbo'
    if requested_model:
        if requested_model in ALLOWED_MODELS:
            model = requested_model
        else:
            return jsonify({'error': f'Nieznany model: {requested_model}', 'allowed_models': ALLOWED_MODELS}), 400

    # temperature: float 0.0..2.0
    temperature = 0.6
    try:
        if requested_temperature is not None:
            temperature = float(requested_temperature)
            if not (0.0 <= temperature <= 2.0):
                raise ValueError('temperature must be between 0.0 and 2.0')
    except Exception as e:
        return jsonify({'error': f'Niepoprawna temperatura: {e}'}), 400

    # max_tokens: int, pozytywna, model-specific limit
    # dopuszczalne limity (bezpieczeństwo): ustawienia przybliżone
    MODEL_MAX_TOKENS = {
        'gpt-3.5-turbo': 2000,
        'gpt-4': 8000,
        'gpt-5-pro': 32768,
    }
    model_cap = MODEL_MAX_TOKENS.get(model, 2000)
    max_tokens = 500
    try:
        if requested_max_tokens is not None:
            max_tokens = int(requested_max_tokens)
            if max_tokens <= 0 or max_tokens > model_cap:
                raise ValueError(f'max_tokens musi być w zakresie 1..{model_cap} dla modelu {model}')
    except Exception as e:
        return jsonify({'error': f'Niepoprawny max_tokens: {e}'}), 400

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    # przygotuj role/system messages
    ASSISTANT_ROLE_PRESETS = {
        'care_assistant': (
            "You are a caring assistant specialized in supporting caregivers of autistic patients. "
            "Answer concisely, using calm, respectful language. Provide practical, evidence-informed suggestions for caregiving, "
            "sensory regulation, communication strategies and safety. When giving advice, explain briefly why and give one concrete next step. "
            "Do NOT provide medical diagnoses or replace professional medical advice; when appropriate, recommend consulting a qualified clinician."
        ),
        'default': (
            "You are a helpful assistant. Reply politely and helpfully."
        )
    }

    system_message = None
    # if assistant_role provided and matches preset, use preset
    if assistant_role:
        if assistant_role in ASSISTANT_ROLE_PRESETS:
            system_message = ASSISTANT_ROLE_PRESETS[assistant_role]
        else:
            # unknown role -> error
            return jsonify({'error': f'Nieznana rola assistant_role: {assistant_role}', 'allowed_roles': list(ASSISTANT_ROLE_PRESETS.keys())}), 400
    # override with explicit custom system prompt if given
    if custom_system:
        try:
            cs = str(custom_system)
            if len(cs) > 4000:
                return jsonify({'error': 'Custom system prompt jest za długi (limit 4000 znaków).'}), 400
            system_message = cs
        except Exception:
            return jsonify({'error': 'Niepoprawny system prompt.'}), 400

    # build messages list: if system_message present, include as first message with role 'system'
    messages = []
    if system_message:
        messages.append({'role': 'system', 'content': system_message})
    messages.append({'role': 'user', 'content': user_message})

    body = {
        'model': model,
        'messages': messages,
        'max_tokens': max_tokens,
        'temperature': temperature,
    }

    try:
        # Some models (eg. gpt-5-pro) require the newer Responses API (/v1/responses)
        RESPONSES_MODELS = {'gpt-5-pro'}
        if model in RESPONSES_MODELS:
            # Responses API expects 'input' (string or array) and uses 'max_output_tokens' instead of 'max_tokens'.
            # Some newer models (like gpt-5-pro) don't accept parameters such as 'temperature' here —
            # to avoid invalid_request_error we omit unsupported tuning params and only send the core fields.
            body_resp = {
                'model': model,
                'input': (system_message + "\n\n" + user_message) if system_message else user_message,
                'max_output_tokens': max_tokens,
            }
            if requests is not None:
                resp = requests.post('https://api.openai.com/v1/responses', headers=headers, json=body_resp, timeout=30)
                if resp.status_code != 200:
                    try:
                        return jsonify({'error': 'Błąd od OpenAI', 'details': resp.text}), resp.status_code
                    except Exception:
                        return jsonify({'error': 'Błąd od OpenAI', 'status': resp.status_code}), resp.status_code
                data = resp.json()
            else:
                import urllib.request as _ur
                req = _ur.Request('https://api.openai.com/v1/responses', data=json.dumps(body_resp).encode('utf-8'), headers=headers)
                with _ur.urlopen(req, timeout=30) as r:
                    raw = r.read().decode('utf-8')
                data = json.loads(raw)
        else:
            # Chat completions endpoint for chat-style models
            if requests is not None:
                resp = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=body, timeout=15)
                if resp.status_code != 200:
                    try:
                        return jsonify({'error': 'Błąd od OpenAI', 'details': resp.text}), resp.status_code
                    except Exception:
                        return jsonify({'error': 'Błąd od OpenAI', 'status': resp.status_code}), resp.status_code
                data = resp.json()
            else:
                # fallback na urllib jeśli requests nie jest zainstalowany
                import urllib.request as _ur
                req = _ur.Request('https://api.openai.com/v1/chat/completions', data=json.dumps(body).encode('utf-8'), headers=headers)
                with _ur.urlopen(req, timeout=15) as r:
                    raw = r.read().decode('utf-8')
                data = json.loads(raw)

        # parsuj odpowiedź — obsłuż zarówno chat/completions jak i responses API
        reply = None
        try:
            # Chat completions (choices -> message -> content)
            if isinstance(data, dict) and 'choices' in data:
                choices = data.get('choices')
                if choices and len(choices) > 0:
                    first = choices[0]
                    if isinstance(first, dict):
                        msg = first.get('message')
                        if isinstance(msg, dict):
                            # content może być string albo dict
                            content = msg.get('content')
                            if isinstance(content, str):
                                reply = content
                            elif isinstance(content, dict):
                                # czasem content ma pole 'content' lub 'text'
                                reply = content.get('text') or content.get('content')
                        else:
                            # fallback: join text fields
                            reply = first.get('text') or None

            # Responses API (output -> list -> content -> text)
            if not reply and isinstance(data, dict) and 'output' in data:
                out = data.get('output')
                if isinstance(out, list) and len(out) > 0:
                    parts = []
                    for item in out:
                        if isinstance(item, dict):
                            content = item.get('content')
                            if isinstance(content, list):
                                for c in content:
                                    # c może mieć 'text' lub 'type'/'text'
                                    if isinstance(c, dict):
                                        if 'text' in c:
                                            parts.append(c.get('text'))
                                        elif 'type' in c and c.get('type') == 'output_text' and 'text' in c:
                                            parts.append(c.get('text'))
                                    elif isinstance(c, str):
                                        parts.append(c)
                            elif isinstance(content, str):
                                parts.append(content)
                    if parts:
                        reply = "\n".join([p for p in parts if p])

            # fallbacky: check common keys
            if not reply and isinstance(data, dict):
                if 'reply' in data:
                    reply = data.get('reply')
                elif 'message' in data and isinstance(data.get('message'), str):
                    reply = data.get('message')

        except Exception:
            reply = None

        if not reply:
            # ostatnia deska ratunku: zamień cały obiekt JSON na string (skrót)
            try:
                reply = json.dumps(data)[:2000]
            except Exception:
                reply = str(data)[:2000]

        return jsonify({'reply': reply})
    except Exception as e:
        return jsonify({'error': 'Błąd podczas wysyłania żądania do API czatu', 'details': str(e)}), 500

@app.route('/participant', methods=['GET'])
def participant_auto():
    """Zwraca dane jedynego uczestnika lub dla podanego ?subject=.
    Jeśli subject zaczyna się od 'S' (np. S2) — można podać pełną nazwę.
    """
    # najpierw parametr subject
    subj = request.args.get('subject')
    if not subj:
        subj, info = _find_default_subject()
        if not subj:
            return jsonify({'error': 'Nie można automatycznie wykryć uczestnika', 'info': info}), 400

    # normalizuj subject dla load_participant_data:
    # jeśli podano 'S2' -> przekaż '2' (load_participant_data tworzy 'S{subject_id}')
    if isinstance(subj, str) and subj.upper().startswith('S') and subj[1:].isdigit():
        subject_id = subj[1:]
    else:
        subject_id = subj

    # użyj istniejącej funkcji zwracającej szczegóły (ponownie skorzystamy z istniejącego route handlera)
    return get_participant_info(str(subject_id))


@app.route('/api/stress_state', methods=['GET'])
def api_stress_state():
    """Zwraca stan stresu dla wybranego uczestnika oraz (opcjonalnie) prostą historię.

    Query params:
      - subject: np. S2 lub 2 (opcjonalne; gdy brak spróbujemy autodetekcji)
      - range: "start:end" (indeksy próbek, opcjonalne) – dotyczy wszystkich kanałów
      - windows: liczba okien do historii (np. 20). Jeśli >0, policzymy historię.
      - window_size: rozmiar okna w próbkach (np. 500). Domyślnie 300.
      - allow_unpickle=1: wymagane jeśli unpickling nie włączony env-em
    """
    # bezpieczeństwo unpicklingu jak w innych endpointach
    if not _is_unpickle_allowed():
        return jsonify({'error': 'Unpickling jest wyłączony. Ustaw ALLOW_UNPICKLE=1 lub dodaj allow_unpickle=1.'}), 403

    subj = request.args.get('subject')
    if not subj:
        subj, info = _find_default_subject()
        if not subj:
            return jsonify({'error': 'Nie można automatycznie wykryć uczestnika', 'info': info}), 400

    # normalizuj subject (S2 -> 2)
    if isinstance(subj, str) and subj.upper().startswith('S') and subj[1:].isdigit():
        subject_id = subj[1:]
    else:
        subject_id = subj

    # range
    range_spec = request.args.get('range')
    sstart = send = None
    if range_spec:
        try:
            parts = range_spec.split(':')
            if len(parts) == 2:
                sstart = int(parts[0]) if parts[0] != '' else None
                send = int(parts[1]) if parts[1] != '' else None
        except Exception:
            sstart = send = None

    def _slice_seq(obj, start=None, end=None):
        try:
            import numpy as _np
            import pandas as _pd
        except Exception:
            _np = None
            _pd = None
        try:
            if start is None and end is None:
                return obj
            if _pd is not None and (isinstance(obj, _pd.Series) or isinstance(obj, _pd.DataFrame)):
                return obj.iloc[start:end]
            if isinstance(obj, (list, tuple)):
                return list(obj)[start:end]
            if _np is not None and isinstance(obj, _np.ndarray):
                return obj[start:end]
            return obj
        except Exception:
            return obj

    try:
        data = load_participant_data(str(subject_id))
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    raw_signals = data.get('signal', data)

    # jeśli mamy range – przytnij wartości w raw_signals (rekurencyjnie po kanałach)
    if sstart is not None or send is not None:
        try:
            if isinstance(raw_signals, dict):
                clipped = {}
                for loc, loc_val in raw_signals.items():
                    if isinstance(loc_val, dict):
                        clipped[loc] = {ch: _slice_seq(ch_val, sstart, send) for ch, ch_val in loc_val.items()}
                    else:
                        clipped[loc] = _slice_seq(loc_val, sstart, send)
                raw_signals = clipped
        except Exception:
            pass

    # oblicz metryki bieżące
    feats = _extract_features_from_signals(raw_signals)
    state = classify(feats)

    # policz prosty wynik (0-100) jako odsetek warunków stresu spełnionych
    stress_conditions = [
        feats.get('mean_eda') is not None and feats['mean_eda'] > 0.761343,
        feats.get('hr') is not None and feats['hr'] > 66.870546,
        feats.get('hrv') is not None and feats['hrv'] < 325.906461,
        feats.get('temp') is not None and feats['temp'] < 31.217497,
        feats.get('acc_rms') is not None and feats['acc_rms'] > 1.015106,
    ]
    known = [c for c in stress_conditions if c is True or c is False]
    score = None
    if known:
        score = int(round(100 * (sum(1 for c in known if c) / len(known))))

    # historia (opcjonalnie)
    try:
        windows = int(request.args.get('windows', 0))
    except Exception:
        windows = 0
    try:
        window_size = int(request.args.get('window_size', 300))
    except Exception:
        window_size = 300

    history = []
    if windows and isinstance(raw_signals, dict):
        # znajdź długość na bazie pierwszego dostępnego kanału
        def _first_len(d):
            try:
                import numpy as _np
                import pandas as _pd
            except Exception:
                _np = None
                _pd = None
            for v in d.values():
                if isinstance(v, dict):
                    l = _first_len(v)
                    if l:
                        return l
                else:
                    try:
                        if _pd is not None and (isinstance(v, _pd.Series) or isinstance(v, _pd.DataFrame)):
                            return len(v)
                        if isinstance(v, (list, tuple)):
                            return len(v)
                        if _np is not None and isinstance(v, _np.ndarray):
                            return int(v.shape[0]) if hasattr(v, 'shape') else len(v)
                    except Exception:
                        pass
            return None

        total_len = _first_len(raw_signals)
        if total_len and total_len > 0:
            end_idx = total_len
            start_idx = max(0, end_idx - windows * window_size)
            # iteruj po oknach
            idx = start_idx
            while idx + window_size <= end_idx:
                # przytnij i policz cechy
                try:
                    # zbuduj clipped wersję dla okna [idx:idx+window_size]
                    clipped = {}
                    for loc, lv in raw_signals.items():
                        if isinstance(lv, dict):
                            clipped[loc] = {ch: _slice_seq(chv, idx, idx + window_size) for ch, chv in lv.items()}
                        else:
                            clipped[loc] = _slice_seq(lv, idx, idx + window_size)
                    f = _extract_features_from_signals(clipped)
                    conds = [
                        f.get('mean_eda') is not None and f['mean_eda'] > 0.761343,
                        f.get('hr') is not None and f['hr'] > 66.870546,
                        f.get('hrv') is not None and f['hrv'] < 325.906461,
                        f.get('temp') is not None and f['temp'] < 31.217497,
                        f.get('acc_rms') is not None and f['acc_rms'] > 1.015106,
                    ]
                    known2 = [c for c in conds if c is True or c is False]
                    sc = None
                    if known2:
                        sc = int(round(100 * (sum(1 for c in known2 if c) / len(known2))))
                except Exception:
                    sc = None
                history.append({'start': idx, 'end': idx + window_size, 'score': sc})
                idx += window_size

    # trend w oparciu o historię, jeśli dostępna
    trend = None
    if score is not None and len(history) >= 2:
        prev_scores = [h.get('score') for h in history if h.get('score') is not None]
        if len(prev_scores) >= 2:
            diff = prev_scores[-1] - prev_scores[-2]
            if diff > 5:
                trend = 'wzrost'
            elif diff < -5:
                trend = 'spadek'
            else:
                trend = 'stabilny'

    result = {
        'subject': subj if isinstance(subj, str) and subj.upper().startswith('S') else f"S{subject_id}",
        'features': feats,
        'state': state,
        'score': score,
        'trend': trend,
        'history': history,
        'generated_at': datetime.utcnow().isoformat() + 'Z'
    }
    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True)
# uruchom serwer Flask