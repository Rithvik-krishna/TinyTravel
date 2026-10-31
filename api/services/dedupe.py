from rapidfuzz import fuzz
AUTO, SUGGEST = 0.90, 0.75
def name_confidence(a: str, b: str) -> float:
    return fuzz.token_sort_ratio(a.lower(), b.lower()) / 100
def match_status(conf: float) -> str:
    return "merged" if conf >= AUTO else "suggested" if conf >= SUGGEST else "separate"
