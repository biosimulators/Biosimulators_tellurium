# Build image:
#   docker build --tag crbm/biosimulations_tellurium:2.4.1 --tag crbm/biosimulations_tellurium:latest .
#
# Run image:
#   docker run \
#     --tty \
#     --rm \
#     --mount type=bind,source="$(pwd)"/tests/fixtures,target=/root/in,readonly \
#     --mount type=bind,source="$(pwd)"/tests/results,target=/root/out \
#     crbm/biosimulations_tellurium:latest \
#       -i /root/in/BIOMD0000000297.omex \
#       -o /root/out

# Base OS
FROM ubuntu:18.04

# metadata
LABEL base_image="ubuntu:18.04"
LABEL version="2.4.1"
LABEL software="tellurium"
LABEL software.version="2.4.1"
LABEL about.summary="Python-based environment for model building, simulation, and analysis that facilitates reproducibility of models in systems and synthetic biology"
LABEL about.home="http://tellurium.analogmachine.org/"
LABEL about.documentation="https://tellurium.readthedocs.io/"
LABEL about.license_file="https://github.com/sys-bio/tellurium/blob/master/LICENSE.txt"
LABEL about.license="SPDX:Apache-2.0"
LABEL about.tags="kinetic modeling,dynamical simulation,systems biology,SBML,SED-ML,COMBINE,OMEX"
LABEL maintainer="Jonathan Karr <karr@mssm.edu>"

# Install requirements
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
    && pip3 install -U pip \
    && pip3 install -U setuptools \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copy code for command-line interface into image and install it
COPY . /root/Biosimulations_tellurium
RUN pip3 install /root/Biosimulations_tellurium

# Configure matplotlib backend
ENV MPLBACKEND="module://Agg" \
    PYTHONWARNINGS="ignore:The 'warn' parameter of use():UserWarning:tellurium.tellurium,ignore:Matplotlib is currently using agg:UserWarning:tellurium.plotting.engine_mpl"

# Entrypoint
ENTRYPOINT ["tellurium"]
CMD []
