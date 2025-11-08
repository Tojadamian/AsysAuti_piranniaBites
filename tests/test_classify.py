import app

# Prosty zestaw testowy dla funkcji klasyfikacji i ekstrakcji cech

def test_classify_stress():
    feats = {
        'mean_eda': 0.9,
        'hr': 70.0,
        'hrv': 300.0,
        'temp': 30.9,
        'acc_rms': 1.02,
    }
    assert app.classify(feats) == 'stres'


def test_classify_pleasure():
    feats = {
        'mean_eda': 0.4,
        'hr': 55.0,
        'hrv': 380.0,
        'temp': 31.3,
        'acc_rms': 1.0,
    }
    assert app.classify(feats) == 'zadowolenie'


def test_classify_neutral():
    feats = {
        'mean_eda': 0.65,
        'hr': 63.0,
        'hrv': 350.0,
        'temp': 31.225,
        'acc_rms': 1.013,
    }
    assert app.classify(feats) == 'neutralny'


def test_extract_dataframe_features(tmp_path, monkeypatch):
    import pandas as pd
    df = pd.DataFrame({
        'EDA': [0.5, 0.6, 0.7],
        'HR': [60, 61, 62],
        'HRV': [360, 355, 350],
        'TEMP': [31.23, 31.24, 31.235],
        'ACC_X': [0.1, 0.2, 0.15],
        'ACC_Y': [0.05, 0.3, 0.25],
        'ACC_Z': [0.2, 0.1, 0.05],
    })
    feats = app._extract_features_from_signals(df)
    assert feats['mean_eda'] is not None
    assert feats['hr'] is not None
    assert feats['hrv'] is not None
    assert feats['temp'] is not None
    assert feats['acc_rms'] is not None
