"""Trie (prefix tree) for fast player-name autocomplete.

Names are normalised (lowercase, accents removed) so "vinicius" finds
"Vinicius Junior". Every word-suffix of a name is indexed, so typing
"mbappe" also finds "Kylian Mbappe".

Search cost is O(L + m): L = length of the typed prefix, m = matches visited,
independent of how many players are stored.
"""
from __future__ import annotations

import re
import unicodedata


def normalize(text: str) -> str:
    """Lowercase, strip accents and punctuation, collapse spaces."""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text).lower()
    return " ".join(text.split())


class TrieNode:
    __slots__ = ("children", "entries")

    def __init__(self) -> None:
        self.children: dict[str, TrieNode] = {}
        self.entries: list[tuple[str, int]] = []  # (display name, player_id)


class Trie:
    def __init__(self) -> None:
        self.root = TrieNode()
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def insert(self, name: str, player_id: int) -> None:
        """Add a player. The full name and every word-suffix are indexed."""
        words = normalize(name).split()
        if not words:
            raise ValueError("name cannot be empty")
        for i in range(len(words)):
            node = self.root
            for ch in " ".join(words[i:]):
                node = node.children.setdefault(ch, TrieNode())
            if (name, player_id) not in node.entries:
                node.entries.append((name, player_id))
        self._size += 1

    def search_prefix(self, prefix: str, limit: int | None = None) -> list[tuple[str, int]]:
        """Return (name, player_id) pairs whose name (or any word-suffix) starts with prefix."""
        node = self.root
        for ch in normalize(prefix):
            node = node.children.get(ch)
            if node is None:
                return []
        results: list[tuple[str, int]] = []
        seen: set[int] = set()
        stack = [node]
        while stack:                              # iterative depth-first search
            cur = stack.pop()
            for name, pid in cur.entries:
                if pid not in seen:
                    seen.add(pid)
                    results.append((name, pid))
                    if limit is not None and len(results) >= limit:
                        return results
            for ch in sorted(cur.children, reverse=True):   # visit a, b, c... in order
                stack.append(cur.children[ch])
        return results
