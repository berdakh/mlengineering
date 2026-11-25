"""Error contracts of the loader, exercised with real files in tmp_path."""
import pytest

from pumpwatch.io import REQUIRED_COLUMNS, load_windows


def test_load_windows_roundtrip(tmp_path, make_frame):
    path = tmp_path / "windows.csv"
    df = make_frame(n_units=1, n_windows=2, n_samples=8)
    df.to_csv(path, index=False)
    loaded = load_windows(path)
    assert len(loaded) == len(df)
    assert set(REQUIRED_COLUMNS) <= set(loaded.columns)


def test_load_windows_accepts_str_path(tmp_path, make_frame):
    path = tmp_path / "windows.csv"
    make_frame(n_units=1, n_windows=1, n_samples=4).to_csv(path, index=False)
    assert len(load_windows(str(path))) == 4


@pytest.mark.parametrize("dropped", ["label", "vibration", "unit_id"])
def test_load_windows_rejects_missing_column(tmp_path, make_frame, dropped):
    path = tmp_path / "broken.csv"
    make_frame(n_units=1, n_windows=1, n_samples=4).drop(columns=dropped).to_csv(path, index=False)
    with pytest.raises(ValueError, match=dropped):
        load_windows(path)


def test_load_windows_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_windows(tmp_path / "does_not_exist.csv")
