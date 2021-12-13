#!/bin/bash
#
# Simple script for starting the SMQTK classifier service
#

# Container image to use
CLASSIFIER_CONTAINER=${SMQTK_REGISTRY}/classifier_service
CLASSIFIER_CONTAINER_VERSION="latest-cpu"
CONTAINER_NAME="smqtk-classifier-service-cpu"
CLASSIFIER_SERVICE_PORT=5002

docker run \
  -p ${CLASSIFIER_SERVICE_PORT}:5002 \
  --name "${CONTAINER_NAME}" \
  ${CLASSIFIER_CONTAINER}:${CLASSIFIER_CONTAINER_VERSION}
