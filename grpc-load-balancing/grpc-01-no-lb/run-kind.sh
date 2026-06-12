#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLUSTER_NAME="${KIND_CLUSTER_NAME:-grpc-local}"
NAMESPACE="${K8S_NAMESPACE:-grpc-no-lb}"

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "docker compose is required but was not found"
  exit 1
fi


if ! kind get clusters | grep -qx "${CLUSTER_NAME}"; then
  echo "Creating Kind cluster: ${CLUSTER_NAME}"
  kind create cluster --name "${CLUSTER_NAME}"
fi

# Use the existing kind context
kubectl config use-context "kind-${CLUSTER_NAME}"

# Create namespace if it does not exist
kubectl get namespace "${NAMESPACE}" >/dev/null 2>&1 || \
  kubectl create namespace "${NAMESPACE}"

# Set current context to use this namespace by default
kubectl config set-context --current --namespace="${NAMESPACE}"

echo "Building Docker images"
"${COMPOSE[@]}" -f "${ROOT_DIR}/compose.yaml" build

echo "Loading images into Kind"
kind load docker-image grpc-echo-server-no-lb:latest --name "${CLUSTER_NAME}"
kind load docker-image grpc-echo-client-no-lb:latest --name "${CLUSTER_NAME}"

echo "Deploying to Kubernetes"
kubectl apply -n "${NAMESPACE}" -f "${ROOT_DIR}/k8s.yaml"

echo "Waiting for rollouts"
kubectl rollout status deployment/grpc-echo-server -n "${NAMESPACE}"
kubectl rollout status deployment/grpc-echo-client -n "${NAMESPACE}"

echo
echo "Server pods:"
kubectl get pods -n "${NAMESPACE}" -l app=grpc-echo-server -o wide

echo
echo "Client logs:"
echo "kubectl logs -f deployment/grpc-echo-client -n ${NAMESPACE}"
