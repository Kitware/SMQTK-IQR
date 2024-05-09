#!/bin/bash
__doc__="
Simple script for starting the SMQTK IQR container over a directory of
images. The ``-t`` option may be optionally provided to tile input imagery
into 128x128 tiles (default). We drop into watching the processing status
after starting the container.

If the container is already running, we just start watching the container's
status.
"

# Script configuration
DRY_RUN=${DRY_RUN:=0}
DEV_TRACE=${DEV_TRACE:=0}
# Container image to use
SMQTK_REGISTRY=${SMQTK_REGISTRY:=gitlab.kitware.com:4567/smqtk-public/smqtk-iqr-docker}
IQR_CONTAINER=${IQR_CONTAINER:=${SMQTK_REGISTRY}/iqr_playground}
IQR_CONTAINER_VERSION=${IQR_CONTAINER_VERSION:=latest-cuda9.2-cudnn7-runtime-ubuntu18.04}
# Name for run container instance
CONTAINER_NAME=${CONTAINER_NAME:=smqtk-iqr-playground-gpu}
IQR_GUI_PORT_PUBLISH=${IQR_GUI_PORT_PUBLISH:=5000}
IQR_REST_PORT_PUBLISH=${IQR_REST_PORT_PUBLISH:=5001}
IMAGE_DIR=${IMAGE_DIR:=""}
# IMAGE_DIR=${1:-${IMAGE_DIR:-""}} # todo: if we do have a $1, we need to shift

if [[ "${DEV_TRACE}" != "0" ]]; then
    set -x
fi

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
	# Running as a script
	set -eo pipefail
fi

echo "
"
show_config(){
    python -c "
def identity(arg=None, *args, **kwargs):
    return arg
try:
    from ubelt import highlight_code, color_text
except ImportError:
    highlight_code = color_text = identity


print(color_text('''
=====
SMQTK
=====
''', 'green'))

print(highlight_code('''

Environment configuration:

DRY_RUN=$DRY_RUN
DEV_TRACE=$DEV_TRACE

SMQTK_REGISTRY=$SMQTK_REGISTRY
IQR_CONTAINER=$IQR_CONTAINER
IQR_CONTAINER_VERSION=$IQR_CONTAINER_VERSION
CONTAINER_NAME=$CONTAINER_NAME
IQR_GUI_PORT_PUBLISH=$IQR_GUI_PORT_PUBLISH
IQR_REST_PORT_PUBLISH=$IQR_REST_PORT_PUBLISH
IMAGE_DIR=$IMAGE_DIR

''', lexer_name='bash'))
    "
}


main(){
    show_config

    if ! (docker ps | grep -q "${CONTAINER_NAME}")
    then
      # Make sure image directory exists as a directory.
      if [ ! -d "${IMAGE_DIR}" ]
      then
        echo "ERROR: Input image directory path was not a directory: ${IMAGE_DIR}"
        exit 1
      fi
      docker run -d --gpus all \
        -p "${IQR_GUI_PORT_PUBLISH}:5000" \
        -p "${IQR_REST_PORT_PUBLISH}:5001" \
        -v "${IMAGE_DIR}":/images \
        --name "${CONTAINER_NAME}" \
        "${IQR_CONTAINER}:${IQR_CONTAINER_VERSION}" -b "$@"
    else
        echo "Container is already running"
    fi

    watch -n1 "
nvidia-smi
docker exec ${CONTAINER_NAME} bash -c '[ -d data/image_tiles ] && echo && echo \"Image tiles generated: \$(ls data/image_tiles | wc -l)\"'
echo
docker exec ${CONTAINER_NAME} tail \
    data/logs/compute_many_descriptors.log \
    data/logs/train_itq.log data/logs/compute_hash_codes.log \
    data/logs/runApp.IqrSearchDispatcher.log \
    data/logs/runApp.IqrService.log
    "
}


# bpkg convention
# https://github.com/bpkg/bpkg
if [[ ${BASH_SOURCE[0]} != "$0" ]]; then
    # We are sourcing the library
    show_config
    echo "Sourcing prepare_system as a library and environment"
else

    for var in "$@"
    do
        if [[ "$var" == "--help" ]]; then
            log "showing help"
            show_config
            echo "The above shows the current environment. Set the values for appropriate variables"
            echo "...exiting"
            exit 1
        fi
    done

    if [[ "$DRY_RUN" == "0" ]]; then
        # Executing file as a script
        main "${@}"
        exit $?
    else
        show_config
    fi
fi
