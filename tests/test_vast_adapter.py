import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

try:
    import astropy  # noqa: F401

    HAS_ASTROPY = True
except ImportError:
    HAS_ASTROPY = False

from voidh0.layer0_cosmology import ReferenceCosmology, load_reference_cosmology
from voidh0.layer1_tracers import DemoTracerAdapter


def _make_vast_output_fits(path, cosmology, include_mask=True):
    """Baut eine VAST-kompatible VoidFinder_Output.fits mit synthetischen
    MAXIMALS-/HOLES-/MASK-HDUs, exakt im offiziellen Spaltenschema
    (siehe https://vast.readthedocs.io/en/latest/VoidFinder_examples.html#output).
    """
    from astropy.io import fits

    # Ein einzelner synthetischer Void bei ra=155, dec=5, z=0.05.
    ra0, dec0, z0 = 155.0, 5.0, 0.05
    r0_h1mpc = cosmology.comoving_distance_h1Mpc(z0)
    ra_rad, dec_rad = np.deg2rad(ra0), np.deg2rad(dec0)
    x0 = r0_h1mpc * np.cos(dec_rad) * np.cos(ra_rad)
    y0 = r0_h1mpc * np.cos(dec_rad) * np.sin(ra_rad)
    z0_cart = r0_h1mpc * np.sin(dec_rad)

    radius = 15.0  # h^-1 Mpc

    maximals = fits.BinTableHDU.from_columns(
        [
            fits.Column(name="x", format="D", array=[x0]),
            fits.Column(name="y", format="D", array=[y0]),
            fits.Column(name="z", format="D", array=[z0_cart]),
            fits.Column(name="radius", format="D", array=[radius]),
            fits.Column(name="void", format="J", array=[1]),
            fits.Column(name="r", format="D", array=[r0_h1mpc]),
            fits.Column(name="ra", format="D", array=[ra0]),
            fits.Column(name="dec", format="D", array=[dec0]),
        ],
        name="MAXIMALS",
    )

    # Zwei Holes-Spheres fuer denselben Void (die Maximal-Sphere selbst plus
    # eine etwas verschobene kleinere Sphere).
    holes = fits.BinTableHDU.from_columns(
        [
            fits.Column(name="x", format="D", array=[x0, x0 + 5.0]),
            fits.Column(name="y", format="D", array=[y0, y0]),
            fits.Column(name="z", format="D", array=[z0_cart, z0_cart]),
            fits.Column(name="radius", format="D", array=[radius, 8.0]),
            fits.Column(name="void", format="J", array=[1, 1]),
        ],
        name="HOLES",
    )

    hdus = [fits.PrimaryHDU(), maximals, holes]

    if include_mask:
        mask_resolution = 1
        mask_arr = np.ones((360 * mask_resolution, 180 * mask_resolution), dtype=np.uint8)
        # Ein kleiner "Loch"-Bereich in der Maske, weit weg vom Void, zum
        # Testen der edge-Klassifikation.
        mask_arr[0:5, 0:5] = 0
        mask_hdu = fits.ImageHDU(data=mask_arr, name="MASK")
        mask_hdu.header["MASKRES"] = mask_resolution
        hdus.append(mask_hdu)

    fits.HDUList(hdus).writeto(path, overwrite=True)


@unittest.skipUnless(HAS_ASTROPY, "astropy nicht installiert -- VASTVoidFinderAdapter uebersprungen")
class TestVASTVoidFinderAdapter(unittest.TestCase):
    def setUp(self):
        self.cosmology = load_reference_cosmology()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.fits_path = Path(self.tmpdir.name) / "test_VoidFinder_Output.fits"
        _make_vast_output_fits(self.fits_path, self.cosmology)
        self.tracers = DemoTracerAdapter(n_objects=10, n_randoms=10, seed=0).load()

        # Provenienz-Sidecar erzeugen, damit die Standard-Pruefung
        # (require_provenance=True) fuer die bestehenden Tests nicht
        # fehlschlaegt -- separate Tests unten pruefen die Validierung selbst.
        from voidh0.layer2_voidfinder.provenance import write_provenance

        self.source_catalog_path = Path(self.tmpdir.name) / "dummy_source_catalog.dat"
        self.source_catalog_path.write_text("ra dec redshift\n150.0 5.0 0.05\n")
        write_provenance(self.fits_path, self.cosmology, self.source_catalog_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_find_voids_reads_maximals(self):
        from voidh0.layer2_voidfinder import VASTVoidFinderAdapter

        adapter = VASTVoidFinderAdapter(self.fits_path, cosmology=self.cosmology)
        voids = adapter.find_voids(self.tracers)

        self.assertEqual(len(voids), 1)
        self.assertAlmostEqual(voids.center_ra_deg[0], 155.0, places=6)
        self.assertAlmostEqual(voids.center_dec_deg[0], 5.0, places=6)
        self.assertAlmostEqual(voids.center_z[0], 0.05, places=3)
        self.assertAlmostEqual(voids.effective_radius_h1Mpc[0], 15.0, places=6)
        self.assertEqual(voids.algorithm, "vast_voidfinder")

    def test_missing_file_raises(self):
        from voidh0.layer2_voidfinder import VASTVoidFinderAdapter

        adapter = VASTVoidFinderAdapter(
            Path(self.tmpdir.name) / "does_not_exist.fits", cosmology=self.cosmology
        )
        with self.assertRaises(FileNotFoundError):
            adapter.find_voids(self.tracers)

    def test_missing_maximals_hdu_raises_keyerror(self):
        from astropy.io import fits

        from voidh0.layer2_voidfinder import VASTVoidFinderAdapter

        bad_path = Path(self.tmpdir.name) / "bad.fits"
        fits.HDUList([fits.PrimaryHDU()]).writeto(bad_path)

        adapter = VASTVoidFinderAdapter(bad_path, cosmology=self.cosmology, require_provenance=False)
        with self.assertRaises(KeyError):
            adapter.find_voids(self.tracers)

    def test_classify_requires_find_voids_first(self):
        from voidh0.layer2_voidfinder import VASTVoidFinderAdapter

        adapter = VASTVoidFinderAdapter(self.fits_path, cosmology=self.cosmology)
        with self.assertRaises(RuntimeError):
            adapter.classify(np.array([155.0]), np.array([5.0]), np.array([0.05]), None)

    def test_classify_point_at_void_center_is_void(self):
        from voidh0.layer2_voidfinder import VASTVoidFinderAdapter

        adapter = VASTVoidFinderAdapter(self.fits_path, cosmology=self.cosmology)
        voids = adapter.find_voids(self.tracers)

        labels = adapter.classify(
            np.array([155.0]), np.array([5.0]), np.array([0.05]), voids
        )
        self.assertEqual(labels[0], "void")

    def test_classify_far_away_point_is_wall(self):
        from voidh0.layer2_voidfinder import VASTVoidFinderAdapter

        adapter = VASTVoidFinderAdapter(self.fits_path, cosmology=self.cosmology)
        voids = adapter.find_voids(self.tracers)

        labels = adapter.classify(
            np.array([10.0]), np.array([-30.0]), np.array([0.09]), voids
        )
        self.assertEqual(labels[0], "wall")

    def test_classify_multiple_points_mixed(self):
        from voidh0.layer2_voidfinder import VASTVoidFinderAdapter

        adapter = VASTVoidFinderAdapter(self.fits_path, cosmology=self.cosmology)
        voids = adapter.find_voids(self.tracers)

        ra = np.array([155.0, 10.0])
        dec = np.array([5.0, -30.0])
        z = np.array([0.05, 0.09])
        labels = adapter.classify(ra, dec, z, voids)
        self.assertEqual(list(labels), ["void", "wall"])

    def test_ra_dec_z_to_xyz_roundtrips_radius(self):
        from voidh0.layer2_voidfinder import ra_dec_z_to_xyz

        x, y, z = ra_dec_z_to_xyz(
            np.array([155.0]), np.array([5.0]), np.array([0.05]), self.cosmology
        )
        r = np.sqrt(x**2 + y**2 + z**2)
        expected_r = self.cosmology.comoving_distance_h1Mpc(0.05)
        self.assertAlmostEqual(float(r[0]), float(expected_r), places=4)

    def test_no_mask_hdu_skips_edge_classification(self):
        from voidh0.layer2_voidfinder import VASTVoidFinderAdapter

        no_mask_path = Path(self.tmpdir.name) / "no_mask.fits"
        _make_vast_output_fits(no_mask_path, self.cosmology, include_mask=False)

        from voidh0.layer2_voidfinder.provenance import write_provenance

        write_provenance(no_mask_path, self.cosmology, self.source_catalog_path)

        adapter = VASTVoidFinderAdapter(no_mask_path, cosmology=self.cosmology)
        voids = adapter.find_voids(self.tracers)
        labels = adapter.classify(np.array([10.0]), np.array([-30.0]), np.array([0.09]), voids)
        # ohne Maske gibt es keine "edge"-Klassifikation -- nur void/wall
        self.assertIn(labels[0], ("void", "wall"))

    def test_missing_provenance_raises_by_default(self):
        from voidh0.layer2_voidfinder import VASTVoidFinderAdapter
        from voidh0.layer2_voidfinder.provenance import ProvenanceMissingError

        no_provenance_path = Path(self.tmpdir.name) / "no_provenance.fits"
        _make_vast_output_fits(no_provenance_path, self.cosmology)
        # bewusst KEIN write_provenance() hier

        adapter = VASTVoidFinderAdapter(no_provenance_path, cosmology=self.cosmology)
        with self.assertRaises(ProvenanceMissingError):
            adapter.find_voids(self.tracers)

    def test_require_provenance_false_skips_check(self):
        from voidh0.layer2_voidfinder import VASTVoidFinderAdapter

        no_provenance_path = Path(self.tmpdir.name) / "no_provenance2.fits"
        _make_vast_output_fits(no_provenance_path, self.cosmology)

        adapter = VASTVoidFinderAdapter(
            no_provenance_path, cosmology=self.cosmology, require_provenance=False
        )
        voids = adapter.find_voids(self.tracers)  # darf NICHT wegen Provenienz scheitern
        self.assertEqual(len(voids), 1)

    def test_cosmology_mismatch_raises(self):
        from voidh0.layer2_voidfinder import VASTVoidFinderAdapter
        from voidh0.layer2_voidfinder.provenance import ProvenanceMismatchError

        different_cosmology = ReferenceCosmology(
            name="other_cosmology", H0_km_s_Mpc=70.0, Om0=0.3
        )
        adapter = VASTVoidFinderAdapter(self.fits_path, cosmology=different_cosmology)
        with self.assertRaises(ProvenanceMismatchError):
            adapter.find_voids(self.tracers)


if __name__ == "__main__":
    unittest.main()
