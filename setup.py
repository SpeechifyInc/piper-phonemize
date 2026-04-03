import platform
import shutil
import subprocess
from pathlib import Path
from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

# Import pybind11 only when needed
try:
    from pybind11.setup_helpers import Pybind11Extension, build_ext
except ImportError:
    # Fallback for when pybind11 is not available
    from setuptools import Extension as Pybind11Extension
    from setuptools.command.build_ext import build_ext

_DIR = Path(__file__).parent
_ESPEAK_DIR = _DIR / "build" / "ei"

# Platform detection
system = platform.system().lower()
machine = platform.machine().lower()
sys_pattern = "*.dylib" if system == "darwin" else "*.so"


# Determine onnxruntime directory based on platform
if system == "darwin":  # macOS
    onnxruntime_dir_name = f"onnxruntime-osx-{machine}-1.14.1"
elif system == "linux":
    if machine in ["x86_64", "amd64"]:
        arch = "x64"
    elif machine in ["aarch64", "arm64"]:
        arch = "arm64"
    else:
        arch = machine
    onnxruntime_dir_name = f"onnxruntime-linux-{arch}-1.14.1"
else:
    raise RuntimeError(f"Unsupported platform: {system}")

_LIB_DIR = _DIR / "lib" / onnxruntime_dir_name
_ONNXRUNTIME_DIR = _LIB_DIR

__version__ = "1.2.0"


def _run_cmake():
    """Download and build native dependencies (espeak-ng, onnxruntime) via CMake."""
    if _ESPEAK_DIR.exists() and _ONNXRUNTIME_DIR.exists():
        return
    build_dir = _DIR / "build"
    build_dir.mkdir(exist_ok=True)
    subprocess.check_call(["cmake", str(_DIR), "-B", str(build_dir)], cwd=str(_DIR))
    subprocess.check_call(
        ["cmake", "--build", str(build_dir), "--config", "Release"],
        cwd=str(_DIR),
    )


def _copy_data_files():
    """Copy runtime data files and dylibs into piper_phonemize/ for bundling."""
    pkg_dir = _DIR / "piper_phonemize"

    # espeak-ng-data
    src = _ESPEAK_DIR / "share" / "espeak-ng-data"
    dst = pkg_dir / "espeak-ng-data"
    if src.exists() and not dst.exists():
        shutil.copytree(str(src), str(dst))

    # libtashkeel_model.ort
    src = _DIR / "etc" / "libtashkeel_model.ort"
    dst = pkg_dir / "libtashkeel_model.ort"
    if src.exists() and not dst.exists():
        shutil.copy2(str(src), str(dst))

    # Dynamic libraries — bundle them so @loader_path / $ORIGIN rpath works
    for lib in (_ESPEAK_DIR / "lib").glob(sys_pattern):
        dst = pkg_dir / lib.name
        if not dst.exists():
            shutil.copy2(str(lib), str(dst))
    for lib in (_ONNXRUNTIME_DIR / "lib").glob(sys_pattern):
        dst = pkg_dir / lib.name
        if not dst.exists():
            shutil.copy2(str(lib), str(dst))


class BuildPy(_build_py):
    """Run cmake before copying package data so bundled files are present."""

    def run(self):
        _run_cmake()
        _copy_data_files()
        super().run()


class BuildExt(build_ext):
    """Run cmake before compiling the C++ extension."""

    def run(self):
        _run_cmake()
        _copy_data_files()
        super().run()


# Use @loader_path / $ORIGIN so the extension finds its bundled dylibs
# regardless of where the package is installed.
if system == "darwin":
    extra_link_args = [
        # @loader_path       → works for normal installs (.so lives inside piper_phonemize/)
        # @loader_path/piper_phonemize → works for editable installs (.so lives in repo root)
        "-Wl,-rpath,@loader_path",
        "-Wl,-rpath,@loader_path/piper_phonemize",
    ]
elif system == "linux":
    extra_link_args = ["-Wl,-rpath,$ORIGIN", "-Wl,-rpath,$ORIGIN/piper_phonemize"]
else:
    extra_link_args = []

ext_modules = [
    Pybind11Extension(
        "piper_phonemize_cpp",
        [
            "src/python.cpp",
            "src/phonemize.cpp",
            "src/phoneme_ids.cpp",
            "src/tashkeel.cpp",
        ],
        define_macros=[("VERSION_INFO", __version__)],
        include_dirs=[str(_ESPEAK_DIR / "include"), str(_ONNXRUNTIME_DIR / "include")],
        library_dirs=[str(_ESPEAK_DIR / "lib"), str(_ONNXRUNTIME_DIR / "lib")],
        libraries=["espeak-ng", "onnxruntime"],
        extra_compile_args=["-std=c++17"],  # uni_algo requires C++17
        extra_link_args=extra_link_args,
    ),
]

setup(
    name="piper_phonemize",
    version=__version__,
    author="Michael Hansen",
    author_email="mike@rhasspy.org",
    url="https://github.com/rhasspy/piper-phonemize",
    description="Phonemization libary used by Piper text to speech system",
    long_description="",
    packages=["piper_phonemize"],
    package_data={
        "piper_phonemize": [
            "espeak-ng-data/**/*",
            "libtashkeel_model.ort",
            "*.dylib",
            "*.so",
        ]
    },
    include_package_data=True,
    ext_modules=ext_modules,
    cmdclass={"build_py": BuildPy, "build_ext": BuildExt},
    zip_safe=False,
    python_requires=">=3.7",
    install_requires=[
        "pybind11>=2.10.0",
        "cmake>=3.25.0",
    ],
)
