import concurrent.futures
import logging
import os
import statistics
import time
from collections import Counter

import grpc

import echo_pb2
import echo_pb2_grpc


TARGET = os.getenv("GRPC_TARGET", "grpc-echo-server.default.svc.cluster.local:50051")
REQUESTS = int(os.getenv("BENCH_REQUESTS", "1000"))
CONCURRENCY = int(os.getenv("BENCH_CONCURRENCY", "16"))
WARMUP_REQUESTS = int(os.getenv("BENCH_WARMUP_REQUESTS", "50"))
TIMEOUT_SECONDS = float(os.getenv("BENCH_TIMEOUT_SECONDS", "5"))
CLIENT_LB = os.getenv("CLIENT_LB", "false").lower() == "true"


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((pct / 100) * len(ordered) + 0.999999) - 1))
    return ordered[index]


def channel_options() -> tuple:
    if not CLIENT_LB:
        return ()
    service_config = '{"loadBalancingConfig": [{"round_robin": {}}]}'
    return (
        ("grpc.service_config", service_config),
        ("grpc.lb_policy_name", "round_robin"),
    )


def call_once(stub, request_id: int) -> tuple[float, str | None, str | None]:
    start = time.perf_counter()
    try:
        response = stub.Ping(
            echo_pb2.PingRequest(message=f"bench-{request_id}"),
            timeout=TIMEOUT_SECONDS,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        return latency_ms, response.hostname, None
    except grpc.RpcError as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        return latency_ms, None, f"{exc.code().name}: {exc.details()}"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.info(
        "benchmark target=%s requests=%s concurrency=%s warmup=%s client_lb=%s",
        TARGET,
        REQUESTS,
        CONCURRENCY,
        WARMUP_REQUESTS,
        CLIENT_LB,
    )

    with grpc.insecure_channel(TARGET, options=channel_options()) as channel:
        stub = echo_pb2_grpc.EchoServiceStub(channel)

        for index in range(WARMUP_REQUESTS):
            call_once(stub, -index)

        started = time.perf_counter()
        latencies = []
        hostnames = Counter()
        errors = Counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
            futures = [executor.submit(call_once, stub, index) for index in range(REQUESTS)]
            for future in concurrent.futures.as_completed(futures):
                latency_ms, hostname, error = future.result()
                latencies.append(latency_ms)
                if hostname:
                    hostnames[hostname] += 1
                if error:
                    errors[error] += 1

        elapsed = time.perf_counter() - started
        successes = sum(hostnames.values())
        total = successes + sum(errors.values())

        print("=== gRPC latency benchmark ===")
        print(f"target: {TARGET}")
        print(f"client_lb: {CLIENT_LB}")
        print(f"requests: {REQUESTS}")
        print(f"concurrency: {CONCURRENCY}")
        print(f"success: {successes}")
        print(f"errors: {sum(errors.values())}")
        print(f"elapsed_seconds: {elapsed:.3f}")
        print(f"throughput_rps: {total / elapsed:.2f}")

        if latencies:
            print(f"latency_min_ms: {min(latencies):.3f}")
            print(f"latency_avg_ms: {statistics.mean(latencies):.3f}")
            print(f"latency_p50_ms: {percentile(latencies, 50):.3f}")
            print(f"latency_p95_ms: {percentile(latencies, 95):.3f}")
            print(f"latency_p99_ms: {percentile(latencies, 99):.3f}")
            print(f"latency_max_ms: {max(latencies):.3f}")

        print("server_pods:")
        for hostname, count in hostnames.most_common():
            print(f"  {hostname}: {count}")

        if errors:
            print("errors_by_type:")
            for error, count in errors.most_common():
                print(f"  {error}: {count}")


if __name__ == "__main__":
    main()
