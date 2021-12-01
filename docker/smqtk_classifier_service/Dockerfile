ARG CUDA_RUNTIME_IMAGE_TAG
ARG CAFFE_COPY_FROM_IMAGE
##############################################################################
# Base system packages and depedencies
#
FROM ${CAFFE_COPY_FROM_IMAGE} AS caffe_image
FROM nvidia/cuda:${CUDA_RUNTIME_IMAGE_TAG} AS smqtk-cpu

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
        vim \
        zlib1g-dev \
        libjpeg-dev \
        # Caffe TPL deps
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
        # Caffe python deps
        numpy==1.18.4 scikit-image==0.16.2 protobuf==3.11.3 \
        scikit-learn==0.24.2

###############################################################################
# COPY in Caffe wheel and install
#
# Model downloads
# - Doing this before because we know that the caffe image reference is
#   variable; don't want to have to download twice.
RUN mkdir -p /caffe/models/msra_resnet \
 && cd /caffe/models/msra_resnet \
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
    rm -rf smqtk && \
    mkdir /configuration

ADD docker/smqtk_classifier_service/default_server.cpu.json \
    /configuration/server.json
ADD docker/smqtk_classifier_service/entrypoint.sh \
    /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
EXPOSE 5002

###############################################################################
# Add GPU variant specific files and configuration
#
FROM smqtk-cpu AS smqtk-gpu
ADD docker/smqtk_classifier_service/default_server.gpu.json \
    /configuration/server.json
