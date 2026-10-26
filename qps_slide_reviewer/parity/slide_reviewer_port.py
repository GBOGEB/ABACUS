#!/usr/bin/env python3
"""Faithful Python port of the slide-reviewer lib/stats.ts bradleyTerry + pca,
used ONLY to numerically compare the app's consumer implementation against the
gg_MATH canonical kernels. Not committed to any repo as runtime code.
"""
from __future__ import annotations
import math


def sr_bradley_terry(ids, comps, iterations=200, prior=0.1):
    n = len(ids)
    idx = {id_: i for i, id_ in enumerate(ids)}
    wins = [0.0] * n
    losses = [0.0] * n
    nij = [[0.0] * n for _ in range(n)]
    wij = [[0.0] * n for _ in range(n)]
    for c in comps:
        a = idx.get(c['slideAId'])
        b = idx.get(c['slideBId'])
        if a is None or b is None or a == b:
            continue
        if c.get('isTie') or c.get('winnerId') is None:
            wij[a][b] += 0.5
            wij[b][a] += 0.5
            nij[a][b] += 1
            nij[b][a] += 1
            continue
        w = idx.get(c['winnerId'])
        if w is None:
            continue
        l = b if w == a else a
        wins[w] += 1
        losses[l] += 1
        wij[w][l] += 1
        nij[a][b] += 1
        nij[b][a] += 1
    pi = [1.0] * n
    for _ in range(iterations):
        nxt = [0.0] * n
        for i in range(n):
            W = prior
            denom = 0.0
            for j in range(n):
                if i == j:
                    continue
                W += wij[i][j]
                if nij[i][j] > 0:
                    denom += nij[i][j] / (pi[i] + pi[j])
            denom += prior * 2 / (pi[i] + 1)
            nxt[i] = W / denom
        gm = math.exp(sum(math.log(v) for v in nxt) / n)
        pi = [v / gm for v in nxt]
    return {ids[i]: pi[i] for i in range(n)}


def sr_pca(ids, features, matrix, n_components=3):
    n = len(matrix)
    m = len(features)
    means = [sum(r[j] for r in matrix) / n for j in range(m)]
    sds = []
    for j in range(m):
        v = sum((r[j] - means[j]) ** 2 for r in matrix) / (n - 1)
        sds.append(math.sqrt(v) or 1.0)
    Z = [[(r[j] - means[j]) / sds[j] for j in range(m)] for r in matrix]
    C = [[sum(Z[r][i] * Z[r][j] for r in range(n)) / (n - 1) for j in range(m)] for i in range(m)]
    total_var = sum(C[i][i] for i in range(m)) or 1.0
    comps = []
    eig = []
    A = [row[:] for row in C]
    for _k in range(min(n_components, m)):
        v = [1 + i * 0.01 for i in range(m)]
        lam = 0.0
        for _ in range(500):
            Av = [sum(A[i][j] * v[j] for j in range(m)) for i in range(m)]
            norm = math.sqrt(sum(x * x for x in Av))
            if norm < 1e-12:
                lam = 0.0
                v = [0.0] * m
                break
            v = [x / norm for x in Av]
            lam = norm
        comps.append(v)
        eig.append(lam)
        A = [[A[i][j] - lam * v[i] * v[j] for j in range(m)] for i in range(m)]
    return {
        'explained_variance': [e / total_var for e in eig],
        'eigenvalues': eig,
        'components': comps,
    }
