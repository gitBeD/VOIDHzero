import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voidh0.layer5_interpretation import propagate_to_H0_bias
from voidh0.layer5_interpretation.propagation import propagate_upper_limit


class TestPropagateToH0Bias(unittest.TestCase):
    def test_zero_step_gives_zero_bias(self):
        result = propagate_to_H0_bias(0.0, 0.05, H0_ref_km_s_Mpc=73.0)
        self.assertAlmostEqual(result.relative_H0_bias, 0.0)
        self.assertAlmostEqual(result.absolute_H0_bias_km_s_Mpc, 0.0)

    def test_zero_fraction_difference_gives_zero_bias(self):
        result = propagate_to_H0_bias(0.1, 0.0, H0_ref_km_s_Mpc=73.0)
        self.assertAlmostEqual(result.relative_H0_bias, 0.0)

    def test_known_riess_mass_step_order_of_magnitude(self):
        # Riess et al. 2016: reiner Massen-Step ~0,7% auf H0 (Exposé Abschnitt 3).
        # Hier nur als Plausibilitaetscheck der Groessenordnung der Formel,
        # NICHT als Reproduktion des publizierten Analysewegs.
        result = propagate_to_H0_bias(
            delta_mu_env_mag=0.07, delta_f_void=0.23, H0_ref_km_s_Mpc=73.0
        )
        self.assertLess(abs(result.relative_H0_bias), 0.05)
        self.assertGreater(abs(result.relative_H0_bias), 0.0)

    def test_sign_flips_with_step_sign(self):
        pos = propagate_to_H0_bias(0.05, 0.1, H0_ref_km_s_Mpc=70.0)
        neg = propagate_to_H0_bias(-0.05, 0.1, H0_ref_km_s_Mpc=70.0)
        self.assertAlmostEqual(pos.relative_H0_bias, -neg.relative_H0_bias)

    def test_absolute_bias_scales_with_H0_ref(self):
        low = propagate_to_H0_bias(0.05, 0.1, H0_ref_km_s_Mpc=67.4)
        high = propagate_to_H0_bias(0.05, 0.1, H0_ref_km_s_Mpc=73.0)
        self.assertLess(abs(low.absolute_H0_bias_km_s_Mpc), abs(high.absolute_H0_bias_km_s_Mpc))


class TestPropagateUpperLimit(unittest.TestCase):
    def test_picks_largest_absolute_candidate(self):
        candidates = [0.098, -0.114, 0.045, -0.097]  # aus Exposé Tabelle Abschnitt 3
        result = propagate_upper_limit(candidates, delta_f_void=0.1, H0_ref_km_s_Mpc=73.0)
        self.assertAlmostEqual(result.delta_mu_env_mag, -0.114)

    def test_rejects_empty_list(self):
        with self.assertRaises(ValueError):
            propagate_upper_limit([], delta_f_void=0.1, H0_ref_km_s_Mpc=73.0)


if __name__ == "__main__":
    unittest.main()
