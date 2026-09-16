import unittest

from queens_solver.board import Puzzle, PuzzleError, check_solution

SMALL = """
# comment lines and blank lines are ignored

AAAB
CCAB
CDDB
CDDD
"""


class ParsingTests(unittest.TestCase):
    def test_parses_and_ignores_comments(self):
        p = Puzzle.from_text(SMALL)
        self.assertEqual(p.size, 4)
        self.assertEqual(p.labels, ["A", "B", "C", "D"])

    def test_spaces_between_cells_are_allowed(self):
        p = Puzzle.from_text("A A A B\nC C A B\nC D D B\nC D D D")
        self.assertEqual(p, Puzzle.from_text(SMALL))

    def test_round_trip(self):
        p = Puzzle.from_text(SMALL)
        self.assertEqual(Puzzle.from_text(p.to_text()), p)

    def test_rejects_non_square(self):
        with self.assertRaises(PuzzleError):
            Puzzle.from_text("AAB\nCCB")

    def test_rejects_wrong_region_count(self):
        with self.assertRaises(PuzzleError):
            Puzzle.from_text("AAAA\nAAAA\nBBBB\nCCCC")

    def test_rejects_empty(self):
        with self.assertRaises(PuzzleError):
            Puzzle.from_text("# nothing here\n")

    def test_disconnected_regions(self):
        p = Puzzle.from_text("ABAC\nBBCC\nDDDD\nDDDD")
        self.assertEqual(p.disconnected_regions(), ["A"])
        self.assertEqual(Puzzle.from_text(SMALL).disconnected_regions(), [])


class RuleCheckTests(unittest.TestCase):
    def setUp(self):
        self.p = Puzzle.from_text(SMALL)
        # A=(0,1) B=(1,3) C=(2,0) D=(3,2) -- satisfies every rule
        self.good = [(0, 1), (1, 3), (2, 0), (3, 2)]

    def test_valid_solution(self):
        self.assertEqual(check_solution(self.p, self.good), [])

    def test_same_row(self):
        problems = check_solution(self.p, [(0, 0), (0, 3), (2, 1), (3, 2)])
        self.assertIn("row 1 has 2 queens", problems)

    def test_same_region(self):
        problems = check_solution(self.p, [(0, 0), (1, 2), (2, 3), (3, 1)])
        self.assertTrue(any("region 'A' has 2" in m for m in problems))

    def test_diagonal_touch_is_illegal(self):
        problems = check_solution(self.p, [(0, 2), (1, 3), (2, 0), (3, 1)])
        self.assertTrue(any("touch" in m for m in problems))

    def test_same_long_diagonal_is_fine(self):
        # Unlike chess queens, only *adjacent* diagonals are forbidden.
        p = Puzzle.from_text("ABBBB\nAACCB\nDDCCB\nDDEEE\nDDEEE")
        queens = [(0, 0), (1, 2), (2, 4), (3, 1), (4, 3)]
        self.assertEqual(check_solution(p, queens), [])

    def test_off_board(self):
        self.assertTrue(check_solution(self.p, [(9, 9)]))


if __name__ == "__main__":
    unittest.main()
