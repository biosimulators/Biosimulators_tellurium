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
#       -i /root/in/BIOMD0000000297.sedml \
#       -o /root/out

# Base OS
FROM ubuntu

# Copy code for command-line interface into image
COPY . /root/Biosimulations_tellurium

# Install command-line interface to tellurium
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
    && pip3 install -U pip \
    && pip3 install -U setuptools \
    \
    && pip3 install /root/Biosimulations_tellurium \
    \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Configure matplotlib backend
ENV MPLBACKEND="module://Agg" \
    PYTHONWARNINGS="ignore:The 'warn' parameter of use():UserWarning:tellurium.tellurium"

# Entrypoint
ENTRYPOINT ["Biosimulations-tellurium"]
CMD []
