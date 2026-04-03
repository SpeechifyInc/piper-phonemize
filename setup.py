import platform
import subprocess
from pathlib import Path

import pybind11
from pybind11.setup_helpers import Pybind11Extension
from pybind11.setup_helpers import build_ext as _build_ext
from setuptools import setup

_DIR = Path(__file__).parent
_VERSION = "1.2.0"
_ONNXRUNTIME_VERSION = "1.14.1"


def _onnxruntime_dir():
    system = platform.system()
    machine = platform.machine()
    if system == "Linux":
        if machine == "x86_64":
            prefix = f"onnxruntime-linux-x64-{_ONNXRUNTIME_VERSION}"
        elif machine == "aarch64":
            prefix = f"onnxruntime-linux-aarch64-{_ONNXRUNTIME_VERSION}"
        elif machine == "armv7l":
            prefix = f"onnxruntime-linux-arm32-{_ONNXRUNTIME_VERSION}"
        else:
            raise RuntimeError(f"Unsupported Linux architecture: {machine}")
    elif system == "Darwin":
        if machine == "arm64":
            prefix = f"onnxruntime-osx-arm64-{_ONNXRUNTIME_VERSION}"
        else:
            prefix = f"onnxruntime-osx-x86_64-{_ONNXRUNTIME_VERSION}"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")
    return _DIR / "lib" / prefix


class build_ext(_build_ext):
    def run(self):
        self._cmake_dir = Path(self.build_temp) / "cmake"
        self._cmake_dir.mkdir(parents=True, exist_ok=True)
        self._run_cmake()
        super().run()

    def _run_cmake(self):
        # Configure: also downloads onnxruntime via file(DOWNLOAD ...) if not present
        subprocess.run(
            ["cmake", str(_DIR), "-DCMAKE_BUILD_TYPE=Release"],
            cwd=str(self._cmake_dir),
            check=True,
        )
        # Build only espeak-ng; skip the C++ lib/exe/tests
        subprocess.run(
            ["cmake", "--build", str(self._cmake_dir), "--target", "espeak_ng_external"],
            check=True,
        )

    def build_extensions(self):
        espeak_dir = self._cmake_dir / "ei"
        ort_dir = _onnxruntime_dir()
        for ext in self.extensions:
            ext.include_dirs.extend([
                pybind11.get_include(),
                str(espeak_dir / "include"),
                str(ort_dir / "include"),
            ])
            ext.library_dirs.extend([
                str(espeak_dir / "lib"),
                str(ort_dir / "lib"),
            ])
        super().build_extensions()


ext_modules = [
    Pybind11Extension(
        "piper_phonemize_cpp",
        [
            "src/python.cpp",
            "src/phonemize.cpp",
            "src/phoneme_ids.cpp",
            "src/tashkeel.cpp",
        ],
        define_macros=[("VERSION_INFO", _VERSION)],
        libraries=["espeak-ng", "onnxruntime"],
    ),
]

setup(
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
