"""
Suffix-based backoff analyzer for unknown Karelian word forms.

Strategy: from the known paradigm table, extract (form_suffix, lemma_suffix, tags)
patterns and use them to predict analyses for words not found in the lexicon.
"""
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

# Maps form_suffix -> list of (lemma_suffix, tags)
SuffixModel = Dict[str, List[Tuple[str, str]]]


def build_suffix_model(
    triples: List[Tuple[str, str, str]],
    max_suffix_len: int = 7,
) -> SuffixModel:
    """
    For each (lemma, form, tags) triple, record the relationship between
    the form suffix and the lemma suffix at lengths 1..max_suffix_len.
    """
    model: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for lemma, form, tags in triples:
        lemma_l = lemma.lower()
        form_l = form.lower()
        for n in range(1, max_suffix_len + 1):
            fsuf = form_l[-n:] if len(form_l) >= n else form_l
            lsuf = lemma_l[-n:] if len(lemma_l) >= n else lemma_l
            model[fsuf].append((lsuf, tags))
    return dict(model)


def _best_candidates(
    word: str,
    model: SuffixModel,
    max_suffix_len: int = 7,
    top_k: int = 5,
) -> List[dict]:
    """
    Try suffixes of decreasing length; return the top-k most frequent
    (lemma_suffix → tags) interpretations with reconstructed lemmas.
    """
    word_l = word.lower()
    results = []
    seen = set()

    for n in range(min(max_suffix_len, len(word_l)), 0, -1):
        fsuf = word_l[-n:]
        if fsuf not in model:
            continue
        stem = word_l[: len(word_l) - n]  # the part before the suffix
        counter: Counter = Counter()
        for lsuf, tags in model[fsuf]:
            counter[(lsuf, tags)] += 1
        for (lsuf, tags), freq in counter.most_common(top_k):
            lemma = stem + lsuf
            key = (lemma, tags)
            if key not in seen:
                seen.add(key)
                results.append(
                    {
                        "lemma": lemma,
                        "tags": tags,
                        "is_known": False,
                        "suffix_len": n,
                        "confidence": freq,
                    }
                )
        if results:
            break  # use longest matching suffix only
    return results[:top_k]


def predict(word: str, model: SuffixModel, top_k: int = 5) -> List[dict]:
    return _best_candidates(word, model, top_k=top_k)
