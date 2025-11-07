import os
import numpy as np
import pandas as pd
import pytest

import app


def test_get_data_dir_with_current(tmp_path, monkeypatch):
    # CURRENT_DATA_DIR powinien być użyty jeśli istnieje
    monkeypatch.setattr(app, 'CURRENT_DATA_DIR', str(tmp_path))
    res = app.get_data_dir()
    assert res == str(tmp_path)


def test_get_data_dir_candidates(tmp_path, monkeypatch):
    # stwórz katalog S2 pod tmp_path i przetestuj że get_data_dir go wykryje
    s2 = tmp_path / 'S2'
    s2.mkdir()
    monkeypatch.setattr(app, 'CURRENT_DATA_DIR', None)
    monkeypatch.setattr(app, 'BASE_DIR', str(tmp_path))
    monkeypatch.setattr(app, 'DATA_DIR_CANDIDATES', ['S2', 'S3'])
    res = app.get_data_dir()
    assert os.path.normpath(res) == os.path.normpath(str(s2))


def test_summarize_list():
    data = list(range(50))
    out = app._summarize_object(data, n=5)
    assert out['type'] == 'list'
    assert out['length'] == 50
    assert out['sample'] == [0, 1, 2, 3, 4]


def test_summarize_numpy():
    arr = np.arange(10)
    out = app._summarize_object(arr, n=3)
    assert out['type'] == 'ndarray'
    assert out['length'] == 10
    # sample może być listą intów
    assert out['sample'] == [0, 1, 2]


def test_summarize_pandas_series_and_df():
    s = pd.Series([1, 2, 3], name='vals')
    out_s = app._summarize_object(s, n=2)
    assert out_s['type'] == 'Series'
    assert out_s['length'] == 3
    assert out_s['sample'] == [1, 2]

    df = pd.DataFrame({'a': [1, 2, 3], 'subject': ['S1', 'S2', 'S3']})
    out_df = app._summarize_object(df, n=2)
    assert out_df['type'] == 'DataFrame'
    assert out_df['length'] == 3
    assert 'columns' in out_df
    assert len(out_df.get('sample_rows', [])) == 2
