import logging
import os
import time

import grpc

import echo_pb2
import echo_pb2_grpc


TARGET = os.getenv("GRPC_TARGET", "grpc-echo-server.grpc-linkerd.svc.cluster.local:50051")
INTERVAL_SECONDS = float(os.getenv("INTERVAL_SECONDS", "1"))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.info("connecting target=%s", TARGET)

    # No client-side load balancing here.
    # gRPC Python uses pick_first by default, so one long-lived HTTP/2 channel
    # can stay pinned to a single backend selected by the Kubernetes Service.
    with grpc.insecure_channel(TARGET) as channel:
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
