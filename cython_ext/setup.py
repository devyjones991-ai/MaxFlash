"""
Setup script для компиляции Cython расширений.
"""
from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy

extensions = [
    Extension(
        "cython_ext.feature_calc",
        ["cython_ext/feature_calc.pyx"],
        include_dirs=[numpy.get_include()],
        extra_compile_args=["-O3"],
    ),
    Extension(
        "cython_ext.scoring",
        ["cython_ext/scoring.pyx"],
        include_dirs=[numpy.get_include()],
        extra_compile_args=["-O3"],
    ),
]

setup(
    name="maxflash_cython_ext",
    ext_modules=cythonize(extensions, compiler_directives={"language_level": "3"}),
    zip_safe=False,
)

