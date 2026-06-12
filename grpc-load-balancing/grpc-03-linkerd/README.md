# gRPC Linkerd Load Balancing on Kubernetes

This example is prepared for the Linkerd/service-mesh load-balancing method.

It runs:

- 1 client pod
- 3 server pods
- a normal Kubernetes `ClusterIP` Service
- a default gRPC client channel with no `round_robin`
- namespace `grpc-linkerd`

With Linkerd installed and injection enabled for the namespace, Linkerd can balance gRPC calls without putting `round_robin` in the client. The runner labels the namespace with `linkerd.io/inject=enabled`.

## Run on Kind

```bash
./grpc-load-balancing/grpc-03-linkerd/run-kind.sh
kubectl logs -f deployment/grpc-echo-client -n grpc-linkerd
```

## Benchmark P99

After deploy:

```bash
kubectl exec -n grpc-linkerd deployment/grpc-echo-client -- env BENCH_REQUESTS=1000 BENCH_CONCURRENCY=16 python benchmark.py
```

To use another Kind cluster name:

```bash
KIND_CLUSTER_NAME=my-cluster ./grpc-load-balancing/grpc-03-linkerd/run-kind.sh
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
kubectl delete -f grpc-load-balancing/grpc-03-linkerd/k8s.yaml -n grpc-linkerd
```
