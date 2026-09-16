"""Random puzzle generator.

1. Place N queens that already satisfy the row/column/no-touch rules.
2. Seed one region at each queen and grow the regions outward at random
   until every cell is claimed. This guarantees the placement from step 1
   is a solution and that every region is contiguous.
3. Ask the solver for any *other* solution. If it finds one, pick a cell
   where that rogue solution puts a queen and hand the cell to a
   neighbouring region (see `_break`). That breaks the rogue solution (one region loses
   its queen, another gets two) while keeping the planted one intact.
   Repeat until the planted solution is the only one left.
"""

from __future__ import annotations

import random

import pulp

from .board import Cell, Puzzle
from .solver import _default_solver, _solve, build_model

LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def random_placement(n: int, rng: random.Random) -> list[int]:
    """Return cols[r] = column of the queen in row r, using randomized backtracking."""
    cols: list[int] = []

    def place(r: int) -> bool:
        if r == n:
            return True
        options = list(range(n))
        rng.shuffle(options)
        for c in options:
            if c in cols:
                continue
            if r > 0 and abs(cols[-1] - c) <= 1:
                continue
            cols.append(c)
            if place(r + 1):
                return True
            cols.pop()
        return False

    if not place(0):
        raise ValueError(f"no valid placement exists for n={n}")
    return cols


def grow_regions(n: int, cols: list[int], rng: random.Random) -> list[list[str]]:
    grid = [[""] * n for _ in range(n)]
    frontier = []
    for r, c in enumerate(cols):
        grid[r][c] = LABELS[r]
        frontier.append((r, c))

    while frontier:
        r, c = frontier.pop(rng.randrange(len(frontier)))
        free = [
            (rr, cc)
            for rr, cc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1))
            if 0 <= rr < n and 0 <= cc < n and not grid[rr][cc]
        ]
        if not free:
            continue
        rr, cc = rng.choice(free)
        grid[rr][cc] = grid[r][c]
        frontier.extend([(r, c), (rr, cc)])

    return grid


def other_solution(puzzle: Puzzle, planted: list[Cell]) -> list[Cell] | None:
    """Any valid placement different from `planted`, or None if it's unique."""
    prob, x = build_model(puzzle)
    prob += pulp.lpSum(x[q] for q in planted) <= puzzle.size - 1, "not_planted"
    return _solve(prob, x, _default_solver(None, False))


def _component(cells: set[Cell], start: Cell) -> set[Cell]:
    seen, stack = {start}, [start]
    while stack:
        r, c = stack.pop()
        for nb in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if nb in cells and nb not in seen:
                seen.add(nb)
                stack.append(nb)
    return seen


def _break(grid: list[list[str]], planted: set[Cell], rogue: list[Cell], rng: random.Random) -> bool:
    """Reassign one of the rogue solution's queen cells to a neighbouring region.

    If that cell was holding its region together, the piece that gets cut
    off from the planted queen goes along with it, so every region stays
    contiguous and still contains exactly one planted queen.
    """
    n = len(grid)
    moves = []
    for r, c in rogue:
        if (r, c) in planted:
            continue
        for rr, cc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= rr < n and 0 <= cc < n and grid[rr][cc] != grid[r][c]:
                moves.append(((r, c), grid[rr][cc]))
    if not moves:
        return False

    (r, c), new_label = rng.choice(moves)
    old_label = grid[r][c]
    region = {(i, j) for i in range(n) for j in range(n) if grid[i][j] == old_label}
    anchor = next(q for q in planted if q in region)
    keep = _component(region - {(r, c)}, anchor)
    for i, j in region - keep:
        grid[i][j] = new_label
    return True


def _relabel(grid: list[list[str]]) -> list[list[str]]:
    mapping: dict[str, str] = {}
    for row in grid:
        for ch in row:
            mapping.setdefault(ch, LABELS[len(mapping)])
    return [[mapping[ch] for ch in row] for row in grid]


def generate(n: int, seed: int | None = None, max_attempts: int = 20, max_fixes: int = 200) -> Puzzle:
    """Build a random n x n puzzle with exactly one solution."""
    if not 4 <= n <= len(LABELS):
        raise ValueError("size must be between 4 and 26")
    rng = random.Random(seed)

    for _ in range(max_attempts):
        cols = random_placement(n, rng)
        planted = [(r, c) for r, c in enumerate(cols)]
        grid = grow_regions(n, cols, rng)

        for _ in range(max_fixes):
            puzzle = Puzzle.from_rows(grid)
            rogue = other_solution(puzzle, planted)
            if rogue is None:
                return Puzzle.from_rows(_relabel(grid))
            if not _break(grid, set(planted), rogue, rng):
                break

    raise RuntimeError(f"couldn't build a unique {n}x{n} puzzle, try another seed")
