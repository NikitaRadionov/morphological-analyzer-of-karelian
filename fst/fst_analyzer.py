"""
Python wrapper around the compiled lexd+twol FST (ana.hfstol / gen.hfstol).
The actual lookup runs inside WSL via hfst-optimized-lookup, since HFST has
no native Windows build; this module just shells out and converts the HFST
tag notation (<n><nom><sg>) to the UniMorph notation (N;NOM;SG) used
elsewhere in the project.

Run standalone for a smoke test: python fst/fst_analyzer.py <word>
"""
import os
import re
import subprocess

FST_DIR = os.path.dirname(__file__)
ANA_HFSTOL = os.path.join(FST_DIR, "ana.hfstol")
GEN_HFSTOL = os.path.join(FST_DIR, "gen.hfstol")

HFST_TAG_MAP = {
    "n": "N", "v": "V",
    "nom": "NOM", "gen": "GEN",
    "sg": "SG", "pl": "PL",
    "nfin": "NFIN",
    "prs": "PRS", "ind": "IND", "pos": "POS",
    "3": "3", "1": "1", "2": "2",
}

_TAG_RE = re.compile(r"<([^>]+)>")
_ANALYSIS_RE = re.compile(r"^(.+?)((?:<[^>]+>)+)$")


def _wsl_path(p):
    p = os.path.abspath(p).replace("\\", "/")
    drive, rest = p.split(":", 1)
    return f"/mnt/{drive.lower()}{rest}"


def available():
    return os.path.exists(ANA_HFSTOL)


def _run_lookup(hfstol_path, query):
    try:
        if os.name == "nt":  # Windows — через WSL
            wsl_dir = _wsl_path(os.path.dirname(hfstol_path))
            fname = os.path.basename(hfstol_path)
            cmd = ["wsl", "-d", "Ubuntu", "--", "bash", "-c",
                   f"cd '{wsl_dir}' && hfst-optimized-lookup {fname}"]
        else:  # Linux / Mac — нативный HFST
            cmd = ["hfst-optimized-lookup", hfstol_path]
        result = subprocess.run(
            cmd, input=query.encode("utf-8"), capture_output=True, timeout=20,
        )
    except Exception:
        return ""
    return result.stdout.decode("utf-8", errors="replace")


def _hfst_tags_to_unimorph(tag_str):
    tokens = _TAG_RE.findall(tag_str)
    return ";".join(HFST_TAG_MAP.get(t, t.upper()) for t in tokens)


def analyze(word):
    """Analyze a surface form via the FST. Returns [{'lemma':, 'tags':}, ...]."""
    if not available():
        return []
    out = _run_lookup(ANA_HFSTOL, word.strip().lower() + "\n")
    results = []
    seen = set()
    for line in out.splitlines():
        if "\t" not in line:
            continue
        surface, analysis = line.split("\t", 1)
        if "+?" in analysis:
            continue
        m = _ANALYSIS_RE.match(analysis)
        if not m:
            continue
        lemma, tag_part = m.groups()
        tags = _hfst_tags_to_unimorph(tag_part)
        key = (lemma, tags)
        if key in seen:
            continue
        seen.add(key)
        results.append({"lemma": lemma, "tags": tags})
    return results


_UNIMORPH_TO_HFST_TAG = {v: k for k, v in HFST_TAG_MAP.items()}
_UNIMORPH_TO_HFST_POS = {"N": "n", "V": "v"}


def generate(lemma, tags):
    """Generate a surface form via the FST for lemma + UniMorph tags ('N;NOM;SG')."""
    if not available():
        return None
    parts = [t.strip() for t in tags.split(";") if t.strip()]
    hfst_tag = "".join(f"<{_UNIMORPH_TO_HFST_TAG.get(p, p.lower())}>" for p in parts)
    query = f"{lemma}{hfst_tag}\n"
    out = _run_lookup(GEN_HFSTOL, query)
    for line in out.splitlines():
        if "\t" not in line:
            continue
        _, surface = line.split("\t", 1)
        if "+?" not in surface and surface.strip():
            return surface
    return None


if __name__ == "__main__":
    import sys
    word = sys.argv[1] if len(sys.argv) > 1 else "akan"
    print(analyze(word))
