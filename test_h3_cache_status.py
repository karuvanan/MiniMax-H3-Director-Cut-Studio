from pathlib import Path
import tempfile
import unittest

from comfyui_director_h3_cache_status.cache_status import (
    CACHE_BUDGET_BYTES,
    configured_cache_directory,
    measure_cache_directory,
)
from comfyui_director_h3_cache_status.system_status import (
    collect_system_resources,
    parse_nvidia_smi_csv,
)


class H3RelayCacheStatusTests(unittest.TestCase):
    @staticmethod
    def _temporary_directory():
        parent = Path.cwd() / ".director_cache" / "cache_status_tests"
        parent.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=parent)

    def test_missing_cache_is_measured_as_zero(self):
        with self._temporary_directory() as temporary:
            result = measure_cache_directory(Path(temporary) / "missing")
        self.assertTrue(result["ok"])
        self.assertEqual(result["used_bytes"], 0)
        self.assertEqual(result["budget_bytes"], CACHE_BUDGET_BYTES)
        self.assertEqual(result["file_count"], 0)

    def test_cache_measurement_reports_total_and_direct_child_breakdown(self):
        with self._temporary_directory() as temporary:
            root = Path(temporary) / "__h3_removal_cache"
            windows = root / "windows" / "scope"
            previews = root / "previews" / "run"
            windows.mkdir(parents=True)
            previews.mkdir(parents=True)
            (windows / "one.pt").write_bytes(b"x" * 1024)
            (windows / "one.json").write_bytes(b"y" * 128)
            (previews / "one.mp4").write_bytes(b"z" * 256)

            result = measure_cache_directory(root)

        self.assertEqual(result["used_bytes"], 1408)
        self.assertEqual(result["file_count"], 3)
        self.assertEqual(result["error_count"], 0)
        self.assertEqual(result["breakdown_bytes"]["windows"], 1152)
        self.assertEqual(result["breakdown_bytes"]["previews"], 256)

    def test_configured_cache_directory_uses_server_settings(self):
        with self._temporary_directory() as temporary:
            root = Path(temporary)
            default = root / "default"
            selected = root / "selected"
            settings = root / "status-settings.json"
            settings.write_text(
                '{"cache_path": "' + str(selected).replace("\\", "\\\\") + '"}',
                encoding="utf-8",
            )
            result = configured_cache_directory(default, settings)
        self.assertEqual(result, selected.resolve(strict=False))

    def test_configured_cache_directory_falls_back_for_invalid_json(self):
        with self._temporary_directory() as temporary:
            root = Path(temporary)
            default = root / "default"
            settings = root / "status-settings.json"
            settings.write_text("{not valid", encoding="utf-8")
            result = configured_cache_directory(default, settings)
        self.assertEqual(result, default)

    def test_nvidia_smi_parser_selects_the_busiest_gpu(self):
        status = parse_nvidia_smi_csv(
            "0, Display GPU, 1024, 8192, 8\n"
            "1, Render GPU, 12288, 16384, 96\n"
        )
        self.assertTrue(status["gpu_available"])
        self.assertEqual(status["gpu_index"], 1)
        self.assertEqual(status["gpu_name"], "Render GPU")
        self.assertEqual(status["gpu_percent"], 96.0)
        self.assertEqual(status["vram_percent"], 75.0)

    def test_system_resources_reports_cpu_and_dram_percentages(self):
        class Memory:
            percent = 62.5
            used = 40 * 1024**3
            total = 64 * 1024**3

        class Psutil:
            @staticmethod
            def cpu_percent(interval=None):
                self.assertEqual(interval, 0.05)
                return 37.25

            @staticmethod
            def virtual_memory():
                return Memory()

        status = collect_system_resources(
            psutil_module=Psutil,
            gpu_query=lambda: parse_nvidia_smi_csv(
                "0, Test GPU, 4096, 8192, 81\n"
            ),
        )
        self.assertEqual(status["cpu_percent"], 37.2)
        self.assertEqual(status["dram_percent"], 62.5)
        self.assertEqual(status["gpu_percent"], 81.0)
        self.assertEqual(status["vram_percent"], 50.0)


if __name__ == "__main__":
    unittest.main()
