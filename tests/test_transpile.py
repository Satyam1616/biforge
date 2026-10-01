"""Unit tests for the Tableau-calc -> DAX transpiler. Run: python -m unittest"""
import unittest

from biforge.dax_transpile import transpile


def dax(formula, table="Sales", measures=frozenset()):
    return transpile(formula, table, set(measures))[0]


class TestTranspile(unittest.TestCase):

    def test_arithmetic_and_fieldref(self):
        self.assertEqual(dax("[Profit] / [Sales]"),
                         "( 'Sales'[Profit] / 'Sales'[Sales] )")

    def test_measure_reference(self):
        # a field known to be a measure is referenced without the table
        self.assertEqual(dax("[Profit Ratio] * 100", measures={"Profit Ratio"}),
                         "( [Profit Ratio] * 100 )")

    def test_aggregate_rename(self):
        self.assertEqual(dax("AVG([Sales])"), "AVERAGE ( 'Sales'[Sales] )")

    def test_iif_to_if(self):
        self.assertEqual(dax('IIF([Sales] > 0, "y", "n")'),
                         '''IF ( ( 'Sales'[Sales] > 0 ), "y", "n" )''')

    def test_if_elseif_else(self):
        out = dax('IF [x] >= 2 THEN "a" ELSEIF [x] >= 1 THEN "b" ELSE "c" END')
        self.assertEqual(
            out,
            '''IF ( ( 'Sales'[x] >= 2 ), "a", '''
            '''IF ( ( 'Sales'[x] >= 1 ), "b", "c" ) )''')

    def test_zn(self):
        self.assertEqual(dax("ZN([Sales])"), "COALESCE ( 'Sales'[Sales], 0 )")

    def test_datediff_reorders_and_maps_part(self):
        self.assertEqual(dax("DATEDIFF('day', [a], [b])"),
                         "DATEDIFF ( 'Sales'[a], 'Sales'[b], DAY )")

    def test_contains(self):
        self.assertEqual(dax('CONTAINS([Category], "Tech")'),
                         '''CONTAINSSTRING ( 'Sales'[Category], "Tech" )''')

    def test_and_or_operators(self):
        self.assertEqual(dax("[a] > 1 AND [b] < 2"),
                         "( ( 'Sales'[a] > 1 ) && ( 'Sales'[b] < 2 ) )")

    def test_string_concat_uses_ampersand(self):
        self.assertEqual(dax('[a] + "x"'), '''( 'Sales'[a] & "x" )''')

    def test_unmapped_function_warns(self):
        expr, warns = transpile("INDEX()", "Sales", set())
        self.assertTrue(warns)
        self.assertIn("INDEX", expr)

    def test_syntax_error_raises(self):
        with self.assertRaises(Exception):
            transpile("SUM([Sales]) * ", "Sales", set())


if __name__ == "__main__":
    unittest.main()
