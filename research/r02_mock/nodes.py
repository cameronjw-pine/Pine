"""R02 {2,3} odds lattice nodes (plan §1), exact rational arithmetic."""
from fractions import Fraction

EPS = Fraction(1, 4100)


class Node:
    __slots__ = ("a", "b", "h", "num", "den", "f", "label")

    def __init__(self, a, b):
        self.a, self.b = a, b
        self.h = abs(a) + abs(b)
        self.num = 2 ** max(a, 0) * 3 ** max(b, 0)
        self.den = 2 ** max(-a, 0) * 3 ** max(-b, 0)
        self.f = Fraction(self.num, self.num + self.den)
        self.label = f"{self.num}:{self.den}"

    def level(self, L, H):
        return L + self.f * (H - L)

    def band(self, L, H):
        r = H - L
        return (L + (self.f - EPS) * r, L + (self.f + EPS) * r)

    def __repr__(self):
        return f"Node({self.label}, h={self.h}, f={self.f})"


def build_nodes():
    out = []
    for a in range(-4, 5):
        for b in range(-4, 5):
            if abs(a) + abs(b) <= 4:
                out.append(Node(a, b))
    out.sort(key=lambda n: n.f)
    fs = [n.f for n in out]
    assert len(set(fs)) == len(fs) == 41
    # f = num/(num+den) must equal o/(1+o)
    for n in out:
        o = Fraction(2) ** n.a * Fraction(3) ** n.b
        assert n.f == o / (1 + o)
    return out


NODES = build_nodes()


def sanity():
    fs = [n.f for n in NODES]
    gaps = [b - a for a, b in zip(fs, fs[1:])]
    return {
        "node_count": len(NODES),
        "f_min": str(fs[0]),
        "f_max": str(fs[-1]),
        "min_gap": str(min(gaps)),
        "max_gap": str(max(gaps)),
        "labels_h_le_2": sum(1 for n in NODES if n.h <= 2),
    }


if __name__ == "__main__":
    print(sanity())
