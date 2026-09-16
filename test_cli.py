import importlib.util
import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import tempfile

from queens_solver import Puzzle, solve
from queens_solver.cli import main

PUZZLES = Path(__file__).resolve().parent.parent / "puzzles"


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    def test_solve(self):
        code, out, _ = run("solve", str(PUZZLES / "medium-8x8.txt"), "--no-color", "--unique")
        self.assertEqual(code, 0)
        self.assertEqual(out.count("Q"), 8 + 1)  # 8 on the board + "Queens (row, col)"
        self.assertIn("Solution is unique.", out)

    def test_no_solution_exit_code(self):
        code, out, _ = run("solve", str(PUZZLES / "no-solution-5x5.txt"), "--no-color")
        self.assertEqual(code, 1)
        self.assertIn("No solution", out)

    def test_missing_file(self):
        code, _, err = run("solve", "does-not-exist.txt")
        self.assertEqual(code, 2)
        self.assertIn("error", err)

    def test_check(self):
        path = str(PUZZLES / "medium-8x8.txt")
        queens = solve(Puzzle.from_file(path)).queens
        good = [f"{r + 1},{c + 1}" for r, c in queens]
        self.assertEqual(run("check", path, *good)[0], 0)
        self.assertEqual(run("check", path, "1,1", "2,2")[0], 1)

    @unittest.skipUnless(importlib.util.find_spec("matplotlib"), "matplotlib not installed")
    def test_generate_and_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            txt, png = Path(tmp, "p.txt"), Path(tmp, "p.png")
            self.assertEqual(run("generate", "6", "--seed", "5", "-o", str(txt))[0], 0)
            code, _, _ = run("solve", str(txt), "--no-color", "--png", str(png))
            self.assertEqual(code, 0)
            self.assertTrue(png.read_bytes().startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
