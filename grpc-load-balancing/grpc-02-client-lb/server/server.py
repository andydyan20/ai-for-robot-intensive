from concurrent import futures
import logging
import os

import grpc

import echo_pb2
import echo_pb2_grpc


PORT = int(os.getenv("PORT", "50051"))


class EchoService(echo_pb2_grpc.EchoServiceServicer):
    def Ping(self, request, context):
        hostname = os.getenv("HOSTNAME", "unknown")
        logging.info("message=%s hostname=%s", request.message, hostname)
        return echo_pb2.PingReply(
            message=f"pong: {request.message}",
            hostname=hostname,
        )


def serve() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    echo_pb2_grpc.add_EchoServiceServicer_to_server(EchoService(), server)
    server.add_insecure_port(f"[::]:{PORT}")
    server.start()
    logging.info("gRPC echo server listening on %s", PORT)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
