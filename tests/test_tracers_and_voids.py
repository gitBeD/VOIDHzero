import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voidh0.layer1_tracers import DemoTracerAdapter
from voidh0.layer2_voidfinder import DemoVoidFinderAdapter


class TestDemoTracerAdapter(unittest.TestCase):
    def test_load_shapes(self):
        adapter = DemoTracerAdapter(n_objects=100, n_randoms=500, seed=1)
        cat = adapter.load()
        self.assertEqual(len(cat), 600)
        self.assertEqual(cat.n_objects, 100)
        self.assertEqual(cat.n_randoms, 500)

    def test_redshift_within_limits(self):
        adapter = DemoTracerAdapter(n_objects=50, n_randoms=50, z_min=0.02, z_max=0.08, seed=2)
        cat = adapter.load()
        self.assertTrue((cat.z >= 0.02).all())
        self.assertTrue((cat.z <= 0.08).all())

    def test_reproducible_with_seed(self):
        cat1 = DemoTracerAdapter(n_objects=20, n_randoms=20, seed=99).load()
        cat2 = DemoTracerAdapter(n_objects=20, n_randoms=20, seed=99).load()
        self.assertTrue((cat1.z == cat2.z).all())


class TestDemoVoidFinderAdapter(unittest.TestCase):
    def test_find_and_classify(self):
        tracers = DemoTracerAdapter(n_objects=300, n_randoms=1000, seed=3).load()
        finder = DemoVoidFinderAdapter(n_voids=5, seed=11)
        voids = finder.find_voids(tracers)
        self.assertEqual(len(voids), 5)

        labels = finder.classify(tracers.ra_deg, tracers.dec_deg, tracers.z, voids)
        self.assertEqual(len(labels), len(tracers))
        allowed = {"void", "wall"}
        self.assertTrue(set(labels).issubset(allowed))


if __name__ == "__main__":
    unittest.main()
