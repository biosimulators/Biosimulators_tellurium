![Latest version](https://img.shields.io/github/v/tag/biosimulators/Biosimulators_tellurium)
[![PyPI](https://img.shields.io/pypi/v/biosimulators_tellurium)](https://pypi.org/project/biosimulators_tellurium/)
[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/biosimulators/Biosimulators_tellurium/workflow-id)](https://github.com/biosimulators/Biosimulators_tellurium/actions?query=workflow%3Aworkflow-id)
[![Documentation](https://img.shields.io/github/license/biosimulators/Biosimulators_tellurium?badges-awesome-green.svg)](https://biosimulators.github.io/Biosimulators_tellurium/)
[![Issues](https://img.shields.io/github/issues/biosimulators/Biosimulators_tellurium)](https://github.com/biosimulators/Biosimulators_tellurium/issues)
[![License](https://img.shields.io/github/license/biosimulators/Biosimulators_tellurium?badges-awesome-green.svg)](https://github.com/biosimulators/Biosimulators_tellurium/blob/dev/LICENSE)

# BioSimulators-tellurium
BioSimulators-compliant command-line interface and Docker image for the [tellurium](http://tellurium.analogmachine.org/) simulation program.

This command-line interface and Docker image enable users to use tellurium to execute [COMBINE/OMEX archives](https://combinearchive.org/) that describe one or more simulation experiments (in [SED-ML format](https://sed-ml.org)) of one or more models (in [SBML format](http://sbml.org])).

A list of the algorithms and algorithm parameters supported by tellurium is available at [BioSimulators](https://biosimulators.org/simulators/tellurium).

A simple web application and web service for using tellurium to execute COMBINE/OMEX archives is also available at [runBioSimulations](https://run.biosimulations.org).

## Contents
* [Installation](#installation)
* [Usage](#usage)
* [Documentation](#documentation)
* [License](#license)
* [Development team](#development-team)
* [Questions and comments](#questions-and-comments)

## Installation

### Install Python package
```
pip install git+https://github.com/biosimulators/biosimulators_tellurium
```

### Install Docker image
```
docker pull ghcr.io/biosimulators/tellurium
```

## Usage

### Local usage
```
usage: tellurium [-h] [-d] [-q] -i ARCHIVE [-o OUT_DIR] [-v]

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
```
docker run \
  --tty \
  --rm \
  --mount type=bind,source="$(pwd)"/tests/fixtures,target=/root/in,readonly \
  --mount type=bind,source="$(pwd)"/tests/results,target=/root/out \
  ghcr.io/biosimulators/tellurium:latest \
    -i /root/in/BIOMD0000000297.omex \
    -o /root/out
```

## Documentation
Documentation is available at https://biosimulators.github.io/Biosimulators_tellurium/.

## License
This package is released under the [MIT license](LICENSE).

## Development team
This package was developed by the [Center for Reproducible Biomedical Modeling](http://reproduciblebiomodels.org) and the [Karr Lab](https://www.karrlab.org) at the Icahn School of Medicine at Mount Sinai in New York.

## Questions and comments
Please contact the [BioSimulators Team](mailto:info@biosimulators.org) with any questions or comments.
