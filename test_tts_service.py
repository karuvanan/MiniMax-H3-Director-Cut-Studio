import sys
import types
from pathlib import Path
import unittest
from unittest.mock import patch

from tts_service import Qwen3TTSLocalSynthesizer, VoxCPM2LocalSynthesizer


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

    @staticmethod
    def manual_seed_all(_seed):
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


class _FakeQwenModel:
    def __init__(self, *, generate_error=None):
        self.generate_error = generate_error
        self.last_kwargs = {}

    def generate_custom_voice(self, **kwargs):
        self.last_kwargs = dict(kwargs)
        if self.generate_error is not None:
            raise self.generate_error
        return [[0.0, 0.0]], 24000


class Qwen3TTSCudaFallbackTests(unittest.TestCase):
    def _torch_module(self):
        torch_module = types.ModuleType("torch")
        torch_module.cuda = _FakeCuda()
        torch_module.bfloat16 = "bfloat16"
        torch_module.float32 = "float32"
        torch_module.manual_seed = lambda _seed: None
        return torch_module

    def test_missing_runtime_or_model_is_rejected_before_import(self):
        with (
            patch("tts_service.qwen3_tts_runtime_missing", return_value=[]),
            patch("tts_service.qwen3_tts_model_missing", return_value=["model folder"]),
        ):
            with self.assertRaisesRegex(RuntimeError, "Qwen3-TTS Local is not ready"):
                Qwen3TTSLocalSynthesizer({"qwen3_tts_device": "auto"})

    def test_auto_tries_cuda_then_cpu_when_model_load_fails(self):
        class Loader:
            calls = []

            @classmethod
            def from_pretrained(cls, *args, **kwargs):
                cls.calls.append(kwargs["device_map"])
                if str(kwargs["device_map"]).startswith("cuda"):
                    raise RuntimeError("CUDA out of memory")
                return _FakeQwenModel()

        soundfile_module = types.ModuleType("soundfile")
        soundfile_module.write = _FakeSoundFile.write
        with (
            patch("tts_service.qwen3_tts_runtime_missing", return_value=[]),
            patch("tts_service.qwen3_tts_model_missing", return_value=[]),
            patch("tts_service._load_qwen3_tts_api", return_value=Loader),
            patch.dict(
                sys.modules,
                {"torch": self._torch_module(), "soundfile": soundfile_module},
            ),
        ):
            synthesizer = Qwen3TTSLocalSynthesizer({"qwen3_tts_device": "auto"})
            try:
                self.assertEqual(Loader.calls, ["cuda:0", "cpu"])
                self.assertEqual(synthesizer.device, "cpu")
            finally:
                synthesizer.release()

    def test_cuda_inference_failure_reloads_cpu_and_retries_same_words(self):
        class Loader:
            calls = []

            @classmethod
            def from_pretrained(cls, *args, **kwargs):
                cls.calls.append(kwargs["device_map"])
                if str(kwargs["device_map"]).startswith("cuda"):
                    return _FakeQwenModel(
                        generate_error=RuntimeError("CUDA kernel failure")
                    )
                return _FakeQwenModel()

        soundfile_module = types.ModuleType("soundfile")
        soundfile_module.write = _FakeSoundFile.write
        with (
            patch("tts_service.qwen3_tts_runtime_missing", return_value=[]),
            patch("tts_service.qwen3_tts_model_missing", return_value=[]),
            patch("tts_service._load_qwen3_tts_api", return_value=Loader),
            patch.dict(
                sys.modules,
                {"torch": self._torch_module(), "soundfile": soundfile_module},
            ),
        ):
            synthesizer = Qwen3TTSLocalSynthesizer({"qwen3_tts_device": "auto"})
            try:
                with (
                    patch("tts_service.Path.is_file", return_value=True),
                    patch(
                        "tts_service.Path.stat",
                        return_value=types.SimpleNamespace(st_size=100),
                    ),
                ):
                    synthesizer.synthesize(
                        {
                            "content": "你好，这是测试对白。",
                            "speaker": "S2",
                            "language": "Mandarin Chinese",
                        },
                        Path("dialogue.wav"),
                    )
                self.assertEqual(Loader.calls, ["cuda:0", "cpu"])
                self.assertEqual(synthesizer.model.last_kwargs["text"], "你好，这是测试对白。")
                self.assertEqual(synthesizer.model.last_kwargs["speaker"], "Uncle_Fu")
                self.assertEqual(synthesizer.model.last_kwargs["language"], "Chinese")
            finally:
                synthesizer.release()


if __name__ == "__main__":
    unittest.main()
