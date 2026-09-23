import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voidh0.layer1_tracers.mask_randoms import (
    build_footprint_mask,
    sample_positions_in_mask,
    sample_redshifts_from_nz,
)


class TestBuildFootprintMask(unittest.TestCase):
    def test_rejects_empty_catalog(self):
        with self.assertRaises(ValueError):
            build_footprint_mask(np.array([]), np.array([]))

    def test_all_cells_occupied_for_dense_uniform_catalog(self):
        rng = np.random.default_rng(0)
        ra = rng.uniform(150, 160, 5000)
        dec = rng.uniform(0, 10, 5000)
        mask = build_footprint_mask(ra, dec, cell_size_deg=1.0, min_objects_per_cell=1)
        # bei so dichter, uniformer Abdeckung sollten praktisch alle Zellen belegt sein
        self.assertGreater(mask.n_occupied_cells / mask.n_total_cells, 0.9)

    def test_sparse_catalog_leaves_some_cells_empty(self):
        rng = np.random.default_rng(1)
        ra = rng.uniform(150, 160, 5)
        dec = rng.uniform(0, 10, 5)
        mask = build_footprint_mask(ra, dec, cell_size_deg=0.5, min_objects_per_cell=1)
        self.assertLess(mask.n_occupied_cells, mask.n_total_cells)

    def test_min_objects_per_cell_increases_strictness(self):
        rng = np.random.default_rng(2)
        ra = rng.uniform(150, 151, 200)
        dec = rng.uniform(0, 1, 200)
        loose = build_footprint_mask(ra, dec, cell_size_deg=0.2, min_objects_per_cell=1)
        strict = build_footprint_mask(ra, dec, cell_size_deg=0.2, min_objects_per_cell=20)
        self.assertGreaterEqual(loose.n_occupied_cells, strict.n_occupied_cells)

    def test_solid_angle_positive_and_less_than_full_sky(self):
        rng = np.random.default_rng(3)
        ra = rng.uniform(150, 160, 2000)
        dec = rng.uniform(0, 10, 2000)
        mask = build_footprint_mask(ra, dec, cell_size_deg=1.0)
        area = mask.solid_angle_deg2()
        self.assertGreater(area, 0.0)
        self.assertLess(area, 41253.0)  # Flaeche der gesamten Himmelskugel in deg^2

    def test_solid_angle_roughly_matches_flat_approx_at_low_dec(self):
        # Nahe dec=0 sollte die sphaerische Flaeche nah an der flachen
        # RA*Dec-Naeherung liegen (kleine Winkel, kein Pol-Effekt).
        rng = np.random.default_rng(4)
        ra = rng.uniform(0, 10, 3000)
        dec = rng.uniform(-5, 5, 3000)
        mask = build_footprint_mask(ra, dec, cell_size_deg=1.0, min_objects_per_cell=1)
        flat_approx = 10.0 * 10.0
        area = mask.solid_angle_deg2()
        self.assertAlmostEqual(area, flat_approx, delta=0.15 * flat_approx)


class TestSamplePositionsInMask(unittest.TestCase):
    def test_returns_requested_count(self):
        rng = np.random.default_rng(0)
        ra = rng.uniform(150, 160, 2000)
        dec = rng.uniform(0, 10, 2000)
        mask = build_footprint_mask(ra, dec, cell_size_deg=1.0)
        ra_r, dec_r = sample_positions_in_mask(mask, 500, np.random.default_rng(5))
        self.assertEqual(len(ra_r), 500)
        self.assertEqual(len(dec_r), 500)

    def test_samples_within_mask_bounds(self):
        rng = np.random.default_rng(0)
        ra = rng.uniform(150, 160, 2000)
        dec = rng.uniform(0, 10, 2000)
        mask = build_footprint_mask(ra, dec, cell_size_deg=1.0)
        ra_r, dec_r = sample_positions_in_mask(mask, 1000, np.random.default_rng(6))
        self.assertTrue((ra_r >= mask.ra_edges_deg[0]).all())
        self.assertTrue((ra_r <= mask.ra_edges_deg[-1]).all())
        self.assertTrue((dec_r >= mask.dec_edges_deg[0]).all())
        self.assertTrue((dec_r <= mask.dec_edges_deg[-1]).all())

    def test_zero_samples_returns_empty(self):
        rng = np.random.default_rng(0)
        ra = rng.uniform(150, 160, 100)
        dec = rng.uniform(0, 10, 100)
        mask = build_footprint_mask(ra, dec, cell_size_deg=1.0)
        ra_r, dec_r = sample_positions_in_mask(mask, 0, np.random.default_rng(7))
        self.assertEqual(len(ra_r), 0)
        self.assertEqual(len(dec_r), 0)

    def test_reproducible_with_seeded_rng(self):
        rng = np.random.default_rng(0)
        ra = rng.uniform(150, 160, 500)
        dec = rng.uniform(0, 10, 500)
        mask = build_footprint_mask(ra, dec, cell_size_deg=1.0)
        ra_r1, dec_r1 = sample_positions_in_mask(mask, 200, np.random.default_rng(42))
        ra_r2, dec_r2 = sample_positions_in_mask(mask, 200, np.random.default_rng(42))
        np.testing.assert_allclose(ra_r1, ra_r2)
        np.testing.assert_allclose(dec_r1, dec_r2)


class TestSampleRedshiftsFromNz(unittest.TestCase):
    def test_rejects_empty_observed(self):
        with self.assertRaises(ValueError):
            sample_redshifts_from_nz(np.array([]), 10, np.random.default_rng(0))

    def test_zero_samples_returns_empty(self):
        out = sample_redshifts_from_nz(np.array([0.05, 0.06]), 0, np.random.default_rng(0))
        self.assertEqual(len(out), 0)

    def test_drawn_values_are_from_observed_set_without_smoothing(self):
        z_obs = np.array([0.02, 0.05, 0.08, 0.11])
        drawn = sample_redshifts_from_nz(z_obs, 100, np.random.default_rng(1), smoothing_sigma=0.0)
        self.assertTrue(np.isin(drawn, z_obs).all())

    def test_smoothing_perturbs_values(self):
        z_obs = np.array([0.05] * 50)
        drawn = sample_redshifts_from_nz(z_obs, 200, np.random.default_rng(2), smoothing_sigma=0.01)
        self.assertGreater(np.std(drawn), 0.0)

    def test_smoothing_never_negative(self):
        z_obs = np.array([0.001] * 50)
        drawn = sample_redshifts_from_nz(z_obs, 500, np.random.default_rng(3), smoothing_sigma=0.01)
        self.assertTrue((drawn >= 0.0).all())

    def test_mean_roughly_matches_observed_distribution(self):
        rng = np.random.default_rng(4)
        z_obs = rng.normal(0.06, 0.02, size=5000)
        z_obs = z_obs[z_obs > 0]
        drawn = sample_redshifts_from_nz(z_obs, 5000, np.random.default_rng(5))
        self.assertAlmostEqual(np.mean(drawn), np.mean(z_obs), delta=0.01)


if __name__ == "__main__":
    unittest.main()
