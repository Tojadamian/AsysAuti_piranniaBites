from flask import Flask, jsonify, request
import pandas as pd
import pickle
import os
import glob
import re

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# globalnie ustawiany katalog danych (można zmienić przez /data_dir?dir=)
CURRENT_DATA_DIR = None

# Ścieżki do katalogów z danymi (najpierw 'data_wesad', jeśli brak — 'S2')
DATA_DIR_CANDIDATES = ['S2', 'S3']

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
    try:
        raw_signals = data.get('signal', {})
    except Exception:
        raw_signals = data  # czasem cały obiekt to sygnały

    found_params = set()

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
                    signals[loc][ch_name] = _summarize_object(ch_val, n=per_n, include_full=include_full)
                    found_params.add(key_lower)
            else:
                # pojedynczy obiekt pod 'chest' np. DataFrame/ndarray
                # Jeśli podano filtrowanie, spróbuj dopasować nazwę lokacji jako parametr
                if requested_params and str(loc).lower() not in requested_params:
                    continue
                per_n = requested_params.get(str(loc).lower()) if requested_params.get(str(loc).lower()) is not None else n
                signals[loc] = _summarize_object(loc_val, n=per_n, include_full=include_full)
                found_params.add(str(loc).lower())
    else:
        # raw_signals nie jest dict — zrób proste podsumowanie całego obiektu
        # jeśli podano parametry i żadna pasuje, zostaw puste
        if requested_params:
            signals = {}
        else:
            signals = {'signal_container': _summarize_object(raw_signals, n=n, include_full=include_full)}

    # lista żądanych, ale niewykrytych parametrów
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
    data_dir = get_data_dir()
    if not os.path.isdir(data_dir):
        return jsonify({'error': f'Katalog danych nie istnieje: {data_dir}'}), 400

    file_filter = request.args.get('file')
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


if __name__ == '__main__':
    app.run(debug=True)
# uruchom serwer Flask