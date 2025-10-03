import platform
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
_LIB_DIR = _DIR / "lib" / f"onnxruntime-osx-{platform.machine()}-1.14.1"
_ONNXRUNTIME_DIR = _LIB_DIR

__version__ = "1.2.0"

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
        extra_link_args=[
            f"-Wl,-rpath,{_ESPEAK_DIR.absolute() / 'lib'}:{_ONNXRUNTIME_DIR.absolute() / 'lib'}",
            f"-Wl,-install_name,@rpath/libespeak-ng.1.dylib",
        ],
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
        + [str(p) for p in (_DIR / "build" / "ei" / "lib").glob("*.dylib")]
        + [str(p) for p in (_DIR / "lib" / f"onnxruntime-osx-{platform.machine()}-1.14.1" / "lib").glob("*.dylib")]
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
