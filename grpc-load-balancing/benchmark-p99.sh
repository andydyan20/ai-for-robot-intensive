#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQUESTS="${BENCH_REQUESTS:-1000}"
CONCURRENCY="${BENCH_CONCURRENCY:-16}"
WARMUP="${BENCH_WARMUP_REQUESTS:-50}"

run_method() {
  local title="$1"
  local folder="$2"
  local namespace="$3"
  local image="$4"
  local target="$5"
  local client_lb="$6"

  echo
  echo "============================================================"
  echo "${title}"
  echo "============================================================"

  "${ROOT_DIR}/${folder}/run-kind.sh"

  echo "Scaling demo client down to avoid benchmark noise"
  kubectl scale deployment/grpc-echo-client --replicas=0 -n "${namespace}"
  kubectl rollout status deployment/grpc-echo-client -n "${namespace}"

  kubectl delete pod grpc-benchmark -n "${namespace}" --ignore-not-found

  kubectl run grpc-benchmark \
    -n "${namespace}" \
    --image="${image}" \
    --image-pull-policy=IfNotPresent \
    --restart=Never \
    --env="GRPC_TARGET=${target}" \
    --env="CLIENT_LB=${client_lb}" \
    --env="BENCH_REQUESTS=${REQUESTS}" \
    --env="BENCH_CONCURRENCY=${CONCURRENCY}" \
    --env="BENCH_WARMUP_REQUESTS=${WARMUP}" \
    --command -- python benchmark.py

  kubectl wait --for=condition=PodScheduled pod/grpc-benchmark -n "${namespace}" --timeout=60s
  kubectl logs -f pod/grpc-benchmark -n "${namespace}"
  kubectl delete pod grpc-benchmark -n "${namespace}" --ignore-not-found
}

run_method \
  "Method 1: no client load balancing" \
  "grpc-01-no-lb" \
  "grpc-no-lb" \
  "grpc-echo-client-no-lb:latest" \
  "grpc-echo-server.grpc-no-lb.svc.cluster.local:50051" \
  "false"

run_method \
  "Method 2: client-side round_robin load balancing" \
  "grpc-02-client-lb" \
  "grpc-client-lb" \
  "grpc-echo-client-client-lb:latest" \
  "dns:///grpc-echo-server.grpc-client-lb.svc.cluster.local:50051" \
  "true"

run_method \
  "Method 3: Linkerd / service-mesh method" \
  "grpc-03-linkerd" \
  "grpc-linkerd" \
  "grpc-echo-client-linkerd:latest" \
  "grpc-echo-server.grpc-linkerd.svc.cluster.local:50051" \
  "false"
