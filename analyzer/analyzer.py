"""
Main Karelian morphological analyzer.

Usage:
    from analyzer.analyzer import KarelianAnalyzer
    a = KarelianAnalyzer()
    results = a.analyze("koiru")
    # -> [{'lemma': 'koiru', 'tags': 'N;NOM;SG', 'is_known': True, ...}, ...]
"""
import os
import sys
from typing import List, Dict, Any
from .loader import load_default_data, FormIndex, LemmaIndex
from .suffixes import build_suffix_model, predict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "fst"))
import fst_analyzer

TAG_DESCRIPTIONS = {
    # Parts of speech
    "N": "существительное",
    "V": "глагол",
    "ADJ": "прилагательное",
    "ADV": "наречие",
    "PROPN": "имя собственное",
    "NUM": "числительное",
    "PRON": "местоимение",
    # Cases
    "NOM": "именительный",
    "GEN": "родительный",
    "ACC": "винительный",
    "PRT": "партитив",
    "IN+ESS": "инессив",
    "IN+ALL": "иллатив",
    "IN+ABL": "элатив",
    "AT+ESS+ALL": "аллатив",
    "AT+ESS": "адессив",
    "AT+ABL": "аблатив",
    "TRANS": "транслатив",
    "FRML": "формальный",
    "PRIV": "привативный",
    "COM": "комитатив",
    "INS": "инструктив",
    # Number
    "SG": "единственное число",
    "PL": "множественное число",
    # Verb features
    "IND": "изъявительное наклонение",
    "COND": "условное наклонение",
    "IMP": "повелительное наклонение",
    "POT": "потенциалис",
    "IPFV": "несовершенный вид",
    "PRF": "перфект",
    "ACT": "действительный залог",
    "PASS": "страдательный залог",
    "NFIN": "инфинитив",
    "PRS": "настоящее время",
    "PST": "прошедшее время",
    "NEG": "отрицательный",
    "1": "1-е лицо",
    "2": "2-е лицо",
    "3": "3-е лицо",
    "POS": "положительная степень",
    "DET": "определённый",
}


def describe_tags(tags_str: str) -> str:
    """Return a human-readable description of a tags string like 'N;NOM;SG'."""
    parts = [t.strip() for t in tags_str.split(";")]
    descriptions = [TAG_DESCRIPTIONS.get(p, p) for p in parts if p]
    return ", ".join(descriptions)


class KarelianAnalyzer:
    def __init__(self):
        print("Loading Karelian morphological data...", end=" ", flush=True)
        self.form_index, self.lemma_index, triples = load_default_data()
        self.suffix_model = build_suffix_model(triples)
        print(f"OK. {len(self.form_index)} known forms, {len(self.lemma_index)} lemmas.")

    def analyze(self, word: str) -> List[Dict[str, Any]]:
        """
        Analyze a word form.
        Returns a list of analyses, each with keys:
          lemma, tags, description, is_known
        Known words come first; unknown words fall back to suffix prediction.
        """
        word_l = word.strip().lower()
        if not word_l:
            return []

        # Primary path: real FST analysis (lexd+twol), when the word falls
        # within the FST's (currently limited demo) lexicon.
        fst_results = fst_analyzer.analyze(word_l)
        if fst_results:
            return [
                {
                    "lemma": r["lemma"],
                    "tags": r["tags"],
                    "description": describe_tags(r["tags"]),
                    "is_known": True,
                    "confidence": None,
                    "source": "fst",
                }
                for r in fst_results
            ]

        if word_l in self.form_index:
            results = []
            seen = set()
            for lemma, tags in self.form_index[word_l]:
                key = (lemma, tags)
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    {
                        "lemma": lemma,
                        "tags": tags,
                        "description": describe_tags(tags),
                        "is_known": True,
                        "confidence": None,
                        "source": "lookup",
                    }
                )
            return results

        # Unknown word — use suffix backoff
        candidates = predict(word_l, self.suffix_model, top_k=5)
        for c in candidates:
            c["description"] = describe_tags(c["tags"])
            c["source"] = "heuristic"
        return candidates

    def generate(self, lemma: str) -> List[Dict[str, str]]:
        """
        Given a lemma, return all known forms with their tags (paradigm).
        """
        lemma_l = lemma.strip().lower()
        if lemma_l not in self.lemma_index:
            return []
        return [
            {"form": form, "tags": tags, "description": describe_tags(tags)}
            for form, tags in self.lemma_index[lemma_l]
        ]

    def stats(self) -> Dict[str, int]:
        return {
            "known_forms": len(self.form_index),
            "lemmas": len(self.lemma_index),
        }
