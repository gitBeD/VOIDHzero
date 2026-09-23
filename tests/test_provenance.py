import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voidh0.layer0_cosmology import ReferenceCosmology
from voidh0.layer2_voidfinder.provenance import (
    ProvenanceMismatchError,
    ProvenanceMissingError,
    VoidFinderProvenance,
    compute_file_sha256,
    read_provenance,
    sidecar_path_for,
    validate_provenance,
    write_provenance,
)


class TestComputeFileSha256(unittest.TestCase):
    def test_known_content_hash(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "f.txt"
            path.write_bytes(b"hello world")
            expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
            self.assertEqual(compute_file_sha256(path), expected)

    def test_different_content_different_hash(self):
        with tempfile.TemporaryDirectory() as d:
            p1 = Path(d) / "a.txt"
            p2 = Path(d) / "b.txt"
            p1.write_bytes(b"content A")
            p2.write_bytes(b"content B")
            self.assertNotEqual(compute_file_sha256(p1), compute_file_sha256(p2))

    def test_same_content_same_hash(self):
        with tempfile.TemporaryDirectory() as d:
            p1 = Path(d) / "a.txt"
            p2 = Path(d) / "b.txt"
            p1.write_bytes(b"identical content")
            p2.write_bytes(b"identical content")
            self.assertEqual(compute_file_sha256(p1), compute_file_sha256(p2))


class TestWriteReadProvenance(unittest.TestCase):
    def setUp(self):
        self.cosmology = ReferenceCosmology(name="test_cosmo", H0_km_s_Mpc=67.4, Om0=0.315)
        self.tmpdir = tempfile.TemporaryDirectory()
        self.output_path = Path(self.tmpdir.name) / "output.fits"
        self.source_path = Path(self.tmpdir.name) / "source.dat"
        self.source_path.write_text("ra dec redshift\n150.0 5.0 0.05\n")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_sidecar_path_convention(self):
        expected = Path(str(self.output_path) + ".provenance.json")
        self.assertEqual(sidecar_path_for(self.output_path), expected)

    def test_write_creates_sidecar_file(self):
        sidecar = write_provenance(self.output_path, self.cosmology, self.source_path)
        self.assertTrue(sidecar.exists())

    def test_read_roundtrips_written_values(self):
        write_provenance(
            self.output_path,
            self.cosmology,
            self.source_path,
            voidfinder_version="1.2.3",
            notes="Testlauf",
        )
        prov = read_provenance(self.output_path)
        self.assertIsNotNone(prov)
        self.assertEqual(prov.cosmology_name, "test_cosmo")
        self.assertAlmostEqual(prov.H0_km_s_Mpc, 67.4)
        self.assertAlmostEqual(prov.Om0, 0.315)
        self.assertEqual(prov.voidfinder_version, "1.2.3")
        self.assertEqual(prov.notes, "Testlauf")
        self.assertEqual(prov.source_catalog_sha256, compute_file_sha256(self.source_path))

    def test_read_missing_sidecar_returns_none(self):
        prov = read_provenance(self.output_path)
        self.assertIsNone(prov)

    def test_provenance_captures_source_catalog_checksum(self):
        write_provenance(self.output_path, self.cosmology, self.source_path)
        prov = read_provenance(self.output_path)
        self.assertEqual(prov.source_catalog_sha256, compute_file_sha256(self.source_path))


class TestValidateProvenance(unittest.TestCase):
    def setUp(self):
        self.cosmology = ReferenceCosmology(name="ref", H0_km_s_Mpc=67.4, Om0=0.315)

    def _make_provenance(self, **overrides):
        defaults = dict(
            cosmology_name="ref",
            H0_km_s_Mpc=67.4,
            Om0=0.315,
            source_catalog_path="/some/path.dat",
            source_catalog_sha256="abc123",
            created_utc="2026-01-01T00:00:00+00:00",
        )
        defaults.update(overrides)
        return VoidFinderProvenance(**defaults)

    def test_matching_provenance_passes(self):
        prov = self._make_provenance()
        validate_provenance(prov, self.cosmology, require=True)  # darf nicht werfen

    def test_none_with_require_true_raises_missing(self):
        with self.assertRaises(ProvenanceMissingError):
            validate_provenance(None, self.cosmology, require=True)

    def test_none_with_require_false_is_silent(self):
        validate_provenance(None, self.cosmology, require=False)  # darf nicht werfen

    def test_h0_mismatch_raises(self):
        prov = self._make_provenance(H0_km_s_Mpc=70.0)
        with self.assertRaises(ProvenanceMismatchError):
            validate_provenance(prov, self.cosmology)

    def test_om0_mismatch_raises(self):
        prov = self._make_provenance(Om0=0.3)
        with self.assertRaises(ProvenanceMismatchError):
            validate_provenance(prov, self.cosmology)

    def test_tiny_floating_point_difference_within_rtol_passes(self):
        prov = self._make_provenance(H0_km_s_Mpc=67.4 + 1e-9)
        validate_provenance(prov, self.cosmology, rtol=1e-6)  # darf nicht werfen

    def test_source_catalog_path_mismatch_raises(self):
        prov = self._make_provenance(source_catalog_path="/some/path.dat")
        with self.assertRaises(ProvenanceMismatchError):
            validate_provenance(
                prov,
                self.cosmology,
                expected_source_catalog_path="/different/path.dat",
            )

    def test_source_catalog_path_match_passes(self):
        prov = self._make_provenance(source_catalog_path="/some/path.dat")
        validate_provenance(
            prov, self.cosmology, expected_source_catalog_path="/some/path.dat"
        )  # darf nicht werfen

    def test_no_expected_source_catalog_skips_that_check(self):
        prov = self._make_provenance(source_catalog_path="/whatever.dat")
        validate_provenance(prov, self.cosmology, expected_source_catalog_path=None)


if __name__ == "__main__":
    unittest.main()
