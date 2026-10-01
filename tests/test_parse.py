"""End-to-end parse + pipeline tests over the bundled sample workbook."""
import os
import unittest

from biforge.cli import run

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "samples",
                      "SuperstoreSample.twb")


class TestPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.res = run(SAMPLE, os.path.join(os.path.dirname(__file__),
                                           "_out"), want_json=True)

    def test_parses_assets(self):
        c = self.res["validation"]["counts"]
        self.assertEqual(c["datasources"], 1)
        self.assertEqual(c["worksheets"], 4)
        self.assertEqual(c["dashboards"], 1)
        self.assertGreaterEqual(c["calculated_fields"], 10)

    def test_broken_calc_is_failed_not_fatal(self):
        statuses = {c["name"]: c["status"]
                    for c in self.res["conversion"]["conversions"]}
        self.assertEqual(statuses["Broken Calc"], "failed")

    def test_profit_ratio_is_measure(self):
        recs = {c["name"]: c for c in self.res["conversion"]["conversions"]}
        self.assertEqual(recs["Profit Ratio"]["kind"], "measure")

    def test_similarity_detects_duplicate_region_sheets(self):
        clusters = self.res["analysis"]["clusters"]
        flat = [name for grp in clusters for name in grp]
        self.assertIn("Profit by Region", flat)
        self.assertIn("Profit by Region (copy)", flat)

    def test_orphan_reference_flagged(self):
        orphans = {ref for _, ref in self.res["validation"]["orphan_refs"]}
        self.assertIn("[Ghost Field]", orphans)

    def test_output_files_written(self):
        names = {os.path.basename(p) for p in self.res["written"]}
        self.assertIn("model.tmdl", names)
        self.assertIn("measures.dax", names)
        self.assertIn("assessment.md", names)


if __name__ == "__main__":
    unittest.main()
