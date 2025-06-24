#!/bin/bash -xe

VERSION=$(<VERSION)
IMAGE_NAME="ghcr.io/tomoyk/k8s-node-rebooter/k8s-node-rebooter:${VERSION}"

docker build --platform=linux/amd64 -t "${IMAGE_NAME}" .
docker push "${IMAGE_NAME}"