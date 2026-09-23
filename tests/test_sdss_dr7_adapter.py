import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

try:
    import astropy  # noqa: F401

    HAS_ASTROPY = True
except ImportError:
    HAS_ASTROPY = False

from voidh0.layer1_tracers import SDSSDR7TracerAdapter

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CATALOG = FIXTURES / "mini_sdss_dr7_sample.dat"
RANDOMS = FIXTURES / "mini_sdss_dr7_randoms.dat"


@unittest.skipUnless(HAS_ASTROPY, "astropy nicht installiert -- SDSSDR7TracerAdapter uebersprungen")
class TestSDSSDR7TracerAdapter(unittest.TestCase):
    def test_load_applies_redshift_and_magnitude_cut(self):
        adapter = SDSSDR7TracerAdapter(
            catalog_path=CATALOG, z_min=0.0, z_max=0.114, magnitude_limit=-20.09
        )
        cat = adapter.load()

        objs = ~cat.is_random
        self.assertTrue((cat.z[objs] <= 0.114).all())
        self.assertTrue((cat.extra["rabsmag"] <= -20.09).all())
        self.assertGreater(cat.n_objects, 0)
        self.assertLess(cat.n_objects, 40)  # Schnitt muss tatsaechlich etwas entfernen

    def test_no_randoms_by_default(self):
        adapter = SDSSDR7TracerAdapter(catalog_path=CATALOG)
        cat = adapter.load()
        self.assertEqual(cat.n_randoms, 0)

    def test_synthetic_randoms_flagged_correctly(self):
        adapter = SDSSDR7TracerAdapter(catalog_path=CATALOG, n_synthetic_randoms=50, seed=1)
        cat = adapter.load()
        self.assertEqual(cat.n_randoms, 50)

    def test_mask_mode_is_default_and_uses_gridded_mask(self):
        adapter = SDSSDR7TracerAdapter(catalog_path=CATALOG, n_synthetic_randoms=100, seed=2)
        self.assertEqual(adapter._randoms_mode, "mask")
        cat = adapter.load()
        self.assertEqual(cat.n_randoms, 100)
        # Nach dem Lauf sollte die gepixelte Maske gecacht sein und eine
        # sphaerisch korrekte Flaeche liefern.
        area = adapter.footprint_area_deg2()
        self.assertGreater(area, 0.0)

    def test_bbox_mode_still_available_for_comparison(self):
        adapter = SDSSDR7TracerAdapter(
            catalog_path=CATALOG, n_synthetic_randoms=50, seed=3, randoms_mode="bbox"
        )
        cat = adapter.load()
        self.assertEqual(cat.n_randoms, 50)

    def test_rejects_invalid_randoms_mode(self):
        with self.assertRaises(ValueError):
            SDSSDR7TracerAdapter(catalog_path=CATALOG, randoms_mode="nonsense")

    def test_mask_mode_random_redshifts_within_observed_range(self):
        adapter = SDSSDR7TracerAdapter(
            catalog_path=CATALOG, z_min=0.0, z_max=0.114, n_synthetic_randoms=200, seed=4
        )
        cat = adapter.load()
        z_randoms = cat.z[cat.is_random]
        # z(randoms) muss aus der beobachteten n(z) resampled sein, also
        # innerhalb des beobachteten Wertebereichs liegen (Default: kein Jitter).
        z_objects = cat.z[~cat.is_random]
        self.assertGreaterEqual(z_randoms.min(), z_objects.min() - 1e-9)
        self.assertLessEqual(z_randoms.max(), z_objects.max() + 1e-9)

    def test_real_randoms_file_is_used(self):
        adapter = SDSSDR7TracerAdapter(catalog_path=CATALOG, randoms_path=RANDOMS)
        cat = adapter.load()
        self.assertGreater(cat.n_randoms, 0)
        self.assertEqual(cat.n_objects + cat.n_randoms, len(cat))

    def test_missing_file_raises(self):
        adapter = SDSSDR7TracerAdapter(catalog_path=FIXTURES / "does_not_exist.dat")
        with self.assertRaises(FileNotFoundError):
            adapter.load()

    def test_footprint_area_after_load(self):
        adapter = SDSSDR7TracerAdapter(catalog_path=CATALOG)
        with self.assertRaises(RuntimeError):
            adapter.footprint_area_deg2()
        adapter.load()
        area = adapter.footprint_area_deg2()
        self.assertGreater(area, 0.0)

    def test_redshift_limits_reported(self):
        adapter = SDSSDR7TracerAdapter(catalog_path=CATALOG, z_min=0.01, z_max=0.1)
        self.assertEqual(adapter.redshift_limits(), (0.01, 0.1))


if __name__ == "__main__":
    unittest.main()
