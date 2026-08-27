import sys
import types
from pathlib import Path
import unittest
from unittest.mock import patch

from tts_service import VoxCPM2LocalSynthesizer


class _FakeCuda:
    @staticmethod
    def is_available():
        return True

    @staticmethod
    def empty_cache():
        return None

    @staticmethod
    def ipc_collect():
        return None


class _FakeSoundFile:
    @staticmethod
    def write(path, wav, sample_rate, **kwargs):
        return None


class _FakeModel:
    def __init__(self, *, generate_error=None):
        self.generate_error = generate_error
        self.tts_model = types.SimpleNamespace(sample_rate=24000)
        self.last_kwargs = {}

    def generate(self, **kwargs):
        self.last_kwargs = dict(kwargs)
        if self.generate_error is not None:
            raise self.generate_error
        return [0.0, 0.0]


def _fake_modules(loader):
    torch_module = types.ModuleType("torch")
    torch_module.cuda = _FakeCuda()
    soundfile_module = types.ModuleType("soundfile")
    soundfile_module.write = _FakeSoundFile.write
    voxcpm_module = types.ModuleType("voxcpm")
    voxcpm_module.VoxCPM = loader
    return {
        "torch": torch_module,
        "soundfile": soundfile_module,
        "voxcpm": voxcpm_module,
    }


class VoxCPMCudaFallbackTests(unittest.TestCase):
    def test_missing_project_model_is_rejected_before_voxcpm_import(self):
        with patch(
            "tts_service.voxcpm_model_missing",
            return_value=["model folder"],
        ):
            with self.assertRaisesRegex(RuntimeError, "models.VoxCPM2"):
                VoxCPM2LocalSynthesizer({"voxcpm_device": "auto"})

    def test_auto_tries_cuda_then_cpu_when_model_load_fails(self):
        class Loader:
            calls = []

            @classmethod
            def from_pretrained(cls, *args, **kwargs):
                cls.calls.append(kwargs["device"])
                if kwargs["device"] == "cuda":
                    raise RuntimeError("CUDA out of memory")
                return _FakeModel()

        with (
            patch("tts_service.voxcpm_model_missing", return_value=[]),
            patch.dict(sys.modules, _fake_modules(Loader)),
        ):
            synthesizer = VoxCPM2LocalSynthesizer({"voxcpm_device": "auto"})
            try:
                self.assertEqual(Loader.calls, ["cuda", "cpu"])
                self.assertEqual(synthesizer.device, "cpu")
            finally:
                synthesizer.release()

    def test_cuda_inference_failure_reloads_cpu_and_retries_same_dialogue(self):
        class Loader:
            calls = []

            @classmethod
            def from_pretrained(cls, *args, **kwargs):
                cls.calls.append(kwargs["device"])
                if kwargs["device"] == "cuda":
                    return _FakeModel(generate_error=RuntimeError("CUDA kernel failure"))
                return _FakeModel()

        with (
            patch("tts_service.voxcpm_model_missing", return_value=[]),
            patch.dict(sys.modules, _fake_modules(Loader)),
        ):
            synthesizer = VoxCPM2LocalSynthesizer({"voxcpm_device": "auto"})
            try:
                output = Path("dialogue.wav")
                with (
                    patch("tts_service.Path.is_file", return_value=True),
                    patch(
                        "tts_service.Path.stat",
                        return_value=types.SimpleNamespace(st_size=100),
                    ),
                ):
                    synthesizer.synthesize(
                        {"content": "你好，这是测试对白。", "speaker": "S1"},
                        output,
                    )
                self.assertEqual(Loader.calls, ["cuda", "cpu"])
                self.assertEqual(synthesizer.device, "cpu")
                self.assertNotIn("seed", synthesizer.model.last_kwargs)
            finally:
                synthesizer.release()

    def test_release_is_idempotent_and_drops_model_reference(self):
        class Loader:
            @classmethod
            def from_pretrained(cls, *args, **kwargs):
                return _FakeModel()

        with (
            patch("tts_service.voxcpm_model_missing", return_value=[]),
            patch.dict(sys.modules, _fake_modules(Loader)),
        ):
            synthesizer = VoxCPM2LocalSynthesizer({"voxcpm_device": "cuda"})
            with patch.object(
                synthesizer, "_clear_model_and_cuda", wraps=synthesizer._clear_model_and_cuda
            ) as clear:
                synthesizer.release()
                synthesizer.release()
            self.assertIsNone(synthesizer.model)
            self.assertTrue(synthesizer._released)
            clear.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
