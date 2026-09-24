import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voidh0.layer0_cosmology import load_reference_cosmology
from voidh0.layer3_environment.density import (
    compute_local_density,
    voronoi_cell_volumes,
)


class TestVoronoiCellVolumes(unittest.TestCase):
    def test_rejects_too_few_points(self):
        with self.assertRaises(ValueError):
            voronoi_cell_volumes(np.zeros((3, 3)))

    def test_regular_grid_has_similar_interior_volumes(self):
        # 5x5x5 regelmaessiges Gitter: alle inneren Zellen sollten (fast)
        # dasselbe Volumen haben (Wuerfelvolumen der Gitterzelle).
        rng = np.random.default_rng(0)
        coords = np.arange(5) * 10.0  # Spacing 10
        xx, yy, zz = np.meshgrid(coords, coords, coords, indexing="ij")
        points = np.column_stack([xx.ravel(), yy.ravel(), zz.ravel()])
        # winziger Jitter, um perfekt entartete Faelle zu vermeiden
        points = points + rng.normal(0, 1e-6, size=points.shape)

        volumes = voronoi_cell_volumes(points)
        finite = volumes[~np.isnan(volumes)]
        self.assertGreater(len(finite), 0)
        # innere Zellen eines regelmaessigen Gitters mit Spacing 10 haben
        # Volumen 10^3 = 1000
        self.assertTrue(np.any(np.isclose(finite, 1000.0, rtol=0.05)))

    def test_edge_points_are_nan(self):
        rng = np.random.default_rng(1)
        points = rng.uniform(0, 100, size=(200, 3))
        volumes = voronoi_cell_volumes(points)
        # in jeder endlichen Punktwolke gibt es Randpunkte auf der konvexen
        # Huelle -> mindestens einige NaN-Eintraege
        self.assertGreater(np.sum(np.isnan(volumes)), 0)

    def test_all_volumes_positive_where_finite(self):
        rng = np.random.default_rng(2)
        points = rng.uniform(0, 50, size=(150, 3))
        volumes = voronoi_cell_volumes(points)
        finite = volumes[~np.isnan(volumes)]
        self.assertTrue((finite > 0).all())

    def test_sparse_region_has_larger_cells_than_dense_region(self):
        rng = np.random.default_rng(3)
        dense = rng.uniform(0, 20, size=(300, 3))
        sparse = rng.uniform(30, 100, size=(30, 3))
        points = np.vstack([dense, sparse])

        volumes = voronoi_cell_volumes(points)
        dense_vol = volumes[: len(dense)]
        sparse_vol = volumes[len(dense) :]

        dense_median = np.nanmedian(dense_vol)
        sparse_median = np.nanmedian(sparse_vol)
        self.assertGreater(sparse_median, dense_median)


class TestComputeLocalDensity(unittest.TestCase):
    def setUp(self):
        self.cosmology = load_reference_cosmology()

    def test_returns_result_matching_input_length(self):
        rng = np.random.default_rng(0)
        n = 200
        ra = rng.uniform(150, 160, n)
        dec = rng.uniform(0, 10, n)
        z = rng.uniform(0.02, 0.08, n)
        ids = np.array([f"obj_{i}" for i in range(n)])

        result = compute_local_density(ids, ra, dec, z, self.cosmology)
        self.assertEqual(len(result.cell_volume_h3Mpc3), n)
        self.assertEqual(len(result.log_density_contrast), n)
        self.assertEqual(len(result.is_edge_cell), n)

    def test_edge_cells_have_nan_density_contrast(self):
        rng = np.random.default_rng(1)
        n = 150
        ra = rng.uniform(150, 160, n)
        dec = rng.uniform(0, 10, n)
        z = rng.uniform(0.02, 0.08, n)
        ids = np.arange(n)

        result = compute_local_density(ids, ra, dec, z, self.cosmology)
        self.assertGreater(result.n_edge_cells(), 0)
        self.assertTrue(np.all(np.isnan(result.log_density_contrast[result.is_edge_cell])))
        self.assertTrue(np.all(~np.isnan(result.log_density_contrast[~result.is_edge_cell])))

    def test_dense_subregion_gets_positive_density_contrast(self):
        # Baue eine kuenstliche Unterdichte: die meisten Punkte dicht
        # gepackt, ein paar wenige weit entfernt und isoliert.
        rng = np.random.default_rng(2)
        ra_dense = rng.uniform(150, 152, 300)
        dec_dense = rng.uniform(0, 2, 300)
        z_dense = rng.uniform(0.05, 0.052, 300)

        ra_sparse = rng.uniform(160, 165, 20)
        dec_sparse = rng.uniform(5, 10, 20)
        z_sparse = rng.uniform(0.06, 0.065, 20)

        ra = np.concatenate([ra_dense, ra_sparse])
        dec = np.concatenate([dec_dense, dec_sparse])
        z = np.concatenate([z_dense, z_sparse])
        ids = np.arange(len(ra))

        result = compute_local_density(ids, ra, dec, z, self.cosmology)

        dense_contrast = np.nanmedian(result.log_density_contrast[:300])
        sparse_contrast = np.nanmedian(result.log_density_contrast[300:])
        # dichter gepackte Region -> hoehere log-Dichte als die isolierte
        self.assertGreater(dense_contrast, sparse_contrast)

    def test_median_log_contrast_is_near_zero_by_construction(self):
        # log10(rho/rho_median) ist per Definition (Median als Referenz) nahe
        # 0 im Median der Verteilung -- robust gegenueber der Rechtsschiefe
        # der Voronoi-Zellvolumina (siehe Docstring in density.py).
        rng = np.random.default_rng(3)
        n = 400
        ra = rng.uniform(150, 160, n)
        dec = rng.uniform(0, 10, n)
        z = rng.uniform(0.02, 0.08, n)
        ids = np.arange(n)

        result = compute_local_density(ids, ra, dec, z, self.cosmology)
        finite_contrast = result.log_density_contrast[~result.is_edge_cell]
        self.assertLess(abs(np.median(finite_contrast)), 0.1)


if __name__ == "__main__":
    unittest.main()
