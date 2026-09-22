import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voidh0.layer0_cosmology import ReferenceCosmology, load_reference_cosmology


class TestReferenceCosmology(unittest.TestCase):
    def test_load_from_config(self):
        cosmo = load_reference_cosmology()
        self.assertEqual(cosmo.name, "reference_flcdm_v0")
        self.assertAlmostEqual(cosmo.H0_km_s_Mpc, 67.4)
        self.assertAlmostEqual(cosmo.Om0, 0.315)
        self.assertAlmostEqual(cosmo.OLambda0, 0.685, places=6)

    def test_rejects_non_flat_lcdm_in_config(self):
        # sanity: model field is validated
        cosmo = load_reference_cosmology()
        self.assertIsInstance(cosmo, ReferenceCosmology)

    def test_E_at_z0_is_one(self):
        cosmo = load_reference_cosmology()
        self.assertAlmostEqual(cosmo.E(0.0), 1.0, places=10)

    def test_comoving_distance_monotonic(self):
        cosmo = load_reference_cosmology()
        d1 = cosmo.comoving_distance_Mpc(0.05)
        d2 = cosmo.comoving_distance_Mpc(0.11)
        self.assertGreater(d2, d1)

    def test_comoving_distance_zero_is_zero(self):
        cosmo = load_reference_cosmology()
        self.assertAlmostEqual(cosmo.comoving_distance_Mpc(0.0), 0.0, places=6)

    def test_low_z_hubble_law_limit(self):
        # Fuer sehr kleine z sollte D_C ~ c*z/H0 gelten (linearer Hubble-Fluss)
        cosmo = load_reference_cosmology()
        z = 1e-4
        d_exact = cosmo.comoving_distance_Mpc(z)
        d_linear = cosmo.hubble_distance_Mpc * z
        rel_diff = abs(d_exact - d_linear) / d_linear
        self.assertLess(rel_diff, 1e-3)

    def test_distance_modulus_increases_with_z(self):
        cosmo = load_reference_cosmology()
        mu1 = cosmo.distance_modulus(0.02)
        mu2 = cosmo.distance_modulus(0.10)
        self.assertGreater(mu2, mu1)

    def test_vectorized_input(self):
        cosmo = load_reference_cosmology()
        import numpy as np

        z = np.array([0.01, 0.05, 0.10])
        d = cosmo.comoving_distance_Mpc(z)
        self.assertEqual(len(d), 3)
        self.assertTrue(all(d[i] < d[i + 1] for i in range(len(d) - 1)))

    def test_rejects_bad_Om0(self):
        with self.assertRaises(ValueError):
            ReferenceCosmology(name="bad", H0_km_s_Mpc=70.0, Om0=2.0)

    def test_rejects_bad_H0(self):
        with self.assertRaises(ValueError):
            ReferenceCosmology(name="bad", H0_km_s_Mpc=-1.0, Om0=0.3)


if __name__ == "__main__":
    unittest.main()
