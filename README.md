[![Latest release](https://img.shields.io/github/v/tag/biosimulators/Biosimulators_tellurium)](https://github.com/biosimulations/Biosimulators_tellurium/releases)
[![PyPI](https://img.shields.io/pypi/v/biosimulators_tellurium)](https://pypi.org/project/biosimulators_tellurium/)
[![CI status](https://github.com/biosimulators/Biosimulators_tellurium/workflows/Continuous%20integration/badge.svg)](https://github.com/biosimulators/Biosimulators_tellurium/actions?query=workflow%3A%22Continuous+integration%22)
[![Test coverage](https://codecov.io/gh/biosimulators/Biosimulators_tellurium/branch/dev/graph/badge.svg)](https://codecov.io/gh/biosimulators/Biosimulators_tellurium)

# BioSimulators-tellurium
BioSimulators-compliant command-line interface and Docker image for the [tellurium](http://tellurium.analogmachine.org/) simulation program.

This command-line interface and Docker image enable users to use tellurium to execute [COMBINE/OMEX archives](https://combinearchive.org/) that describe one or more simulation experiments (in [SED-ML format](https://sed-ml.org)) of one or more models (in [SBML format](http://sbml.org])).

A list of the algorithms and algorithm parameters supported by tellurium is available at [BioSimulators](https://biosimulators.org/simulators/tellurium).

A simple web application and web service for using tellurium to execute COMBINE/OMEX archives is also available at [runBioSimulations](https://run.biosimulations.org).

## Installation

### Dependencies

* Python
* pip
* libncurses
* libxml

### Install Python package
```
pip install biosimulators-tellurium
```

### Install Docker image
```
docker pull ghcr.io/biosimulators/tellurium
```

## Usage

### Local usage
```
usage: biosimulators-tellurium [-h] [-d] [-q] -i ARCHIVE [-o OUT_DIR] [-v]

BioSimulators-compliant command-line interface to the tellurium simulation program <http://tellurium.analogmachine.org>.

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           full application debug mode
  -q, --quiet           suppress all console output
  -i ARCHIVE, --archive ARCHIVE
                        Path to OMEX file which contains one or more SED-ML-
                        encoded simulation experiments
  -o OUT_DIR, --out-dir OUT_DIR
                        Directory to save outputs
  -v, --version         show program's version number and exit
```

### Usage through Docker container
The entrypoint to the Docker image supports the same command-line interface described above.

For example, the following command could be used to use the Docker image to execute the COMBINE/OMEX archive `./modeling-study.omex` and save its outputs to `./`.

```
docker run \
  --tty \
  --rm \
  --mount type=bind,source="$(pwd)",target=/root/in,readonly \
  --mount type=bind,source="$(pwd)",target=/root/out \
  ghcr.io/biosimulators/tellurium:latest \
    -i /root/in/modeling-study.omex \
    -o /root/out
```

## Documentation
Documentation is available at https://docs.biosimulators.org/Biosimulators_tellurium/.

## License
This package is released under the [MIT license](LICENSE).

## Development team
This package was developed by the [Center for Reproducible Biomedical Modeling](http://reproduciblebiomodels.org) and the [Karr Lab](https://www.karrlab.org) at the Icahn School of Medicine at Mount Sinai in New York.

## Questions and comments
Please contact the [BioSimulators Team](mailto:info@biosimulators.org) with any questions or comments.
