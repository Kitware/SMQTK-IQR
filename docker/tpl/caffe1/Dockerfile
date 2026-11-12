ARG CUDA_DEVEL_IMAGE_TAG
FROM nvidia/cuda:${CUDA_DEVEL_IMAGE_TAG} AS base

# System Package dependencies
RUN apt-get -y update \
 && apt-get -y install \
        # Basic dependencies
        git \
        cmake \
        python3-dev \
        python3-pip \
        # Caffe Dependencies
        libopenblas-dev \
        libboost-all-dev \
        libprotobuf-dev \
        protobuf-compiler \
        libgoogle-glog-dev \
        libgflags-dev \
        libhdf5-dev \
 # Clean products of ``update``
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Python dependencies for pycaffe
RUN pip3 install numpy==1.18.4 \
                 scikit-image==0.16.2 \
                 protobuf==3.11.3

# Caffe source via git clone
ENV CAFFE_URL="https://github.com/BVLC/caffe.git" \
    CAFFE_VERSION="1.0" \
    CAFFE_DIR_SOURCE="/opt/caffe/source"
RUN git clone https://github.com/BVLC/caffe.git "${CAFFE_DIR_SOURCE}" \
 && cd "${CAFFE_DIR_SOURCE}" \
 && git checkout ${CAFFE_VERSION}
# Inject additional `setup.py` for python wheel generation.

ENV CAFFE_DIR_BUILD="/opt/caffe/build" \
    CAFFE_DIR_INSTALL="/opt/caffe/install"
RUN mkdir -p "${CAFFE_DIR_BUILD}"

##############################################################################
FROM base AS caffe_cpu
# Configure CPU build
RUN mkdir -p "${CAFFE_DIR_BUILD}" \
 && cd "${CAFFE_DIR_BUILD}" \
 && cmake \
    -DCMAKE_BUILD_TYPE:STRING=Release \
    -DBUILD_SHARED_LIBS:BOOL=ON \
    -DCMAKE_INSTALL_PREFIX:PATH="${CAFFE_DIR_INSTALL}" \
    # Use OpenBLAS
    -DBLAS:STRING=Open \
    # Python options \
    -Dpython_version:STRING=3 \
    -DPYTHON_EXECUTABLE:STRING="$(command -v python3)" \
    # Turn off uneeded parts. \
    -DUSE_LEVELDB:BOOL=OFF \
    -DUSE_LMDB:BOOL=OFF \
    -DUSE_OPENCV:BOOL=OFF \
    # CPU-ONLY build options \
    -DCPU_ONLY:BOOL=ON \
    "${CAFFE_DIR_SOURCE}"
# Build/Install SHARED
RUN cd "${CAFFE_DIR_BUILD}" \
 && make install -j$(nproc)
# Build/Install STATIC
# - Doing this intentionally second for python binding library install to be
#   statically compiled for transportability.
RUN cd "${CAFFE_DIR_BUILD}" \
 && cmake -DBUILD_SHARED_LIBS:BOOL=OFF . \
 && make install -j$(nproc)
# Create python wheel
COPY setup.py "${CAFFE_DIR_INSTALL}/python/"
RUN cd "${CAFFE_DIR_INSTALL}/python" \
 && python3 setup.py bdist_wheel \
 && mv ./dist/caffe-"${CAFFE_VERSION}"-py3-none-any.whl /
# Where things are
ENV PATH="${CAFFE_DIR_INSTALL}/bin:${PATH}" \
    PYTHONPATH="${CAFFE_DIR_INSTALL}/python:${PYTHONPATH}" \
    LD_LIBRARY_PATH="${CAFFE_DIR_INSTALL}/lib:${LD_LIBRARY_PATH}"

##############################################################################
FROM base AS caffe_gpu
# Configure GPU build
ARG CUDA_ARCH_BIN_LIST
RUN cd "${CAFFE_DIR_BUILD}" \
 && cmake \
    -DCMAKE_BUILD_TYPE:STRING=Release \
    -DBUILD_SHARED_LIBS:BOOL=ON \
    -DCMAKE_INSTALL_PREFIX:PATH="${CAFFE_DIR_INSTALL}" \
    # Use OpenBLAS
    -DBLAS:STRING=Open \
    # Python options \
    -Dpython_version:STRING=3 \
    -DPYTHON_EXECUTABLE:STRING="$(command -v python3)" \
    # Turn off uneeded parts. \
    -DUSE_LEVELDB:BOOL=OFF \
    -DUSE_LMDB:BOOL=OFF \
    -DUSE_OPENCV:BOOL=OFF \
    # GPU build options \
    -DUSE_CUDNN:BOOL=ON \
    -DCPU_ONLY:BOOL=OFF \
    -DCUDA_ARCH_NAME:STRING=Manual \
    -DCUDA_ARCH_BIN:STRING="${CUDA_ARCH_BIN_LIST}" \
    -DCUDA_ARCH_PTX:STRING="" \
    "${CAFFE_DIR_SOURCE}"
# Build/Install SHARED
RUN cd "${CAFFE_DIR_BUILD}" \
 && make install -j$(nproc)
# Build/Install STATIC
# - Doing this intentionally second for python binding library install to be
#   statically compiled for transportability.
RUN cd "${CAFFE_DIR_BUILD}" \
 && cmake -DBUILD_SHARED_LIBS:BOOL=OFF . \
 && make install -j$(nproc)
# Create python wheel
COPY setup.py "${CAFFE_DIR_INSTALL}/python/"
RUN cd "${CAFFE_DIR_INSTALL}/python" \
 && python3 setup.py bdist_wheel \
 && mv ./dist/caffe-"${CAFFE_VERSION}"-py3-none-any.whl /
# Where things are
ENV PATH="${CAFFE_DIR_INSTALL}/bin:${PATH}" \
    PYTHONPATH="${CAFFE_DIR_INSTALL}/python:${PYTHONPATH}" \
    LD_LIBRARY_PATH="${CAFFE_DIR_INSTALL}/lib:${LD_LIBRARY_PATH}"
