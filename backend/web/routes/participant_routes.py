import glob
import json
import os
from flask import Blueprint, jsonify, request

from backend.utils import _json_error, _parse_bool, _parse_int, _summarize_object
from backend.web.context import AppContext
from backend.web.security import is_unpickle_allowed


def create_participant_blueprint(ctx: AppContext) -> Blueprint:
    cache = ctx.cache
    max_full_in_summary = ctx.max_full_in_summary
    bp = Blueprint('participants', __name__)

    @bp.route('/participant/<subject_id>', methods=['GET'])
    def get_participant_info(subject_id):
        n = _parse_int(request.args.get('n'), default=20)
        include_full = _parse_bool(request.args.get('full'), default=False)
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

        if not is_unpickle_allowed():
            return _json_error('Unpickling jest wyłączony. Ustaw zmienną środowiskową ALLOW_UNPICKLE=1 lub dodaj query param allow_unpickle=1.', status=403)

        cache_key = None
        if cache:
            try:
                cache_key = json.dumps({
                    'sid': subject_id,
                    'n': n,
                    'full': include_full,
                    'range': range_spec,
                    'params': request.args.get('params')
                }, sort_keys=True)
                cached_info = cache.get(f"participant_resp:{cache_key}")
                if cached_info is not None:
                    return jsonify(cached_info)
            except Exception:
                cache_key = None

        try:
            def _load():
                return ctx.load_participant_data(subject_id)
            if cache:
                data = cache.get_or_set(f"participant_raw:{subject_id}", _load, ttl=60.0)
            else:
                data = _load()
        except FileNotFoundError as e:
            return _json_error(str(e), status=404)
        except Exception as e:
            return _json_error(str(e), status=500)

        subject = None
        try:
            subject = data.get('subject', f'S{subject_id}')
        except Exception:
            subject = f'S{subject_id}'

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
            raw_signals = data

        found_params = set()
        requested_params_json = None

        if isinstance(raw_signals, dict):
            for loc, loc_val in raw_signals.items():
                if isinstance(loc_val, dict):
                    signals[loc] = {}
                    for ch_name, ch_val in loc_val.items():
                        key_lower = str(ch_name).lower()
                        if requested_params and key_lower not in requested_params:
                            continue
                        per_n = requested_params.get(key_lower) if requested_params.get(key_lower) is not None else n
                        if range_slice:
                            sstart, send = range_slice
                            try:
                                import pandas as _pd
                                import numpy as _np
                                if isinstance(ch_val, _pd.Series) or isinstance(ch_val, _pd.DataFrame):
                                    ch_val_s = ch_val.iloc[sstart:send]
                                    try:
                                        slen = len(ch_val_s)
                                    except Exception:
                                        slen = None
                                    show_full = include_full or (slen is not None and slen <= max_full_in_summary)
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
                                    show_full = include_full or (slen is not None and slen <= max_full_in_summary)
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
                                    show_full = include_full or (slen is not None and slen <= max_full_in_summary)
                                    per_n_use = slen if (slen is not None and show_full) else per_n
                                    signals[loc][ch_name] = _summarize_object(ch_val_s, n=per_n_use, include_full=show_full)
                                    found_params.add(key_lower)
                                    continue
                            except Exception:
                                pass
                        try:
                            import numpy as _np
                            import pandas as _pd
                        except Exception:
                            _np = None
                            _pd = None

                        def _to_jsonable(obj):
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
                                    out = {}
                                    for k, v in obj.items():
                                        try:
                                            out[k] = _to_jsonable(v)
                                        except Exception:
                                            out[k] = str(v)
                                    return out
                            except Exception:
                                pass
                            try:
                                return str(obj)
                            except Exception:
                                return None

                        if include_full:
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

                            if slen is not None and slen > max_full_in_summary:
                                try:
                                    if _pd is not None and (isinstance(ch_val_use, _pd.Series) or isinstance(ch_val_use, _pd.DataFrame)):
                                        truncated = ch_val_use.iloc[:max_full_in_summary].to_dict(orient='records') if hasattr(ch_val_use, 'to_dict') else list(ch_val_use.iloc[:max_full_in_summary])
                                    elif _np is not None and isinstance(ch_val_use, _np.ndarray):
                                        truncated = ch_val_use[:max_full_in_summary].tolist()
                                    else:
                                        truncated = list(ch_val_use)[:max_full_in_summary]
                                except Exception:
                                    truncated = _to_jsonable(ch_val_use)[:max_full_in_summary] if isinstance(_to_jsonable(ch_val_use), list) else _to_jsonable(ch_val_use)
                                signals[loc][ch_name] = {'data': truncated, 'truncated': True, 'total_length': slen}
                                truncated_channels.append(f"{loc}/{ch_name}")
                            else:
                                signals[loc][ch_name] = _to_jsonable(ch_val_use)
                        else:
                            signals[loc][ch_name] = _summarize_object(ch_val, n=per_n, include_full=include_full)
                        found_params.add(key_lower)
                else:
                    if requested_params and str(loc).lower() not in requested_params:
                        continue
                    per_n = requested_params.get(str(loc).lower()) if requested_params.get(str(loc).lower()) is not None else n
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
                                show_full = include_full or (slen is not None and slen <= max_full_in_summary)
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
                                show_full = include_full or (slen is not None and slen <= max_full_in_summary)
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
                                show_full = include_full or (slen is not None and slen <= max_full_in_summary)
                                per_n_use = slen if (slen is not None and show_full) else per_n
                                signals[loc] = _summarize_object(loc_val_s, n=per_n_use, include_full=show_full)
                                found_params.add(str(loc).lower())
                                continue
                        except Exception:
                            pass
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

                        if slen is not None and slen > max_full_in_summary:
                            try:
                                if _pd is not None and (isinstance(loc_val_use, _pd.DataFrame) or isinstance(loc_val_use, _pd.Series)):
                                    truncated = loc_val_use.iloc[:max_full_in_summary].to_dict(orient='records') if hasattr(loc_val_use, 'to_dict') else list(loc_val_use.iloc[:max_full_in_summary])
                                elif _np is not None and isinstance(loc_val_use, _np.ndarray):
                                    truncated = loc_val_use[:max_full_in_summary].tolist()
                                else:
                                    truncated = list(loc_val_use)[:max_full_in_summary]
                            except Exception:
                                truncated = _to_jsonable_loc(loc_val_use)
                                if isinstance(truncated, list):
                                    truncated = truncated[:max_full_in_summary]
                            signals[loc] = {'data': truncated, 'truncated': True, 'total_length': slen}
                            truncated_channels.append(loc)
                        else:
                            signals[loc] = _to_jsonable_loc(loc_val_use)
                    else:
                        signals[loc] = _summarize_object(loc_val, n=per_n, include_full=include_full)
                    found_params.add(str(loc).lower())
        else:
            if requested_params:
                signals = {}
            else:
                signals = {'signal_container': _summarize_object(raw_signals, n=n, include_full=include_full)}

        if include_full:
            def _convert_and_maybe_truncate(obj):
                try:
                    import numpy as _np
                    import pandas as _pd
                except Exception:
                    _np = None
                    _pd = None

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
                    if slen is not None and slen > max_full_in_summary:
                        if _pd is not None and (isinstance(obj_use, _pd.DataFrame) or isinstance(obj_use, _pd.Series)):
                            truncated = obj_use.iloc[:max_full_in_summary].to_dict(orient='records') if hasattr(obj_use, 'to_dict') else list(obj_use.iloc[:max_full_in_summary])
                        elif _np is not None and isinstance(obj_use, _np.ndarray):
                            truncated = obj_use[:max_full_in_summary].tolist()
                        else:
                            truncated = list(obj_use)[:max_full_in_summary]
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
                                out[k] = _convert_and_maybe_truncate(v)
                            except Exception:
                                out[k] = str(v)
                        return out
                    return str(obj_use)
                except Exception:
                    return str(obj_use)

            signals = {}
            found_params = set()
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
                            if requested_params and key_lower in requested_params:
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
                signals = {'signal_container': _convert_and_maybe_truncate(raw_signals)}
                if requested_params:
                    for p in requested_params.keys():
                        requested_params_json.setdefault(p, signals['signal_container'])
        missing_params = []
        if requested_params:
            for p in requested_params.keys():
                if p not in found_params:
                    missing_params.append(p)

        labels_sample = []
        try:
            labels = data.get('label', [])
            try:
                labels_sample = _summarize_object(labels, n=n, include_full=False).get('sample', [])
            except Exception:
                labels_sample = []
        except Exception:
            labels_sample = []

        metadata = {}
        try:
            for k, v in getattr(data, 'items', lambda: {})():
                if k in ('subject', 'signal', 'label'):
                    continue
                try:
                    metadata[k] = {'type': type(v).__name__, 'preview': _summarize_object(v, n=5, include_full=False).get('sample')}
                except Exception:
                    metadata[k] = {'type': type(v).__name__}
        except Exception:
            pass

        info = {
            'subject': subject,
            'available_signals': signals,
            'labels_sample': labels_sample,
            'metadata_preview': metadata
        }
        if requested_params_json:
            info['requested_params'] = requested_params_json
        if truncated_channels:
            info['truncated_channels'] = truncated_channels
            info['note'] = f"Returned first {max_full_in_summary} items for some channels — to nie wszystko."

        if include_full:
            try:
                import numpy as _np
                import pandas as _pd
            except Exception:
                _np = None
                _pd = None

            def _make_json_full(obj):
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
                    if slen is not None and slen > max_full_in_summary:
                        if _pd is not None and (isinstance(obj_use, _pd.DataFrame) or isinstance(obj_use, _pd.Series)):
                            truncated = obj_use.iloc[:max_full_in_summary].to_dict(orient='records') if hasattr(obj_use, 'to_dict') else list(obj_use.iloc[:max_full_in_summary])
                        elif _np is not None and isinstance(obj_use, _np.ndarray):
                            truncated = obj_use[:max_full_in_summary].tolist()
                        else:
                            truncated = list(obj_use)[:max_full_in_summary]
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

            def _sanitize_signals(sig_tree, raw_tree):
                if isinstance(sig_tree, dict):
                    if any(k in sig_tree for k in ('sample', 'length', 'type', 'sample_rows', 'full', 'full_rows')):
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
            try:
                av = info.get('available_signals', {})
                wrapped = {}
                for loc, val in av.items():
                    if isinstance(val, dict) and 'full' in val and len(val) == 1:
                        wrapped[loc] = val
                    else:
                        wrapped[loc] = {'full': val}
                info['available_signals'] = wrapped
            except Exception:
                pass
        try:
            if cache and cache_key is not None:
                cache.set(f"participant_resp:{cache_key}", info, ttl=30.0)
        except Exception:
            pass
        return jsonify(info)

    @bp.route('/participants', methods=['GET'])
    def participants_list():
        search_all = _parse_bool(request.args.get('search_all'), default=False)
        file_filter = request.args.get('file')

        if search_all:
            subjects_by_file = {}
            files_list = []
            for cand in ctx.data_dir_candidates:
                cand_path = cand if os.path.isabs(cand) else os.path.join(ctx.base_dir, cand)
                if not os.path.isdir(cand_path):
                    continue
                pkls = glob.glob(os.path.join(cand_path, '*.pkl'))
                if file_filter:
                    pkls = [p for p in pkls if os.path.basename(p) == file_filter or p == file_filter]
                for p in sorted(pkls):
                    key = f"{os.path.basename(cand_path)}/{os.path.basename(p)}"
                    files_list.append(key)
                    try:
                        subjects = ctx.discover_subjects_in_file(p)
                        subjects_by_file[key] = subjects
                    except Exception as e:
                        subjects_by_file[key] = {'error': str(e)}

            if not files_list:
                return jsonify({'data_dir_candidates': ctx.data_dir_candidates, 'files': [], 'subjects_by_file': {}, 'note': 'Brak plików .pkl w żadnym z katalogów'}), 200

            if not is_unpickle_allowed():
                return jsonify({'data_dir_candidates': ctx.data_dir_candidates, 'files': files_list, 'subjects_by_file': {}, 'note': 'Unpickling jest wyłączony. Ustaw ALLOW_UNPICKLE=1 lub dodaj allow_unpickle=1 by zobaczyć subjecty.'})

            return jsonify({'data_dir_candidates': ctx.data_dir_candidates, 'files': files_list, 'subjects_by_file': subjects_by_file})

        data_dir = ctx.get_data_dir()
        if not os.path.isdir(data_dir):
            return _json_error(f'Katalog danych nie istnieje: {data_dir}', status=400)

        def _list_pkls():
            return glob.glob(os.path.join(data_dir, '*.pkl'))
        if cache:
            all_pkls = cache.get_or_set(f"pkls:{data_dir}", _list_pkls, ttl=10.0)
        else:
            all_pkls = _list_pkls()
        if file_filter:
            matches = [p for p in all_pkls if os.path.basename(p) == file_filter or p == file_filter]
            all_pkls = matches

        if not all_pkls:
            return jsonify({'data_dir': data_dir, 'files': [], 'subjects_by_file': {}, 'note': 'Brak plików .pkl w katalogu'}), 200

        if not is_unpickle_allowed():
            return jsonify({
                'data_dir': data_dir,
                'files': sorted([os.path.basename(p) for p in all_pkls]),
                'subjects_by_file': {},
                'note': 'Unpickling jest wyłączony. Ustaw ALLOW_UNPICKLE=1 lub dodaj allow_unpickle=1 by zobaczyć subjecty.'
            })

        subjects_by_file = {}
        for p in sorted(all_pkls):
            try:
                if cache:
                    subjects = cache.get_or_set(f"subjects:{p}", lambda: ctx.discover_subjects_in_file(p), ttl=30.0)
                else:
                    subjects = ctx.discover_subjects_in_file(p)
                subjects_by_file[os.path.basename(p)] = subjects
            except Exception as e:
                subjects_by_file[os.path.basename(p)] = {'error': str(e)}

        return jsonify({
            'data_dir': data_dir,
            'files': sorted([os.path.basename(p) for p in all_pkls]),
            'subjects_by_file': subjects_by_file
        })

    @bp.route('/participant', methods=['GET'])
    def participant_auto():
        subj = request.args.get('subject')
        if not subj:
            subj, info = ctx.find_default_subject()
            if not subj:
                return _json_error('Nie można automatycznie wykryć uczestnika', status=400, info=info)

        if isinstance(subj, str) and subj.upper().startswith('S') and subj[1:].isdigit():
            subject_id = subj[1:]
        else:
            subject_id = subj

        return get_participant_info(str(subject_id))

    return bp
