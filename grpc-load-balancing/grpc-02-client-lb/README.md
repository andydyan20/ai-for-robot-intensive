# gRPC Load Balancing on Kubernetes

This is **method 1: load balancing in the gRPC client**.

This example runs one gRPC client Deployment and one gRPC server Deployment with 3 pods.

The server returns its pod hostname. The client calls the server every second and logs which server pod handled each request.

## Why Headless Service?

gRPC uses long-lived HTTP/2 connections. If the client connects through a normal Kubernetes `ClusterIP` Service, the connection can stay pinned to one server pod. This example uses:

- a headless Service: `clusterIP: None`
- a gRPC target: `dns:///grpc-echo-server.grpc-client-lb.svc.cluster.local:50051`
- a client channel option: `round_robin`

That lets the gRPC client resolve the server pod IPs and balance calls across them.

## Build Images

For Kind, the easiest path is the one-file runner:

```bash
./grpc-load-balancing/grpc-02-client-lb/run-kind.sh
```

It will build with Docker Compose, create a Kind cluster named `grpc-local` if needed, load both images into Kind, deploy the manifests, and wait for rollout.

To use another Kind cluster name:

```bash
KIND_CLUSTER_NAME=my-cluster ./grpc-load-balancing/grpc-02-client-lb/run-kind.sh
```

Then watch the client:

```bash
kubectl logs -f deployment/grpc-echo-client -n grpc-client-lb
```

For Docker:

```bash
cd grpc-load-balancing
docker build -f grpc-02-client-lb/Dockerfile.server -t grpc-echo-server-client-lb:latest grpc-02-client-lb
docker build -f grpc-02-client-lb/Dockerfile.client -t grpc-echo-client-client-lb:latest grpc-02-client-lb
```

For Minikube:

```bash
eval "$(minikube docker-env)"
cd grpc-load-balancing
docker build -f grpc-02-client-lb/Dockerfile.server -t grpc-echo-server-client-lb:latest grpc-02-client-lb
docker build -f grpc-02-client-lb/Dockerfile.client -t grpc-echo-client-client-lb:latest grpc-02-client-lb
```

For Kind:

```bash
cd grpc-load-balancing
docker build -f grpc-02-client-lb/Dockerfile.server -t grpc-echo-server-client-lb:latest grpc-02-client-lb
docker build -f grpc-02-client-lb/Dockerfile.client -t grpc-echo-client-client-lb:latest grpc-02-client-lb
kind load docker-image grpc-echo-server-client-lb:latest --name grpc-local
kind load docker-image grpc-echo-client-client-lb:latest --name grpc-local
```

## Deploy

```bash
kubectl apply -f grpc-load-balancing/grpc-02-client-lb/k8s.yaml -n grpc-client-lb
kubectl rollout status deployment/grpc-echo-server -n grpc-client-lb
kubectl rollout status deployment/grpc-echo-client -n grpc-client-lb
```

## Check Load Balancing

```bash
kubectl get pods -n grpc-client-lb -l app=grpc-echo-server -o wide
kubectl logs -f deployment/grpc-echo-client -n grpc-client-lb
```

You should see `server_pod=...` change across the 3 server pods over time.

## Benchmark P99

After deploy:

```bash
kubectl exec -n grpc-client-lb deployment/grpc-echo-client -- env BENCH_REQUESTS=1000 BENCH_CONCURRENCY=16 CLIENT_LB=true python benchmark.py
```

Or benchmark all methods:

```bash
./grpc-load-balancing/benchmark-p99.sh
```

## Cleanup

```bash
kubectl delete -f grpc-load-balancing/grpc-02-client-lb/k8s.yaml -n grpc-client-lb
```
