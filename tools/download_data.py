import os
import zipfile
import requests
from tqdm import tqdm

def download_file(url: str, filename: str):
    print(f"Downloading {filename}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024 * 1024 # 1 Megabyte
    
    with open(filename, 'wb') as file, tqdm(
        total=total_size, unit='iB', unit_scale=True
    ) as bar:
        for data in response.iter_content(block_size):
            bar.update(len(data))
            file.write(data)

def main():
    # 1. Download Kaikki German Dictionary (~1 GB)
    kaikki_url = "https://kaikki.org/dictionary/German/kaikki.org-dictionary-German.jsonl"
    if not os.path.exists("kaikki.jsonl"):
        download_file(kaikki_url, "kaikki.jsonl")
    else:
        print("kaikki.jsonl already exists. Skipping.")

    # 2. Download Tatoeba German-English pairs (~10 MB)
    tatoeba_url = "http://www.manythings.org/anki/deu-eng.zip"
    if not os.path.exists("tatoeba.tsv"):
        download_file(tatoeba_url, "deu-eng.zip")
        print("Extracting Tatoeba sentences...")
        with zipfile.ZipFile("deu-eng.zip", 'r') as zip_ref:
            # The zip contains a 'deu.txt' file
            zip_ref.extract("deu.txt")
        os.rename("deu.txt", "tatoeba.tsv")
        os.remove("deu-eng.zip")
        print("Saved to tatoeba.tsv")
    else:
        print("tatoeba.tsv already exists. Skipping.")
        
    print("\nDownload complete! You can now run build_pipeline.py")

if __name__ == "__main__":
    main()
