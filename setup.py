import setuptools
try:
    import pkg_utils
except ImportError:
    import subprocess
    import sys
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "pkg_utils"])
    import pkg_utils
import os

name = 'Biosimulations_tellurium'
dirname = os.path.dirname(__file__)

# get package metadata
md = pkg_utils.get_package_metadata(dirname, name)

# install package
setuptools.setup(
    name=name,
    version=md.version,
    description=("BioSimulations-compliant command-line interface to "
                 "the tellurium simulation program <http://tellurium.analogmachine.org>."),
    long_description=md.long_description,
    url="https://github.com/reproducible-biomedical-modeling/" + name,
    download_url='https://github.com/reproducible-biomedical-modeling/' + name,
    author='Center for Reproducible Biomedical Modeling',
    author_email="info@reproduciblebiomodels.org",
    license="MIT",
    keywords='systems biology modeling simulation',
    packages=setuptools.find_packages(exclude=['tests', 'tests.*']),
    install_requires=md.install_requires,
    extras_require=md.extras_require,
    tests_require=md.tests_require,
    dependency_links=md.dependency_links,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
    ],
    entry_points={
        'console_scripts': [
            'tellurium = Biosimulations_tellurium.__main__:main',
        ],
    },
)
