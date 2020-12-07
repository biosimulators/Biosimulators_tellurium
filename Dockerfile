# Build image:
#   docker build --tag biosimulators/tellurium:2.1.6 --tag biosimulators/tellurium:latest .
#
# Run image:
#   docker run \
#     --tty \
#     --rm \
#     --mount type=bind,source="$(pwd)"/tests/fixtures,target=/root/in,readonly \
#     --mount type=bind,source="$(pwd)"/tests/results,target=/root/out \
#     biosimulators/tellurium:latest \
#       -i /root/in/BIOMD0000000297.omex \
#       -o /root/out

# Base OS
FROM python:3.7.9-slim-buster

# metadata
LABEL \
    org.opencontainers.image.title="tellurium" \
    org.opencontainers.image.version="2.1.5" \
    org.opencontainers.image.description="Python-based environment for model building, simulation, and analysis that facilitates reproducibility of models in systems and synthetic biology" \
    org.opencontainers.image.url="http://tellurium.analogmachine.org/" \
    org.opencontainers.image.documentation="https://tellurium.readthedocs.io/" \
    org.opencontainers.image.source="https://github.com/biosimulators/Biosimulators_tellurium" \
    org.opencontainers.image.authors="BioSimulators Team <info@biosimulators.org>" \
    org.opencontainers.image.vendor="BioSimulators Team" \
    org.opencontainers.image.licenses="Apache-2.0" \
    \
    base_image="python:3.7.9-slim-buster" \
    version="0.0.1" \ 
    software="tellurium" \
    software.version="2.1.6" \
    about.summary="Python-based environment for model building, simulation, and analysis that facilitates reproducibility of models in systems and synthetic biology" \
    about.home="http://tellurium.analogmachine.org/" \
    about.documentation="https://tellurium.readthedocs.io/" \
    about.license_file="https://github.com/sys-bio/tellurium/blob/develop/LICENSE.txt" \
    about.license="SPDX:Apache-2.0" \
    about.tags="kinetic modeling,dynamical simulation,systems biology,biochemical networks,SBML,SED-ML,COMBINE,OMEX,BioSimulators" \
    maintainer="BioSimulators Team <info@biosimulators.org>"

# Install requirements
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends \
        libxml2 \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copy code for command-line interface into image and install it
COPY . /root/Biosimulators_tellurium
RUN pip install /root/Biosimulators_tellurium

# Configure matplotlib backend
ENV MPLBACKEND="module://Agg" \
    PYTHONWARNINGS="ignore:The 'warn' parameter of use():UserWarning:tellurium.tellurium,ignore:Matplotlib is currently using agg:UserWarning:tellurium.plotting.engine_mpl"

# Entrypoint
ENTRYPOINT ["tellurium"]
CMD []
