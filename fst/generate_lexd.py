"""
Generates karelian.lexd from the UniMorph data: classifies nouns into
gradation classes (no gradation / kk~k / p~v / k-deletion) by comparing
NOM.SG and GEN.SG forms, then writes lexd LEXICON entries using marker
symbols for the alternating consonant. The actual phonological realization
of the markers is handled separately by karelian.twol.

Run: python fst/generate_lexd.py
"""
import sys, os
from collections import defaultdict, Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from analyzer.loader import load_tsv

DATA = os.path.join(os.path.dirname(__file__), "..", "data", "krl-new-written-karelian.tsv")
OUT_LEXD = os.path.join(os.path.dirname(__file__), "karelian.lexd")

MAX_NOGRAD = 40  # cap the baseline (no-alternation) class for a manageable demo
MAX_VERB_CLASS = 40  # cap each verb class for a manageable demo

# Verb classes: NFIN tail -> PRS;IND;POS;3;SG tail. All four are purely
# concatenative (the stem is unchanged, only the final-vowel suffix differs
# between the infinitive and the 3sg present) -- no twol rule is needed.
VERB_CLASSES = {
    ("ua", "au"): "UA",
    ("o", "u"): "O",
    ("yä", "äy"): "YA",
    ("ö", "y"): "OE",
}


def classify():
    triples = load_tsv(DATA)
    by_lemma_list = defaultdict(list)
    for lemma, form, tags in triples:
        by_lemma_list[lemma].append((form, tags))
    by_lemma_first = defaultdict(dict)
    for lemma, form, tags in triples:
        if tags not in by_lemma_first[lemma]:
            by_lemma_first[lemma][tags] = form

    lemma_pos = {}
    for lemma, entries in by_lemma_list.items():
        pos_counter = Counter(t.split(";")[0] for _, t in entries)
        lemma_pos[lemma] = pos_counter.most_common(1)[0][0]
    noun_lemmas = [l for l, p in lemma_pos.items() if p == "N"]

    groups = {"KK": [], "P": [], "K0": [], "K0A": [], "NOGRAD": []}
    for lemma in noun_lemmas:
        nom = by_lemma_first[lemma].get("N;NOM;SG")
        gen = by_lemma_first[lemma].get("N;GEN;SG")
        if not nom or not gen or "'" in lemma or chr(8217) in lemma:
            continue
        i = 0
        while i < min(len(nom), len(gen)) and nom[i] == gen[i]:
            i += 1
        nom_tail, gen_tail = nom[i:], gen[i:]
        prefix = nom[:i]
        if nom_tail == "ka" and gen_tail == "an":
            # "kk" surfaces only if the prefix itself ends in "k" (true geminate,
            # e.g. ak|ka ~ ak|an -> akka/akan). Otherwise there's just a single
            # "k" that deletes entirely before -n, e.g. huah|ka ~ huah|an
            # (huahka/huahan) -- same pattern as K0 but with vowel "a".
            if prefix.endswith("k"):
                groups["KK"].append((lemma, nom, gen, prefix))
            else:
                groups["K0A"].append((lemma, nom, gen, prefix))
        elif nom_tail == "pa" and gen_tail == "van":
            groups["P"].append((lemma, nom, gen, prefix))
        elif nom_tail == "ku" and gen_tail == "un":
            groups["K0"].append((lemma, nom, gen, prefix))
        elif nom_tail == "" and gen_tail == "n":
            groups["NOGRAD"].append((lemma, nom, gen, prefix))

    groups["NOGRAD"] = groups["NOGRAD"][:MAX_NOGRAD]
    return groups


def classify_verbs():
    triples = load_tsv(DATA)
    by_lemma_list = defaultdict(list)
    for lemma, form, tags in triples:
        by_lemma_list[lemma].append((form, tags))
    by_lemma_first = defaultdict(dict)
    for lemma, form, tags in triples:
        if tags not in by_lemma_first[lemma]:
            by_lemma_first[lemma][tags] = form

    lemma_pos = {}
    for lemma, entries in by_lemma_list.items():
        pos_counter = Counter(t.split(";")[0] for _, t in entries)
        lemma_pos[lemma] = pos_counter.most_common(1)[0][0]
    verb_lemmas = [l for l, p in lemma_pos.items() if p == "V"]

    def common_prefix_len(a, b):
        i = 0
        while i < min(len(a), len(b)) and a[i] == b[i]:
            i += 1
        return i

    groups = {name: [] for name in VERB_CLASSES.values()}
    for lemma in verb_lemmas:
        nfin = by_lemma_first[lemma].get("V;NFIN")
        prs = by_lemma_first[lemma].get("V;PRS;IND;POS;3;SG")
        if not nfin or not prs or nfin != lemma or "'" in lemma or chr(8217) in lemma:
            continue
        i = common_prefix_len(nfin, prs)
        tail = (nfin[i:], prs[i:])
        if tail in VERB_CLASSES:
            stem = nfin[:i]
            groups[VERB_CLASSES[tail]].append((lemma, nfin, prs, stem))

    for name in groups:
        groups[name] = groups[name][:MAX_VERB_CLASS]
    return groups


def build_lexd(groups, verb_groups):
    lines = []
    lines.append("PATTERNS")
    lines.append("NounRootNoGrad NounInfl")
    lines.append("NounRootKK NounInfl")
    lines.append("NounRootP NounInfl")
    lines.append("NounRootK0 NounInfl")
    lines.append("NounRootK0A NounInfl")
    for name in verb_groups:
        lines.append(f"VerbRoot{name} VerbInfl{name}")
    lines.append("")

    lines.append("LEXICON NounRootNoGrad")
    for lemma, nom, gen, prefix in groups["NOGRAD"]:
        lines.append(f"{lemma}:{nom}")
    lines.append("")

    lines.append("LEXICON NounRootKK")
    for lemma, nom, gen, prefix in groups["KK"]:
        stem = prefix[:-1] if prefix.endswith("k") else prefix
        marked = f"{stem}{{GK}}a"
        lines.append(f"{lemma}:{marked}")
    lines.append("")

    lines.append("LEXICON NounRootP")
    for lemma, nom, gen, prefix in groups["P"]:
        marked = f"{prefix}{{GP}}a"
        lines.append(f"{lemma}:{marked}")
    lines.append("")

    lines.append("LEXICON NounRootK0")
    for lemma, nom, gen, prefix in groups["K0"]:
        marked = f"{prefix}{{GD}}u"
        lines.append(f"{lemma}:{marked}")
    lines.append("")

    lines.append("LEXICON NounRootK0A")
    for lemma, nom, gen, prefix in groups["K0A"]:
        marked = f"{prefix}{{GD}}a"
        lines.append(f"{lemma}:{marked}")
    lines.append("")

    lines.append("LEXICON NounInfl")
    lines.append("<n><nom><sg>:")
    lines.append("<n><gen><sg>:n")
    lines.append("")

    tails_by_name = {name: tail for tail, name in VERB_CLASSES.items()}
    for name, items in verb_groups.items():
        lines.append(f"LEXICON VerbRoot{name}")
        for lemma, nfin, prs, stem in items:
            lines.append(f"{lemma}:{stem}")
        lines.append("")

    for name in verb_groups:
        nfin_tail, prs_tail = tails_by_name[name]
        lines.append(f"LEXICON VerbInfl{name}")
        lines.append(f"<v><nfin>:{nfin_tail}")
        lines.append(f"<v><prs><ind><pos><3><sg>:{prs_tail}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


if __name__ == "__main__":
    groups = classify()
    for k, v in groups.items():
        print(f"{k}: {len(v)} lemmas")
    verb_groups = classify_verbs()
    for k, v in verb_groups.items():
        print(f"Verb{k}: {len(v)} lemmas")
    text = build_lexd(groups, verb_groups)
    with open(OUT_LEXD, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"\nWrote {OUT_LEXD}")
