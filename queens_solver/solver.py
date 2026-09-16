"""Binary integer programming model for the Queens puzzle.

Decision variables
    x[r][c] in {0, 1}   -- 1 if a queen sits on cell (r, c)

Constraints
    sum_c x[r][c] = 1                 for every row r
    sum_r x[r][c] = 1                 for every column c
    sum_{(r,c) in R} x[r][c] = 1      for every color region R
    x[r][c] + x[r][c+1]
      + x[r+1][c] + x[r+1][c+1] <= 1  for every 2x2 window

The last family is the "no touching" rule. Two queens can only touch if
they fall inside the same 2x2 window, and the row/column constraints
already stop orthogonal neighbours, so one inequality per window covers
every diagonal case with only (N-1)^2 constraints instead of checking
all pairs.

There is nothing to optimise, so the objective is a constant; the solver
just has to find a feasible point.
"""

from __future__ import annotations

import time
import warnings
from dataclasses import dataclass, field

import pulp

from .board import Cell, Puzzle


class NoSolutionError(RuntimeError):
    """The puzzle has no valid queen placement."""


@dataclass
class Solution:
    queens: list[Cell]
    seconds: float
    stats: dict = field(default_factory=dict)


def build_model(puzzle: Puzzle) -> tuple[pulp.LpProblem, dict[Cell, pulp.LpVariable]]:
    n = puzzle.size
    prob = pulp.LpProblem("queens", pulp.LpMinimize)

    x = {
        (r, c): prob.add_variable(f"x_{r}_{c}", cat=pulp.LpBinary)
        for r in range(n)
        for c in range(n)
    }

    prob += pulp.lpSum([]), "feasibility"

    for r in range(n):
        prob += pulp.lpSum(x[r, c] for c in range(n)) == 1, f"row_{r}"
    for c in range(n):
        prob += pulp.lpSum(x[r, c] for r in range(n)) == 1, f"col_{c}"

    for i, (label, cells) in enumerate(puzzle.region_cells().items()):
        prob += pulp.lpSum(x[cell] for cell in cells) == 1, f"region_{i}"

    for r in range(n - 1):
        for c in range(n - 1):
            prob += (
                x[r, c] + x[r, c + 1] + x[r + 1, c] + x[r + 1, c + 1] <= 1,
                f"touch_{r}_{c}",
            )

    return prob, x


def _default_solver(time_limit: float | None, verbose: bool):
    # PuLP 3.x ships a CBC binary and exposes it as PULP_CBC_CMD. It warns that
    # the class goes away in 4.0 (where CBC becomes an optional extra), which is
    # why requirements pin pulp<4. Nothing for the user to act on, so hide it.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return pulp.PULP_CBC_CMD(msg=verbose, timeLimit=time_limit)


def _solve(prob, x, solver) -> list[Cell] | None:
    prob.solve(solver)
    if pulp.LpStatus[prob.status] != "Optimal":
        return None
    return sorted(cell for cell, var in x.items() if (var.value() or 0) > 0.5)


def solve(
    puzzle: Puzzle,
    *,
    time_limit: float | None = None,
    verbose: bool = False,
    solver=None,
) -> Solution:
    """Solve a puzzle and return the queen positions (0-indexed, sorted by row)."""
    prob, x = build_model(puzzle)
    solver = solver or _default_solver(time_limit, verbose)

    start = time.perf_counter()
    queens = _solve(prob, x, solver)
    elapsed = time.perf_counter() - start

    if queens is None:
        raise NoSolutionError(f"no valid placement ({pulp.LpStatus[prob.status]})")

    return Solution(
        queens=queens,
        seconds=elapsed,
        stats={
            "variables": len(x),
            "constraints": 3 * puzzle.size + (puzzle.size - 1) ** 2,
            "solver": solver.name,
        },
    )


def find_solutions(puzzle: Puzzle, limit: int = 2, *, solver=None) -> list[list[Cell]]:
    """Return up to `limit` distinct solutions.

    After each solve we add a "no-good" cut that forbids that exact set of
    queens (at most N-1 of them may be chosen again) and solve again.
    """
    prob, x = build_model(puzzle)
    solver = solver or _default_solver(None, False)
    n = puzzle.size

    found: list[list[Cell]] = []
    while len(found) < limit:
        queens = _solve(prob, x, solver)
        if queens is None:
            break
        found.append(queens)
        prob += pulp.lpSum(x[q] for q in queens) <= n - 1, f"nogood_{len(found)}"
    return found


def count_solutions(puzzle: Puzzle, limit: int = 2, *, solver=None) -> int:
    """Count distinct solutions, stopping at `limit`. A well-formed puzzle gives 1."""
    return len(find_solutions(puzzle, limit, solver=solver))
