import re
import setuptools
import subprocess
import sys
try:
    result = subprocess.run(
        [sys.executable, "-m", "pip", "show", "pkg_utils"],
        check=True, capture_output=True)
    match = re.search(r'\nVersion: (.*?)\n', result.stdout.decode(), re.DOTALL)
    assert match and tuple(match.group(1).split('.')) >= ('0', '0', '5')
except (subprocess.CalledProcessError, AssertionError):
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-U", "pkg_utils"],
        check=True)
import os
import pkg_utils

name = 'biosimulators_tellurium'
dirname = os.path.dirname(__file__)

# get package metadata
md = pkg_utils.get_package_metadata(dirname, name)

# install package
setuptools.setup(
    name=name,
    version=md.version,
    description=("BioSimulators-compliant command-line interface to "
                 "the tellurium simulation program <http://tellurium.analogmachine.org>."),
    long_description=md.long_description,
    url="https://github.com/biosimulators/Biosimulators_tellurium",
    download_url="https://github.com/biosimulators/Biosimulators_tellurium",
    author='BioSimulators Team',
    author_email="info@biosimulators.org",
    license="MIT",
    keywords=[
        'systems biology',
        'computational biology',
        'kinetic modeling',
        'numerical simulation',
        'stochastic',
        'SBML',
        'SED-ML',
        'COMBINE',
        'BioSimulators',
    ],
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
            'tellurium = biosimulators_tellurium.__main__:main',
        ],
    },
)
