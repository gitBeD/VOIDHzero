import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voidh0.layer4_statistics import Blinder, fit_environment_step


class TestFitEnvironmentStep(unittest.TestCase):
    def test_recovers_known_injected_step(self):
        rng = np.random.default_rng(0)
        n = 4000
        env = rng.integers(0, 2, size=n).astype(float)
        mass = rng.normal(10.0, 0.5, size=n)
        true_env_step = 0.08  # mag
        true_mass_slope = 0.03
        noise = rng.normal(0, 0.1, size=n)

        residual = true_env_step * env + true_mass_slope * (mass - mass.mean()) + noise

        result = fit_environment_step(residual, env, mass)
        env_val, env_err = result.env_step_mag()

        self.assertAlmostEqual(env_val, true_env_step, delta=5 * env_err)
        self.assertGreater(result.env_step_significance(), 3.0)

    def test_no_step_when_none_injected(self):
        rng = np.random.default_rng(1)
        n = 3000
        env = rng.integers(0, 2, size=n).astype(float)
        mass = rng.normal(10.0, 0.5, size=n)
        residual = rng.normal(0, 0.12, size=n)

        result = fit_environment_step(residual, env, mass)
        self.assertLess(result.env_step_significance(), 3.0)

    def test_with_optional_sSFR_column(self):
        rng = np.random.default_rng(2)
        n = 500
        env = rng.integers(0, 2, size=n).astype(float)
        mass = rng.normal(10.0, 0.5, size=n)
        sSFR = rng.normal(-10.0, 1.0, size=n)
        residual = rng.normal(0, 0.1, size=n)

        result = fit_environment_step(residual, env, mass, log_sSFR=sSFR)
        self.assertIn("sSFR_c", result.param_names)
        self.assertEqual(len(result.beta), 4)

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            fit_environment_step(
                np.array([0.1, 0.2]), np.array([0, 1, 1]), np.array([10.0, 10.1])
            )


class TestBlinder(unittest.TestCase):
    def test_deterministic_offset(self):
        b1 = Blinder(secret_seed="my-secret")
        b2 = Blinder(secret_seed="my-secret")
        self.assertEqual(b1.offset_mag, b2.offset_mag)

    def test_different_seeds_differ(self):
        b1 = Blinder(secret_seed="seed-a")
        b2 = Blinder(secret_seed="seed-b")
        self.assertNotEqual(b1.offset_mag, b2.offset_mag)

    def test_blind_unblind_roundtrip(self):
        b = Blinder(secret_seed="round-trip")
        data = np.array([0.0, 0.1, -0.2, 0.05])
        blinded = b.blind(data)
        recovered = b.unblind(blinded)
        np.testing.assert_allclose(recovered, data)

    def test_offset_within_bounds(self):
        b = Blinder(secret_seed="bounds-test", max_abs_offset_mag=0.1)
        self.assertLessEqual(abs(b.offset_mag), 0.1)

    def test_commitment_hash_is_stable_and_hides_seed(self):
        b = Blinder(secret_seed="hidden-seed")
        h = b.commitment_hash()
        self.assertEqual(len(h), 64)  # sha256 hex digest length
        self.assertNotIn("hidden-seed", h)


if __name__ == "__main__":
    unittest.main()
