import json
from pathlib import Path
import shutil
import unittest
import uuid

import numpy as np

from vocal_separator_engine import (
    AUTO_VOCAL_REFERENCE_MARKER,
    auto_vocal_reference_recognition,
    cached_vocal_stem,
    is_auto_vocal_reference,
    validate_separator_installation,
    vocal_stem_cache_key,
    vocal_stem_paths,
)
from vocal_separator_service import prepare_soundfile_samples


class VocalSeparatorEngineTests(unittest.TestCase):
    def _workspace(self) -> Path:
        folder = (
            Path(__file__).resolve().parent
            / ".director_cache"
            / f"vocal-separator-test-{uuid.uuid4().hex}"
        )
        folder.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, folder, True)
        return folder

    def test_installation_validator_requires_model_and_both_runtime_packages(self):
        root = self._workspace()
        self.assertEqual(len(validate_separator_installation(root)), 6)
        install = root / "models" / "audio-separator"
        (install / "runtime" / "audio_separator").mkdir(parents=True)
        (install / "runtime" / "onnxruntime").mkdir(parents=True)
        (install / "Kim_Vocal_2.onnx").write_bytes(b"model")
        for filename in ("download_checks.json", "mdx_model_data.json", "vr_model_data.json"):
            (install / filename).write_text("{}", encoding="utf-8")
        self.assertEqual(validate_separator_installation(root), [])

    def test_cache_key_depends_on_source_and_model_bytes_not_filename(self):
        root = self._workspace()
        source = root / "song.wav"
        renamed = root / "copy.wav"
        model = root / "model.onnx"
        source.write_bytes(b"same-song")
        renamed.write_bytes(b"same-song")
        model.write_bytes(b"same-model")
        self.assertEqual(
            vocal_stem_cache_key(source, model),
            vocal_stem_cache_key(renamed, model),
        )
        renamed.write_bytes(b"changed-song")
        self.assertNotEqual(
            vocal_stem_cache_key(source, model),
            vocal_stem_cache_key(renamed, model),
        )

    def test_cache_requires_matching_manifest_and_vocal_file(self):
        folder = self._workspace()
        paths = vocal_stem_paths(folder, "abc123")
        paths["folder"].mkdir(parents=True)
        paths["vocal"].write_bytes(b"wave")
        self.assertIsNone(cached_vocal_stem(folder, "abc123"))
        paths["manifest"].write_text(
            json.dumps({"cache_key": "abc123"}), encoding="utf-8"
        )
        self.assertEqual(cached_vocal_stem(folder, "abc123"), paths["vocal"])

    def test_auto_reference_marker_is_unambiguous(self):
        text = auto_vocal_reference_recognition("song.mp3", "abc")
        self.assertIn(AUTO_VOCAL_REFERENCE_MARKER, text)
        self.assertTrue(is_auto_vocal_reference(text))
        self.assertFalse(is_auto_vocal_reference("user supplied vocal"))

    def test_safe_stem_writer_preserves_float_stereo_samples(self):
        original = np.array(
            [[0.25, -0.25], [0.5, -0.5], [0.75, -0.75]],
            dtype=np.float32,
            order="C",
        )
        prepared = prepare_soundfile_samples(original)
        self.assertEqual(prepared.shape, (3, 2))
        np.testing.assert_allclose(prepared, original)
        self.assertGreater(float(np.max(np.abs(prepared))), 0.5)

    def test_safe_stem_writer_transposes_channels_first_audio(self):
        channels_first = np.array(
            [[0.1, 0.2, 0.3], [-0.1, -0.2, -0.3]], dtype=np.float32
        )
        prepared = prepare_soundfile_samples(channels_first)
        self.assertEqual(prepared.shape, (3, 2))
        np.testing.assert_allclose(prepared[:, 0], channels_first[0])


if __name__ == "__main__":
    unittest.main()
