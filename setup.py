from setuptools import setup, Extension


try:
    from Cython.Build import cythonize
    extensions = [
        Extension(
            'optionstools.pricing',
            sources=['optionstools/pricing.pyx'],
        ),
    ]
    extensions = cythonize(extensions)
except ImportError:
    extensions = [
        Extension(
            'optionstools.pricing',
            sources=['optionstools/pricing.c'],
        ),
    ]


# pull requirements
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

# pull version
exec(open('optionstools/version.py').read())


setup(
    name='optionstools',
    version=__version__,
    install_requires=requirements,
    setup_requires=[
        'setuptools>=18.0',  # automatically handles Cython extensions
    ],
    scripts=['bin/optionstools'],
    ext_modules=extensions,
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
)