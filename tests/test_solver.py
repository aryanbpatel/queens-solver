"""Solver tests.

The ILP is cross-checked against a dumb brute-force search on lots of
random boards, including ones with zero or several solutions.
"""

import random
import unittest
from itertools import permutations
from pathlib import Path

from queens_solver import NoSolutionError, Puzzle, check_solution, count_solutions, solve
from queens_solver.generator import generate, grow_regions, random_placement
from queens_solver.solver import find_solutions

PUZZLES = Path(__file__).resolve().parent.parent / "puzzles"


def brute_force(puzzle: Puzzle) -> list[list[tuple[int, int]]]:
    """Try every column permutation. Only usable up to ~8x8."""
    n = puzzle.size
    out = []
    for cols in permutations(range(n)):
        queens = list(enumerate(cols))
        if not check_solution(puzzle, queens):
            out.append(queens)
    return out


def random_board(n: int, rng: random.Random) -> Puzzle:
    """Random contiguous regions -- may have 0, 1 or many solutions."""
    seeds = rng.sample([(r, c) for r in range(n) for c in range(n)], n)
    grid = [[""] * n for _ in range(n)]
    frontier = []
    for i, (r, c) in enumerate(seeds):
        grid[r][c] = "ABCDEFGHIJ"[i]
        frontier.append((r, c))
    while frontier:
        r, c = frontier.pop(rng.randrange(len(frontier)))
        free = [(a, b) for a, b in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1))
                if 0 <= a < n and 0 <= b < n and not grid[a][b]]
        if free:
            a, b = rng.choice(free)
            grid[a][b] = grid[r][c]
            frontier += [(r, c), (a, b)]
    return Puzzle.from_rows(grid)


class SolverTests(unittest.TestCase):
    def test_example_puzzles_solve_uniquely(self):
        files = sorted(PUZZLES.glob("*.txt"))
        self.assertTrue(files, "no example puzzles found")
        for path in files:
            with self.subTest(puzzle=path.name):
                puzzle = Puzzle.from_file(path)
                if path.name.startswith("no-solution"):
                    with self.assertRaises(NoSolutionError):
                        solve(puzzle)
                    continue
                result = solve(puzzle)
                self.assertEqual(check_solution(puzzle, result.queens), [])
                self.assertEqual(count_solutions(puzzle), 1)

    def test_matches_brute_force_on_random_boards(self):
        rng = random.Random(1234)
        outcomes = {"none": 0, "unique": 0, "multiple": 0}
        for _ in range(60):
            n = rng.choice([4, 5, 6, 7])
            puzzle = random_board(n, rng)
            expected = brute_force(puzzle)
            with self.subTest(board=puzzle.to_text()):
                found = find_solutions(puzzle, limit=len(expected) + 1)
                self.assertEqual(sorted(found), sorted(expected))
                if expected:
                    self.assertIn(solve(puzzle).queens, expected)
                else:
                    with self.assertRaises(NoSolutionError):
                        solve(puzzle)
            key = "none" if not expected else "unique" if len(expected) == 1 else "multiple"
            outcomes[key] += 1
        # make sure the random boards actually exercised every case
        self.assertTrue(all(outcomes.values()), outcomes)

    def test_count_solutions_respects_limit(self):
        # four 2x2 blocks leave room for more than one answer
        puzzle = Puzzle.from_text("AABB\nAABB\nCCDD\nCCDD")
        self.assertEqual(count_solutions(puzzle, limit=1), 1)
        self.assertEqual(count_solutions(puzzle, limit=10), len(brute_force(puzzle)))


class GeneratorTests(unittest.TestCase):
    def test_random_placement_is_legal(self):
        rng = random.Random(7)
        for n in range(4, 12):
            cols = random_placement(n, rng)
            self.assertEqual(sorted(cols), list(range(n)))
            self.assertTrue(all(abs(a - b) > 1 for a, b in zip(cols, cols[1:])))

    def test_regions_contain_planted_solution(self):
        rng = random.Random(3)
        cols = random_placement(8, rng)
        puzzle = Puzzle.from_rows(grow_regions(8, cols, rng))
        self.assertEqual(check_solution(puzzle, list(enumerate(cols))), [])
        self.assertEqual(puzzle.disconnected_regions(), [])

    def test_generated_puzzles_are_unique_and_contiguous(self):
        for n, seed in [(5, 1), (6, 2), (8, 3), (9, 4)]:
            with self.subTest(n=n):
                puzzle = generate(n, seed=seed)
                self.assertEqual(puzzle.size, n)
                self.assertEqual(puzzle.disconnected_regions(), [])
                self.assertEqual(count_solutions(puzzle, limit=2), 1)

    def test_same_seed_same_puzzle(self):
        self.assertEqual(generate(7, seed=99), generate(7, seed=99))


if __name__ == "__main__":
    unittest.main()
