import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voidh0.layer3_environment import assign_environment


class TestAssignEnvironment(unittest.TestCase):
    def test_full_agreement_is_robust(self):
        ids = np.array(["a", "b", "c"])
        labels = {
            "algo1": np.array(["void", "wall", "void"], dtype=object),
            "algo2": np.array(["void", "wall", "void"], dtype=object),
        }
        result = assign_environment(ids, labels)
        self.assertTrue((result.robustness_flag == "robust").all())
        self.assertEqual(list(result.environment_class), ["void", "wall", "void"])

    def test_majority_is_marginal(self):
        ids = np.array(["a"])
        labels = {
            "algo1": np.array(["void"], dtype=object),
            "algo2": np.array(["void"], dtype=object),
            "algo3": np.array(["wall"], dtype=object),
        }
        result = assign_environment(ids, labels)
        self.assertEqual(result.robustness_flag[0], "marginal")
        self.assertEqual(result.environment_class[0], "void")

    def test_tie_is_edge_excluded(self):
        ids = np.array(["a"])
        labels = {
            "algo1": np.array(["void"], dtype=object),
            "algo2": np.array(["wall"], dtype=object),
        }
        result = assign_environment(ids, labels)
        self.assertEqual(result.robustness_flag[0], "edge_excluded")
        self.assertEqual(result.environment_class[0], "unclassified")

    def test_edge_label_forces_edge_excluded(self):
        ids = np.array(["a", "b"])
        labels = {
            "algo1": np.array(["void", "edge"], dtype=object),
            "algo2": np.array(["void", "wall"], dtype=object),
        }
        result = assign_environment(ids, labels)
        self.assertEqual(result.robustness_flag[1], "edge_excluded")
        self.assertEqual(result.environment_class[1], "unclassified")

    def test_rejects_empty_input(self):
        with self.assertRaises(ValueError):
            assign_environment(np.array(["a"]), {})

    def test_rejects_length_mismatch(self):
        with self.assertRaises(ValueError):
            assign_environment(
                np.array(["a", "b"]), {"algo1": np.array(["void"], dtype=object)}
            )


if __name__ == "__main__":
    unittest.main()
