import unittest
from tools.recovery.comparable_coverage import compare

class ComparableCoverageTests(unittest.TestCase):
    def test_same_denominator(self):
        a={"modules":{"a":{"covered_lines":2,"eligible_lines":4,"covered_branches":1,"eligible_branches":2}}}
        b={"modules":{"a":{"covered_lines":3,"eligible_lines":4,"covered_branches":2,"eligible_branches":2}}}
        r=compare(a,b)
        self.assertEqual(r["line_covered_delta"],1)
        self.assertFalse(r["closure_credit"])
    def test_changed_denominator_excluded(self):
        a={"modules":{"a":{"covered_lines":2,"eligible_lines":4,"covered_branches":1,"eligible_branches":2}}}
        b={"modules":{"a":{"covered_lines":3,"eligible_lines":5,"covered_branches":2,"eligible_branches":2}}}
        self.assertEqual(compare(a,b)["cohort"],[])

if __name__=="__main__": unittest.main()
