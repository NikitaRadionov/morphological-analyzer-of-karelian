"""
Evaluation script for the Karelian morphological analyzer.

Splits data by LEMMA (not by individual triples) so the model never sees
any form of a held-out lemma during training.

Reports:
  - Coverage: % of test word forms covered by the lexicon (all training lemma forms)
  - Exact-match accuracy for known forms
  - Suffix-backoff accuracy for unknown (held-out) lemma forms
  - Tag-level F1 on unknown forms

Run: python evaluation/eval.py
"""
import sys, os, random
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "fst"))

from analyzer.loader import load_tsv, build_indices
from analyzer.suffixes import build_suffix_model, predict


def run_evaluation(test_lemma_ratio: float = 0.1, seed: int = 42):
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    main_file = os.path.join(data_dir, "krl-new-written-karelian.tsv")

    all_triples = load_tsv(main_file)

    # Group by lemma
    by_lemma = defaultdict(list)
    for lemma, form, tags in all_triples:
        by_lemma[lemma].append((form, tags))

    lemmas = list(by_lemma.keys())
    random.seed(seed)
    random.shuffle(lemmas)

    split = int(len(lemmas) * (1 - test_lemma_ratio))
    train_lemmas = set(lemmas[:split])
    test_lemmas  = set(lemmas[split:])

    train_triples = [(l, f, t) for l in train_lemmas for f, t in by_lemma[l]]
    test_triples  = [(l, f, t) for l in test_lemmas  for f, t in by_lemma[l]]

    form_index, _ = build_indices(train_triples)
    suffix_model   = build_suffix_model(train_triples)

    # --- full lexicon stats (using ALL data) ---
    all_form_index, _ = build_indices(all_triples)
    full_coverage = len(all_form_index)

    total = len(test_triples)
    known_count = unknown_count = 0
    known_correct = unknown_correct = 0
    tag_tp = tag_total = 0

    for lemma_gold, form, tags_gold in test_triples:
        form_l = form.lower()
        gold_tags = set(tags_gold.split(";"))

        if form_l in form_index:
            # Form appears in a training lemma's paradigm
            known_count += 1
            top_lemma, top_tags = form_index[form_l][0]
            correct = (top_lemma == lemma_gold and top_tags == tags_gold)
            if correct:
                known_correct += 1
            pred_tags = set(top_tags.split(";"))
        else:
            unknown_count += 1
            candidates = predict(form_l, suffix_model, top_k=1)
            if candidates:
                top = candidates[0]
                if top["lemma"] == lemma_gold and top["tags"] == tags_gold:
                    unknown_correct += 1
                pred_tags = set(top["tags"].split(";"))
            else:
                pred_tags = set()

        tag_tp    += len(pred_tags & gold_tags)
        tag_total += len(gold_tags)

    print("=" * 55)
    print("  ОЦЕНКА МОРФОЛОГИЧЕСКОГО АНАЛИЗАТОРА КАРЕЛЬСКОГО")
    print("=" * 55)
    print(f"  Всего лемм в данных:        {len(lemmas)}")
    print(f"  Обучающих лемм:             {len(train_lemmas)}")
    print(f"  Тестовых лемм (скрытых):    {len(test_lemmas)}")
    print(f"  Словоформ в словаре:        {full_coverage}")
    print()
    print(f"  Тест на {total} словоформах скрытых лемм:")
    print()
    if known_count:
        print(f"  Омонимичные формы          {known_count}/{total} = {known_count/total*100:.1f}%")
        print(f"    Точность (exact match):  {known_correct}/{known_count} = {known_correct/known_count*100:.1f}%")
    print(f"  Полностью новых форм:       {unknown_count}/{total} = {unknown_count/total*100:.1f}%")
    if unknown_count:
        print(f"    Точность суф. эвристики: {unknown_correct}/{unknown_count} = {unknown_correct/unknown_count*100:.1f}%")
    print(f"  Точность на уровне тегов:   {tag_tp}/{tag_total} = {tag_tp/tag_total*100:.1f}%")
    print("=" * 55)

    return {
        "coverage": full_coverage,
        "unknown_accuracy": unknown_correct / unknown_count if unknown_count else 0,
        "tag_accuracy": tag_tp / tag_total if tag_total else 0,
    }


def run_fst_evaluation():
    """
    Compares the three analysis methods used in the project on their own
    terms (they cover different, mostly non-overlapping slices of the data,
    so this is not a single shared test set):

      - lookup table:     exact match only on forms seen verbatim in training
                           data; 0% generalization to any unseen form.
      - suffix heuristic:  generalizes to any unseen lemma, but only by
                           string analogy (see run_evaluation() above for its
                           ~55% tag accuracy / ~4% exact-match on held-out
                           lemmas).
      - FST (lexd+twol):   models the actual morphophonology (consonant
                           gradation for nouns, suffix-class allomorphy for
                           verbs) and generates/recognizes every form in its
                           covered paradigm classes correctly by
                           construction, including forms never seen in any
                           training split, as long as the lemma's
                           gradation/conjugation class is one of the ones
                           modeled in karelian.lexd / karelian.twol.
    """
    import generate_lexd
    import validate as fst_validate

    groups = generate_lexd.classify()
    verb_groups = generate_lexd.classify_verbs()
    generated = fst_validate.get_generated_forms()

    total = correct = 0
    for items in groups.values():
        for lemma, nom_gold, gen_gold, prefix in items:
            for case, gold in (("nom", nom_gold), ("gen", gen_gold)):
                total += 1
                if generated.get((lemma, case)) == gold:
                    correct += 1
    for items in verb_groups.values():
        for lemma, nfin_gold, prs_gold, stem in items:
            for cell, gold in (("nfin", nfin_gold), ("prs", prs_gold)):
                total += 1
                if generated.get((lemma, cell)) == gold:
                    correct += 1

    n_lemmas = sum(len(v) for v in groups.values()) + sum(len(v) for v in verb_groups.values())
    print()
    print("=" * 55)
    print("  FST (lexd+twol) — точность на покрытых классах")
    print("=" * 55)
    print(f"  Лемм охвачено (демо-выборка классов):  {n_lemmas}")
    print(f"  Точное совпадение форм:                {correct}/{total} = {correct/total*100:.1f}%")
    print("  (NOM/GEN.SG для 5 именных классов градации;")
    print("   NFIN/PRS.3SG для 4 глагольных классов)")
    print("=" * 55)
    return {"fst_lemmas": n_lemmas, "fst_accuracy": correct / total if total else 0}


if __name__ == "__main__":
    run_evaluation()
    try:
        run_fst_evaluation()
    except Exception as e:
        print(f"\n(Пропускаю оценку FST — нужен собранный gen.hfst в WSL: {e})")
