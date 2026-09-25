import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voidh0.wp2_cove import (
    angular_separation_deg,
    build_diagnosis_table,
    crossmatch_sdss_spec,
    load_pantheon_calibrators,
    summarize,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "mini_pantheon_sh0es.dat"


class TestLoadPantheonCalibrators(unittest.TestCase):
    def test_loads_only_calibrator_rows(self):
        cal = load_pantheon_calibrators(FIXTURE)
        # 3 Zeilen mit IS_CALIBRATOR=1 in der Fixture
        self.assertEqual(len(cal), 3)

    def test_calibrator_cids_correct(self):
        cal = load_pantheon_calibrators(FIXTURE)
        cids = {str(c) for c in cal["CID"]}
        self.assertEqual(cids, {"2011fe", "1994ae", "missinghost"})

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_pantheon_calibrators("/does/not/exist.dat")

    def test_missing_required_column_raises(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            bad_path = Path(d) / "bad.dat"
            bad_path.write_text("CID zHD IS_CALIBRATOR\nfoo 0.01 1\n")
            with self.assertRaises(KeyError):
                load_pantheon_calibrators(bad_path)


class TestAngularSeparation(unittest.TestCase):
    def test_zero_separation_for_identical_points(self):
        sep = angular_separation_deg(10.0, 5.0, 10.0, 5.0)
        self.assertAlmostEqual(float(sep), 0.0, places=8)

    def test_known_separation_along_dec(self):
        # 1 Grad Trennung entlang Dec bei ra konstant, dec nahe 0 (keine
        # cos(dec)-Verzerrung)
        sep = angular_separation_deg(0.0, 0.0, 0.0, 1.0)
        self.assertAlmostEqual(float(sep), 1.0, places=6)

    def test_vectorized_input(self):
        ra2 = np.array([0.0, 1.0, 2.0])
        dec2 = np.array([0.0, 0.0, 0.0])
        sep = angular_separation_deg(0.0, 0.0, ra2, dec2)
        self.assertEqual(len(sep), 3)
        self.assertTrue(np.all(sep >= 0))


class TestCrossmatchSdssSpec(unittest.TestCase):
    def test_finds_close_match_within_radius_and_ztol(self):
        sdss_ra = np.array([10.0, 20.0, 30.0])
        sdss_dec = np.array([5.0, 15.0, 25.0])
        sdss_z = np.array([0.05, 0.06, 0.07])

        matched, sep = crossmatch_sdss_spec(
            10.0002, 5.0001, 0.0502, sdss_ra, sdss_dec, sdss_z,
            radius_arcsec=5.0, z_tol=0.005,
        )
        self.assertTrue(matched)
        self.assertIsNotNone(sep)
        self.assertLess(sep, 5.0)

    def test_no_match_when_too_far(self):
        sdss_ra = np.array([10.0])
        sdss_dec = np.array([5.0])
        sdss_z = np.array([0.05])

        matched, sep = crossmatch_sdss_spec(
            50.0, 40.0, 0.05, sdss_ra, sdss_dec, sdss_z,
            radius_arcsec=3.0, z_tol=0.005,
        )
        self.assertFalse(matched)

    def test_no_match_when_redshift_outside_tolerance(self):
        sdss_ra = np.array([10.0])
        sdss_dec = np.array([5.0])
        sdss_z = np.array([0.20])  # weit weg vom Host-z

        matched, sep = crossmatch_sdss_spec(
            10.0, 5.0, 0.05, sdss_ra, sdss_dec, sdss_z,
            radius_arcsec=5.0, z_tol=0.005,
        )
        self.assertFalse(matched)
        self.assertIsNone(sep)

    def test_empty_sdss_catalog_returns_no_match(self):
        matched, sep = crossmatch_sdss_spec(
            10.0, 5.0, 0.05, np.array([]), np.array([]), np.array([]),
        )
        self.assertFalse(matched)
        self.assertIsNone(sep)


class TestBuildDiagnosisTable(unittest.TestCase):
    def setUp(self):
        self.calibrators = load_pantheon_calibrators(FIXTURE)

    def test_flags_missing_position(self):
        rows = build_diagnosis_table(self.calibrators)
        by_cid = {r.cid: r for r in rows}
        self.assertFalse(by_cid["missinghost"].has_position)
        self.assertTrue(by_cid["2011fe"].has_position)
        self.assertTrue(by_cid["1994ae"].has_position)

    def test_position_source_host_when_host_fields_filled(self):
        rows = build_diagnosis_table(self.calibrators)
        by_cid = {r.cid: r for r in rows}
        self.assertEqual(by_cid["1994ae"].position_source, "host")

    def test_position_source_falls_back_to_sn_position(self):
        # 2011fe hat HOST_RA/HOST_DEC == -999, aber gefuellte RA/DEC --
        # genau der empirische Befund aus dem echten Pantheon+SH0ES.dat-Lauf.
        rows = build_diagnosis_table(self.calibrators)
        by_cid = {r.cid: r for r in rows}
        self.assertEqual(by_cid["2011fe"].position_source, "sn_position")
        self.assertAlmostEqual(by_cid["2011fe"].host_ra, 210.774, places=3)
        self.assertAlmostEqual(by_cid["2011fe"].host_dec, 54.2737, places=3)

    def test_position_source_missing_when_both_absent(self):
        rows = build_diagnosis_table(self.calibrators)
        by_cid = {r.cid: r for r in rows}
        self.assertEqual(by_cid["missinghost"].position_source, "missing")

    def test_sdss_flag_none_without_sdss_data(self):
        rows = build_diagnosis_table(self.calibrators)
        for r in rows:
            self.assertIsNone(r.sdss_spec_match)

    def test_sdss_flag_set_with_sdss_data(self):
        # SDSS-Tracer exakt am Host von 2011fe platziert (210.774, 54.2737,
        # z=0.00122), plus ein irrelevanter weit entfernter Tracer.
        sdss_ra = np.array([210.774, 0.0])
        sdss_dec = np.array([54.2737, 0.0])
        sdss_z = np.array([0.00122, 0.5])

        rows = build_diagnosis_table(self.calibrators, sdss_ra, sdss_dec, sdss_z)
        by_cid = {r.cid: r for r in rows}
        self.assertTrue(by_cid["2011fe"].sdss_spec_match)
        self.assertFalse(by_cid["1994ae"].sdss_spec_match)

    def test_missing_position_skips_sdss_check(self):
        sdss_ra = np.array([0.0])
        sdss_dec = np.array([0.0])
        sdss_z = np.array([0.01])
        rows = build_diagnosis_table(self.calibrators, sdss_ra, sdss_dec, sdss_z)
        by_cid = {r.cid: r for r in rows}
        # kein Crossmatch versucht, wenn schon Flag 1 fehlschlaegt
        self.assertIsNone(by_cid["missinghost"].sdss_spec_match)

    def test_environment_lookup_applied(self):
        lookup = {"2011fe": (True, "void")}
        rows = build_diagnosis_table(self.calibrators, environment_lookup=lookup)
        by_cid = {r.cid: r for r in rows}
        self.assertTrue(by_cid["2011fe"].environment_robust)
        self.assertEqual(by_cid["2011fe"].environment_class, "void")
        self.assertIsNone(by_cid["1994ae"].environment_class)


class TestSummarize(unittest.TestCase):
    def test_cumulative_counts(self):
        calibrators = load_pantheon_calibrators(FIXTURE)
        sdss_ra = np.array([210.774])
        sdss_dec = np.array([54.2737])
        sdss_z = np.array([0.00122])

        rows = build_diagnosis_table(calibrators, sdss_ra, sdss_dec, sdss_z)
        summary = summarize(rows)

        self.assertEqual(summary["n_total_calibrators"], 3)
        self.assertEqual(summary["n_with_position"], 2)  # missinghost fehlt
        self.assertEqual(summary["n_sdss_spec_match"], 1)  # nur 2011fe matcht
        self.assertEqual(summary["n_environment_robust"], 0)  # kein Lookup uebergeben


if __name__ == "__main__":
    unittest.main()
