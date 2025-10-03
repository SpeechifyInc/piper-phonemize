import platform
import sys
from pathlib import Path
from setuptools import setup

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
    # For Linux, we need to determine the architecture
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

# Platform-specific linker arguments
if system == "darwin":  # macOS
    extra_link_args = [
        f"-Wl,-rpath,{_ESPEAK_DIR.absolute() / 'lib'}:{_ONNXRUNTIME_DIR.absolute() / 'lib'}",
        f"-Wl,-install_name,@rpath/libespeak-ng.1.dylib",
    ]
elif system == "linux":
    extra_link_args = [
        f"-Wl,-rpath-link,{_ESPEAK_DIR.absolute() / 'lib'}:{_ONNXRUNTIME_DIR.absolute() / 'lib'}",
    ]
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
            str(p) for p in (_DIR / "build" / "ei" / "share" / "espeak-ng-data").rglob("*")
        ]
        + [str(_DIR / "etc" / "libtashkeel_model.ort")]
        + [str(p) for p in (_DIR / "build" / "ei" / "lib").glob(sys_pattern)]
        + [str(p) for p in (_ONNXRUNTIME_DIR / "lib").glob(sys_pattern)]
    },
    include_package_data=True,
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
    python_requires=">=3.7",
    install_requires=[
        "pybind11>=2.10.0",
        "cmake>=3.25.0",
    ],
)
