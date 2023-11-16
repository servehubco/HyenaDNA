#!/bin/bash
CONDA_INSTALL_URL=${CONDA_INSTALL_URL:-"https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"}

# Install Miniconda locally
rm -rf lib/conda
rm -f /tmp/Miniconda3-latest-Linux-x86_64.sh
wget -P /tmp \
    "${CONDA_INSTALL_URL}" \
    && bash /tmp/Miniconda3-latest-Linux-x86_64.sh -b -p lib/conda \
    && rm /tmp/Miniconda3-latest-Linux-x86_64.sh

# Grab conda-only packages
export PATH=lib/conda/bin:$PATH
lib/conda/bin/python3 -m pip install nvidia-pyindex
conda env create -f esm/environment.yml

