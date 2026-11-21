"""Create a source-only Oracle VM bundle without local secrets or datasets."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist" / "retailpulse-oracle-deploy.zip"

FILES = [
    Path("Dockerfile"),
    Path(".dockerignore"),
    Path("requirements-dashboard.txt"),
    Path("app.py"),
    Path("dashboard_data.py"),
    Path("README.MD"),
    Path(".streamlit/config.toml"),
    Path("app_pages/overview.py"),
    Path("app_pages/sales.py"),
    Path("app_pages/products.py"),
    Path("app_pages/customers.py"),
    Path("app_pages/returns.py"),
    Path("app_pages/data_quality.py"),
    Path("assets/retailpulse_logo.svg"),
    Path("assets/retailpulse_icon.svg"),
    Path("deploy/oracle/compose.yml"),
    Path("deploy/oracle/create_reader.sh"),
    Path("deploy/oracle/grant_reader.sql"),
    Path("deploy/oracle/.env.example"),
    Path("deploy/oracle/README.md"),
]


def main() -> None:
    missing = [str(path) for path in FILES if not (ROOT / path).is_file()]
    if missing:
        raise FileNotFoundError(f"Deployment files missing: {', '.join(missing)}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED, compresslevel=8) as archive:
        for relative_path in FILES:
            archive.write(ROOT / relative_path, Path("RetailPulse") / relative_path)

    print(f"Deployment bundle created: {OUTPUT}")
    print(f"Files included: {len(FILES)}")


if __name__ == "__main__":
    main()
