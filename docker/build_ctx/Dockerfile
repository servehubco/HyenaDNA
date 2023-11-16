# Using Ray 2.5.0 base image
FROM rayproject/ray-ml:2.6.1-py39-gpu

# Set the working directory
WORKDIR /workspace

# Installing system utilities
USER root
RUN apt-get update && apt-get install -y sudo && sudo apt-get install -y \
    git-lfs aria2 awscli \
    && rm -rf /var/lib/apt/lists/*


# Clone the esm repository
RUN git clone https://github.com/facebookresearch/esm.git esm && \
    cd esm && \
    git config advice.detachedHead false && \
    git checkout 2b36991

# Create the conda env and make it always active
COPY scripts scripts
RUN bash scripts/create_conda_env.sh && echo "source /workspace/scripts/activate_conda_env.sh" >> ~/.bashrc


RUN pip install "fair-esm[esmfold]"
RUN pip install 'dllogger @ git+https://github.com/NVIDIA/dllogger.git'
RUN pip install 'openfold @ git+https://github.com/aqlaboratory/openfold.git@4b41059694619831a7db195b7e0988fc4ff3a307'
RUN pip install biotite fastapi
RUN rm esm/README.md
COPY README.md esm/README.md
RUN bash esm/scripts/download_weights.sh /home/ray/.cache/torch/hub
#COPY ./download_weights.py download_weights.py
#RUN python download_weights.py


# Provide an entry point to keep the container running
ENTRYPOINT ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]
