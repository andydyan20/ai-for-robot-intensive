import logging
import os
import time

import grpc

import echo_pb2
import echo_pb2_grpc


TARGET = os.getenv("GRPC_TARGET", "dns:///grpc-echo-server.grpc-client-lb.svc.cluster.local:50051")
INTERVAL_SECONDS = float(os.getenv("INTERVAL_SECONDS", "1"))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # Method 1: client-side gRPC load balancing.
    # Use a headless Kubernetes Service plus dns:/// target so gRPC can resolve
    # every server pod IP, then round_robin spreads RPCs across those addresses.
    service_config = '{"loadBalancingConfig": [{"round_robin": {}}]}'
    options = (
        ("grpc.service_config", service_config),
        ("grpc.lb_policy_name", "round_robin"),
    )

    logging.info("connecting target=%s", TARGET)
    with grpc.insecure_channel(TARGET, options=options) as channel:
        stub = echo_pb2_grpc.EchoServiceStub(channel)
        counter = 0
        while True:
            counter += 1
            try:
                response = stub.Ping(echo_pb2.PingRequest(message=f"request-{counter}"), timeout=5)
                logging.info("reply=%s server_pod=%s", response.message, response.hostname)
            except grpc.RpcError as exc:
                logging.warning("rpc failed code=%s details=%s", exc.code(), exc.details())
            time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
