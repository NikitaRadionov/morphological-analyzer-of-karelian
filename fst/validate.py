"""
Validates the compiled lexd+twol FST grammar against the gold UniMorph forms
for NOM.SG / GEN.SG of every lemma included in karelian.lexd.

Requires gen.hfst to be built (see build.sh). Calls hfst-fst2strings inside WSL.

Run: python fst/validate.py
"""
import sys, os, subprocess, re
from collections import defaultdict, Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from analyzer.loader import load_tsv
from generate_lexd import classify, classify_verbs

FST_DIR = os.path.dirname(__file__)


def wsl_path(p):
    p = os.path.abspath(p).replace("\\", "/")
    drive, rest = p.split(":", 1)
    return f"/mnt/{drive.lower()}{rest}"


def get_generated_forms():
    gen_hfst = os.path.join(FST_DIR, "gen.hfst")
    wsl_dir = wsl_path(FST_DIR)
    result = subprocess.run(
        ["wsl", "-d", "Ubuntu", "--", "bash", "-c",
         f"cd '{wsl_dir}' && hfst-fst2strings gen.hfst"],
        capture_output=True, text=True, encoding="utf-8",
    )
    forms = {}  # (lemma, tag) -> surface
    noun_pattern = re.compile(r"^(.+?)<n><(nom|gen)><sg>:(.+)$")
    verb_pattern = re.compile(r"^(.+?)<v>(<nfin>|<prs><ind><pos><3><sg>):(.+)$")
    for line in result.stdout.splitlines():
        line = line.strip()
        m = noun_pattern.match(line)
        if m:
            lemma, case, surface = m.groups()
            forms[(lemma, case)] = surface
            continue
        m = verb_pattern.match(line)
        if m:
            lemma, tag, surface = m.groups()
            cell = "nfin" if tag == "<nfin>" else "prs"
            forms[(lemma, cell)] = surface
    return forms


def main():
    groups = classify()
    verb_groups = classify_verbs()
    generated = get_generated_forms()

    total = 0
    correct = 0
    errors = []

    for group_name, items in groups.items():
        group_total = 0
        group_correct = 0
        for lemma, nom_gold, gen_gold, prefix in items:
            for case, gold in (("nom", nom_gold), ("gen", gen_gold)):
                total += 1
                group_total += 1
                got = generated.get((lemma, case))
                if got == gold:
                    correct += 1
                    group_correct += 1
                else:
                    errors.append((group_name, lemma, case, gold, got))
        pct = group_correct / group_total * 100 if group_total else 0
        print(f"{group_name:8s}: {group_correct}/{group_total} = {pct:.1f}%")

    for group_name, items in verb_groups.items():
        group_total = 0
        group_correct = 0
        for lemma, nfin_gold, prs_gold, stem in items:
            for cell, gold in (("nfin", nfin_gold), ("prs", prs_gold)):
                total += 1
                group_total += 1
                got = generated.get((lemma, cell))
                if got == gold:
                    correct += 1
                    group_correct += 1
                else:
                    errors.append((f"Verb{group_name}", lemma, cell, gold, got))
        pct = group_correct / group_total * 100 if group_total else 0
        print(f"Verb{group_name:5s}: {group_correct}/{group_total} = {pct:.1f}%")

    print()
    print(f"ИТОГО: {correct}/{total} = {correct/total*100:.1f}%")

    if errors:
        print(f"\nОшибки ({len(errors)}):")
        for group_name, lemma, case, gold, got in errors[:20]:
            print(f"  [{group_name}] {lemma} {case}: ожидалось {gold!r}, получено {got!r}")


if __name__ == "__main__":
    main()
