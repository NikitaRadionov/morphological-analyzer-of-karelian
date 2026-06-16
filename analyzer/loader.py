"""
Loads and indexes the UniMorph Karelian paradigm tables.
"""
import os
from collections import defaultdict
from typing import Dict, List, Tuple

# (form -> [(lemma, tags_string), ...])
FormIndex = Dict[str, List[Tuple[str, str]]]
# (lemma -> [(form, tags_string), ...])
LemmaIndex = Dict[str, List[Tuple[str, str]]]


def load_tsv(path: str) -> List[Tuple[str, str, str]]:
    """Read a UniMorph TSV file and return (lemma, form, tags) triples."""
    triples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            lemma, form, tags = parts
            triples.append((lemma.strip(), form.strip(), tags.strip()))
    return triples


def build_indices(triples: List[Tuple[str, str, str]]) -> Tuple[FormIndex, LemmaIndex]:
    """Build forward (form→lemma+tags) and backward (lemma→forms) indices."""
    form_index: FormIndex = defaultdict(list)
    lemma_index: LemmaIndex = defaultdict(list)
    for lemma, form, tags in triples:
        form_index[form.lower()].append((lemma, tags))
        lemma_index[lemma.lower()].append((form, tags))
    return dict(form_index), dict(lemma_index)


def load_default_data() -> Tuple[FormIndex, LemmaIndex, List[Tuple[str, str, str]]]:
    """Load the main New Written Karelian dataset."""
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    main_file = os.path.join(data_dir, "krl-new-written-karelian.tsv")
    triples = load_tsv(main_file)
    form_index, lemma_index = build_indices(triples)
    return form_index, lemma_index, triples
