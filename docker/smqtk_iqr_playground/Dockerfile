ARG CUDA_RUNTIME_IMAGE_TAG
ARG CAFFE_COPY_FROM_IMAGE
ARG FAISS_COPY_FROM_IMAGE
##############################################################################
# Base system packages and depedencies
#
FROM ${FAISS_COPY_FROM_IMAGE} AS faiss_image
FROM ${CAFFE_COPY_FROM_IMAGE} AS caffe_image
FROM nvidia/cuda:${CUDA_RUNTIME_IMAGE_TAG} AS smqtk-cpu
MAINTAINER paul.tunison@kitware.com

SHELL ["/bin/bash", "-c"]

# System Package dependencies
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get -y update \
 && apt-get -y install \
        cmake \
        curl \
        less \
        parallel \
        python3-dev \
        python3-pip \
        sudo \
        vim \
        zlib1g-dev \
        libjpeg-dev \
        # PostgreSQL 10 Installation
        postgresql-10 \
        # MongoDB Installation
        mongodb \
        # Caffe/FAISS TPL deps
        libboost-python1.65.1 \
        libboost-system1.65.1 \
        libboost-thread1.65.1 \
        libgoogle-glog0v5 \
        libgflags2.2 \
        libhdf5-100 \
        libprotobuf10 \
        libopenblas-base \
 # Clean up apt resources.
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*
# Python package requirements for Caffe/FAISS + deps for SMQTK parts for
# postgresql/mongo. Add some nice-to-haves in there, too.
RUN pip3 install \
        # Update version of six
        six==1.14.0 \
        # Caffe/FAISS python deps
        numpy==1.18.4 scikit-image==0.16.2 protobuf==3.11.3 \
        # PostgreSQL python client
        psycopg2-binary==2.8.5 \
        # Nice-to-haves
        file-magic==0.4.0 \
        ipython==7.14.0 \
        jedi==0.17.2 \
        scikit-learn==0.24.2

###############################################################################
# COPY in FAISS wheel and install
#
ARG FAISS_VERSION
COPY --from=faiss_image \
     /opt/faiss/python/dist/faiss-${FAISS_VERSION}-py3-none-any.whl /
RUN pip3 install /faiss-${FAISS_VERSION}-py3-none-any.whl \
 && rm /faiss-${FAISS_VERSION}-py3-none-any.whl

###############################################################################
# COPY in Caffe wheel and install
#
# Model downloads
# - Doing this before because we know that the caffe image reference is
#   variable; don't want to have to download twice.
RUN mkdir -p /downloads/caffe/msra-resnet-50 \
 && cd /downloads/caffe/msra-resnet-50 \
 && curl https://data.kitware.com/api/v1/item/5939a7828d777f16d01e4e5d/download \
        -o LICENSE.txt \
 && curl https://data.kitware.com/api/v1/item/5939a61e8d777f16d01e4e52/download \
        -o ResNet_mean.binaryproto \
 && curl https://data.kitware.com/api/v1/item/5939a6188d777f16d01e4e40/download \
        -o ResNet-50-deploy.prototxt \
 && curl https://data.kitware.com/api/v1/item/5939a6198d777f16d01e4e43/download \
        -o ResNet-50-model.caffemodel

COPY --from=caffe_image /caffe-1.0-py3-none-any.whl /
RUN pip3 install /caffe-1.0-py3-none-any.whl \
 && rm /caffe-1.0-py3-none-any.whl

# Export language options to use UTF-8, desired by Click
ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# Export language options to use UTF-8, desired by Click
ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# Shim to expose legacy postgresql CLI tools
# TODO: Clean this up / modernize / don't be running a local database
RUN ln -s /usr/share/postgresql-common/pg_wrapper /usr/local/bin/pg_ctl \
 && ln -s /usr/share/postgresql-common/pg_wrapper /usr/local/bin/postgres

###############################################################################
# SMQTK installation
#
RUN mkdir /smqtk/
COPY docs /smqtk/source/docs
COPY pyproject.toml /smqtk/source
COPY README.md /smqtk/source
COPY smqtk_iqr /smqtk/source/smqtk_iqr
RUN cd /smqtk/source && \
    pip3 install -U pip && \
    pip3 install . && \
    cd / && \
    rm -rf smqtk

# !!! NOTE THIS KLUDGE !!!
# This symlink is lost during the smqtk-iqr installation, as pip currently
# does not support symlinks, so we re-create it here.
RUN ln -s /usr/local/lib/python3.6/dist-packages/smqtk_iqr/web/search_app/templates/base.html \
          /usr/local/lib/python3.6/dist-packages/smqtk_iqr/web/search_app/modules/iqr/templates/base.html

# Add ``smqtk`` user
RUN useradd -mr -s /bin/bash smqtk \
 # sudo permission for modifying permissions at runtime (see entrypoint.sh).
 # TODO: Remove this eventually since its defeating the point of having a user.
 && echo "smqtk ALL=(ALL:ALL) NOPASSWD:ALL" >>/etc/sudoers \
 && mkdir -m 0555 /images

USER smqtk
WORKDIR /home/smqtk

# Setup expected user-space directories.
RUN mkdir -p data/{models,configs,logs,db.psql,db.mongo} \
 && ln -s /images data/images \
    # Link to Caffe downloads
 && mkdir caffe \
 && ln -s /downloads/caffe/msra-resnet-50 caffe/msra_resnet

# Configuration for Matplotlib to just use the Agg backend, not Tkinter
COPY --chown=smqtk:smqtk \
     docker/smqtk_iqr_playground/matplotlibrc \
     .config/matplotlib/

# Copy in general entrypoint and CPU-variant test script
COPY --chown=smqtk:smqtk \
     docker/smqtk_iqr_playground/entrypoint.sh \
     docker/smqtk_iqr_playground/descr_comp_test.cpu.py \
     /home/smqtk/

# Copy in general and CPU-variant configs
COPY --chown=smqtk:smqtk \
     docker/smqtk_iqr_playground/default_confs/* \
     docker/smqtk_iqr_playground/default_confs/cpu/* \
     /home/smqtk/data/configs/

ENTRYPOINT ["/home/smqtk/entrypoint.sh"]
EXPOSE 5000 5001

###############################################################################
# Add GPU variant specific files and configuration
#
FROM smqtk-cpu AS smqtk-gpu
# Add GPU-variant test script
COPY --chown=smqtk:smqtk \
     docker/smqtk_iqr_playground/descr_comp_test.gpu.py \
     /home/smqtk/
# Overwrite CPU-variance configs with the GPU variants.
COPY --chown=smqtk:smqtk \
     docker/smqtk_iqr_playground/default_confs/gpu/* \
     /home/smqtk/data/configs/
