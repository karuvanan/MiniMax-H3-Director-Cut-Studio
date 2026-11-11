from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ace_step_server_extension import release_ace_step_models


class _Store:
    def __init__(self, *, queued: int = 0, running: int = 0) -> None:
        self.queued = queued
        self.running = running

    def get_stats(self) -> dict[str, int]:
        return {"queued": self.queued, "running": self.running}


class _Llm:
    def __init__(self) -> None:
        self.llm = object()
        self.unload_calls = 0

    def unload(self) -> None:
        self.unload_calls += 1
        self.llm = None


def _handler() -> SimpleNamespace:
    return SimpleNamespace(
        model=object(),
        vae=object(),
        text_encoder=object(),
        text_tokenizer=object(),
        silence_latent=object(),
        reward_model=None,
        _base_decoder=object(),
        mlx_decoder=None,
        mlx_vae=None,
        compiled=True,
        mlx_dit_compiled=True,
        lora_loaded=True,
        use_lora=True,
        _lora_active_adapter="voice",
        _active_loras={"voice": 1.0},
        last_init_params={"config_path": "acestep-v15-turbo"},
    )


class AceStepServerExtensionTests(unittest.TestCase):
    def test_release_drops_models_but_preserves_lazy_reload_state(self):
        handler = _handler()
        llm = _Llm()
        state = SimpleNamespace(
            job_store=_Store(),
            handler=handler,
            handler2=None,
            handler3=None,
            llm_handler=llm,
            _initialized=True,
            _initialized2=False,
            _initialized3=False,
            _init_error="old",
            _llm_initialized=True,
            _llm_init_error="old",
            _llm_lazy_load_disabled=True,
        )

        with patch("ace_step_server_extension._clear_device_caches", return_value=True):
            result = release_ace_step_models(state)

        self.assertEqual(result["released_slots"], [1])
        self.assertTrue(result["llm_unloaded"])
        self.assertTrue(result["lazy_reload"])
        self.assertIsNone(handler.model)
        self.assertIsNone(handler.vae)
        self.assertIsNone(handler.text_encoder)
        self.assertFalse(handler.compiled)
        self.assertEqual(handler._active_loras, {})
        self.assertEqual(handler.last_init_params["config_path"], "acestep-v15-turbo")
        self.assertFalse(state._initialized)
        self.assertFalse(state._llm_initialized)
        self.assertEqual(llm.unload_calls, 1)

    def test_release_rejects_active_generation(self):
        state = SimpleNamespace(job_store=_Store(running=1))
        with self.assertRaisesRegex(RuntimeError, "ACE-Step is busy"):
            release_ace_step_models(state)


if __name__ == "__main__":
    unittest.main()
