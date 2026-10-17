"""Global maximum-weight matching on the feasible graph (general graph, not bipartite).

Components are solved exactly: bitmask DP for small ones, Edmonds' blossom
(networkx, optional) for larger ones, greedy as a last resort. No dependency is
required for correctness of the small, typical case (median feasible degree ~1).
"""
import sys


def _components(edges):
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b, _ in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    comps = {}
    for a, b, w in edges:
        comps.setdefault(find(a), []).append((a, b, w))
    return list(comps.values())


def _exact(edges):
    nodes = sorted({x for a, b, _ in edges for x in (a, b)})
    idx = {n: i for i, n in enumerate(nodes)}
    adj = {i: [] for i in range(len(nodes))}
    for a, b, w in edges:
        adj[idx[a]].append((idx[b], w))
        adj[idx[b]].append((idx[a], w))
    memo = {}

    def solve(mask):
        # mask: set of still-undecided nodes
        if not mask:
            return 0.0, ()
        if mask in memo:
            return memo[mask]
        v = (mask & -mask).bit_length() - 1
        rest = mask & ~(1 << v)
        best = solve(rest)
        for u, w in adj[v]:
            if rest >> u & 1:
                sub = solve(rest & ~(1 << u))
                val = sub[0] + w
                if val > best[0] + 1e-15:
                    best = (val, sub[1] + ((v, u),))
        memo[mask] = best
        return best
    _, pairs = solve((1 << len(nodes)) - 1)
    return [(nodes[v], nodes[u]) for v, u in pairs]


def _greedy(edges):
    used, out = set(), []
    for a, b, w in sorted(edges, key=lambda e: (-e[2], e[0], e[1])):
        if a not in used and b not in used:
            used.update((a, b))
            out.append((a, b))
    return out


def max_weight_matching(edges, exact_limit=16, blossom_edge_limit=4000, use_blossom=True):
    """edges: list of (a, b, weight>0). Returns list of (a, b)."""
    out = []
    for comp in _components(edges):
        n = len({x for a, b, _ in comp for x in (a, b)})
        if n <= exact_limit:
            out += _exact(comp)
            continue
        if use_blossom and len(comp) <= blossom_edge_limit:
            try:
                import networkx as nx
                g = nx.Graph()
                for a, b, w in comp:
                    g.add_edge(a, b, weight=w)
                out += [tuple(sorted(p)) for p in nx.max_weight_matching(g)]
                continue
            except Exception as err:  # networkx missing or failed: degrade, never crash
                print('blossom unavailable, greedy fallback: %r' % (err,), file=sys.stderr)
        out += _greedy(comp)
    return out


def greedy_matching(edges):
    return _greedy(edges)
