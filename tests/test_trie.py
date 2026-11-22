import pytest

from core.trie import Trie, normalize

NAMES = [
    "Kylian Mbappe", "Erling Haaland", "Vinícius Júnior", "Son Heung-min",
    "Bruno Fernandes", "Bruno Guimaraes", "Marcus Rashford", "Mohamed Salah",
    "Martin Odegaard", "Mikel Merino",
]


def build(names=NAMES) -> Trie:
    t = Trie()
    for i, n in enumerate(names, start=1):
        t.insert(n, i)
    return t


def ids(results):
    return sorted(pid for _, pid in results)


def test_normalize_strips_accents_and_punctuation():
    assert normalize("Vinícius Júnior") == "vinicius junior"
    assert normalize("Son Heung-min") == "son heung min"
    assert normalize("  ERLING   Haaland ") == "erling haaland"


def test_find_by_first_name_prefix():
    t = build()
    assert t.search_prefix("kyl") == [("Kylian Mbappe", 1)]


def test_find_by_surname_prefix():
    t = build()
    assert ids(t.search_prefix("mbap")) == [1]


def test_accent_and_case_insensitive():
    t = build()
    assert ids(t.search_prefix("VINI")) == [3]
    assert ids(t.search_prefix("júnior")) == [3]


def test_no_match_returns_empty_list():
    assert build().search_prefix("zzz") == []


def test_limit_caps_results():
    t = Trie()
    for i in range(10):
        t.insert(f"Marco Player{i}", i)
    assert len(t.search_prefix("marco", limit=3)) == 3
    assert len(t.search_prefix("marco")) == 10


def test_no_duplicate_players_in_results():
    t = Trie()
    t.insert("Bruno Bruno", 7)           # matches "bru" through two word-suffixes
    assert t.search_prefix("bru") == [("Bruno Bruno", 7)]


def test_empty_name_rejected():
    with pytest.raises(ValueError):
        Trie().insert("   ", 1)


def test_len_counts_inserted_players():
    assert len(build()) == len(NAMES)


def test_empty_prefix_returns_everyone():
    assert ids(build().search_prefix("")) == list(range(1, len(NAMES) + 1))


@pytest.mark.parametrize("prefix", ["m", "mo", "mar", "bru", "bruno f", "ju", "heung",
                                    "kylian m", "son", "e", "zzz"])
def test_matches_brute_force(prefix):
    """The trie must return exactly what a slow scan of every name would."""
    t = build()
    p = normalize(prefix)
    expected = []
    for i, n in enumerate(NAMES, start=1):
        words = normalize(n).split()
        if any(" ".join(words[k:]).startswith(p) for k in range(len(words))):
            expected.append(i)
    assert ids(t.search_prefix(prefix)) == sorted(expected)
