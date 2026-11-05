import shutil
import zipfile
from pathlib import Path

import requests
from tqdm import tqdm

TOOLS_DIR = Path(__file__).resolve().parent
KAIKKI_PATH = TOOLS_DIR / "kaikki.jsonl"
TATOEBA_PATH = TOOLS_DIR / "tatoeba.tsv"


def download_file(url: str, filename: Path):
    print(f"Downloading {filename.name}...")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    block_size = 1024 * 1024  # 1 MiB

    with open(filename, "wb") as file, tqdm(
        total=total_size, unit="iB", unit_scale=True
    ) as bar:
        for data in response.iter_content(block_size):
            bar.update(len(data))
            file.write(data)


def main():
    # 1. Download Kaikki German Dictionary (~1 GB).
    kaikki_url = (
        "https://kaikki.org/dictionary/German/"
        "kaikki.org-dictionary-German.jsonl"
    )
    if not KAIKKI_PATH.exists():
        download_file(kaikki_url, KAIKKI_PATH)
    else:
        print(f"{KAIKKI_PATH} already exists. Skipping.")

    # 2. Download Tatoeba German-English pairs (~10 MB).
    tatoeba_url = "https://www.manythings.org/anki/deu-eng.zip"
    if not TATOEBA_PATH.exists():
        zip_path = TOOLS_DIR / "deu-eng.zip"
        download_file(tatoeba_url, zip_path)
        print("Extracting Tatoeba sentences...")
        with zipfile.ZipFile(zip_path) as archive:
            with archive.open("deu.txt") as source:
                with open(TATOEBA_PATH, "wb") as target:
                    shutil.copyfileobj(source, target)
        zip_path.unlink()
        print(f"Saved to {TATOEBA_PATH}")
    else:
        print(f"{TATOEBA_PATH} already exists. Skipping.")

    print("\nDownload complete! You can now run python tools/build_pipeline.py")


if __name__ == "__main__":
    main()
