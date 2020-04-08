# Biosimulations_tellurium
Biosimulations-compliant command-line interface to the [tellurium](http://tellurium.analogmachine.org/) simulation program.

## Contents
* [Installation](#installation)
* [Usage](#usage)
* [License](#license)
* [Development team](#development-team)
* [Questions and comments](#questions-and-comments)

## Installation

```
pip install git+https://github.com/reproducible-biomedical-modeling/Biosimulations_tellurium
```

## Usage
```
usage: Biosimulations-tellurium [-h] [-d] [-q] -i SIM_FILE [-o OUT_DIR] [-v]

BioSimulations-compliant command-line interface to the tellurium simulation program

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           full application debug mode
  -q, --quiet           suppress all console output
  -i SIM_FILE, --sim-file SIM_FILE
                        Path to SED-ML file which describes a simulation
                        experiment
  -o OUT_DIR, --out-dir OUT_DIR
                        Directory to save outputs
  -v, --version         show program's version number and exit
```

## License
This package is released under the [MIT license](LICENSE).

## Development team
This package was developed by the [Center for Reproducible Biomedical Modeling](http://reproduciblebiomodels.org) and the [Karr Lab](https://www.karrlab.org) at the Icahn School of Medicine at Mount Sinai in New York.

## Questions and comments
Please contact the [Center for Reproducible Biomedical Modeling](mailto:info@reproduciblebiomodels.org) with any questions or comments.
