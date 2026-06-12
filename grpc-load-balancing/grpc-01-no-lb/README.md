# gRPC Without Client Load Balancing on Kubernetes

This example intentionally demonstrates the common gRPC load-balancing issue.

It runs:

- 1 client pod
- 3 server pods
- a normal Kubernetes `ClusterIP` Service
- a default gRPC client channel with no `round_robin`

Because gRPC uses long-lived HTTP/2 connections, the client often sticks to one server pod. In the client logs, `server_pod=...` will usually stay the same.

## Run on Kind

```bash
./grpc-load-balancing/grpc-01-no-lb/run-kind.sh
kubectl logs -f deployment/grpc-echo-client -n grpc-no-lb
```

## Benchmark P99

After deploy:

```bash
kubectl exec -n grpc-no-lb deployment/grpc-echo-client -- env BENCH_REQUESTS=1000 BENCH_CONCURRENCY=16 python benchmark.py
```

To use another Kind cluster name:

```bash
KIND_CLUSTER_NAME=my-cluster ./grpc-load-balancing/grpc-01-no-lb/run-kind.sh
```

## Compare With Client-Side Load Balancing

Run the fixed method:

```bash
./grpc-load-balancing/grpc-02-client-lb/run-kind.sh
kubectl logs -f deployment/grpc-echo-client -n grpc-client-lb
```

In that version, the client uses:

- headless Service
- `dns:///...` target
- gRPC `round_robin`

So `server_pod=...` should change across the 3 server pods.

## Cleanup

```bash
kubectl delete -f grpc-load-balancing/grpc-01-no-lb/k8s.yaml -n grpc-no-lb
```
