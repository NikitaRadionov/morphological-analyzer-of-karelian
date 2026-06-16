"""
Downloads UniMorph Karelian data from GitHub and saves locally.
Run once: python data/download.py
"""
import urllib.request
import os

BASE_URL = "https://raw.githubusercontent.com/unimorph/krl/master/"
DATA_DIR = os.path.dirname(__file__)

FILES = [
    "krl",
    "krl-dyorzha",
    "krl-kestenga",
    "krl-uhta",
    "krl-voknavolok",
    "krl-new-written-karelian",
]


def download():
    for fname in FILES:
        url = BASE_URL + fname
        dest = os.path.join(DATA_DIR, fname + ".tsv")
        if os.path.exists(dest):
            print(f"  already exists: {dest}")
            continue
        print(f"  downloading {fname} ...", end=" ")
        try:
            urllib.request.urlretrieve(url, dest)
            lines = open(dest, encoding="utf-8").readlines()
            print(f"{len(lines)} lines")
        except Exception as e:
            print(f"FAILED: {e}")


if __name__ == "__main__":
    print("Downloading UniMorph Karelian data...")
    download()
    print("Done.")
