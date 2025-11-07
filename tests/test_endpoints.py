import json
import pytest
from flask import url_for

import app


def test_home(client):
    res = client.get('/')
    assert res.status_code == 200
    # compare as text to handle non-ascii characters
    assert 'WESAD Backend API działa' in res.get_data(as_text=True)


def test_data_dir(client, monkeypatch, tmp_path):
    # patch BASE_DIR and DATA_DIR_CANDIDATES to use a temp dir
    monkeypatch.setattr(app, 'BASE_DIR', str(tmp_path))
    # create S2 folder
    s2 = tmp_path / 'S2'
    s2.mkdir()
    monkeypatch.setattr(app, 'DATA_DIR_CANDIDATES', ['S2', 'S3'])

    res = client.get('/data_dir')
    assert res.status_code == 200
    j = res.get_json()
    assert 'data_dir' in j
    assert 'files' in j


def test_participants_no_unpickle(client, monkeypatch, tmp_path):
    # create empty data dir and ensure unpickling disabled -> returns files list only
    monkeypatch.setattr(app, 'BASE_DIR', str(tmp_path))
    s2 = tmp_path / 'S2'
    s2.mkdir()
    monkeypatch.setattr(app, 'DATA_DIR_CANDIDATES', ['S2'])

    # Ensure _is_unpickle_allowed returns False
    monkeypatch.setattr(app, '_is_unpickle_allowed', lambda: False)

    res = client.get('/participants')
    assert res.status_code == 200
    j = res.get_json()
    assert 'files' in j
    assert j['subjects_by_file'] == {}


def test_participant_info_mocked(client, monkeypatch):
    # Mock load_participant_data to avoid unpickling heavy files
    fake_data = {
        'subject': 'S99',
        'signal': {
            'chest': {
                'TEMP': list(range(200)),
                'EDA': list(range(50))
            },
            'wrist': {
                'ACC': [0, 1, 2]
            }
        },
        'label': [0, 1, 0]
    }

    monkeypatch.setattr(app, 'load_participant_data', lambda sid: fake_data)
    # allow unpickling via query param (endpoint checks it)
    res = client.get('/participant/99?allow_unpickle=1')
    assert res.status_code == 200
    j = res.get_json()
    assert j['subject'] == 'S99'
    assert 'available_signals' in j
    assert 'chest' in j['available_signals']
    assert 'TEMP' in j['available_signals']['chest']

    # test params filtering: request TEMP:5 only
    res2 = client.get('/participant/99?allow_unpickle=1&params=TEMP:5')
    assert res2.status_code == 200
    j2 = res2.get_json()
    chest = j2['available_signals'].get('chest', {})
    assert 'TEMP' in chest
    # sample length for TEMP should be 5
    sample = chest['TEMP'].get('sample')
    assert sample is not None and len(sample) == 5


# pytest fixtures
@pytest.fixture
def client():
    app.app.config['TESTING'] = True
    with app.app.test_client() as c:
        yield c
