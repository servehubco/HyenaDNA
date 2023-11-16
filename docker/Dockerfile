# Using Ray 2.5.0 base image
FROM rayproject/ray-ml:2.6.1-py39-gpu

# Set the working directory
WORKDIR /workspace

# Installing system utilities
USER root
RUN apt-get update && apt-get install -y sudo && sudo apt-get install -y \
    git-lfs aria2 awscli \
    && rm -rf /var/lib/apt/lists/*


# Clone the OpenFold repository
# Assuming OpenFold's repository URL is: https://github.com/your-openfold-repo-url/openfold
# Replace 'your-openfold-repo-url' with the actual URL
RUN git clone https://github.com/aqlaboratory/openfold.git openfold && \
    cd openfold && \
    git config advice.detachedHead false && \
    git checkout 4b41059694619831a7db195b7e0988fc4ff3a307 && \
    git lfs pull

# Running the OpenFold setup script
RUN cd openfold && bash scripts/install_third_party_dependencies.sh

# Add conda to the PATH and activate the environment
ENV PATH /workspace/openfold/miniconda3/bin:$PATH
RUN echo "source /workspace/openfold/scripts/activate_conda_env.sh" >> ~/.bashrc

# Install HH-suite
RUN cd openfold && bash scripts/install_hh_suite.sh

# Compile OpenFold's CUDA kernels
RUN cd openfold && bash -c "source scripts/activate_conda_env.sh && python3 setup.py install"

COPY ./download_weights.py download_weights.py
COPY ./requirements.in requirements.in
RUN pip install "fair-esm[esmfold]" && pip-compile && pip install -r requirements.txt
RUN python download_weights.py

# Provide an entry point to keep the container running
ENTRYPOINT ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]
