
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = PROJECT_ROOT / "data" / "source" / "olist"
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze" / "olist"


def test_source_directory_exists():
    assert SOURCE_DIR.is_dir()


def test_csv_files_exist():
    assert list(SOURCE_DIR.glob("*.csv"))


def test_csv_files_are_readable():
    files = list(SOURCE_DIR.glob("*.csv"))
    assert files

    for file in files:
        df = pd.read_csv(file, nrows=5)
        assert len(df.columns) > 0


def test_bronze_parquet_files_exist():
    assert list(BRONZE_DIR.glob("*.parquet"))


def test_bronze_parquet_files_are_readable():
    files = list(BRONZE_DIR.glob("*.parquet"))
    assert files

    for file in files:
        df = pd.read_parquet(file)
        assert len(df.columns) > 0
        assert not df.empty
