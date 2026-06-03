import numpy as np
import websockets

class SherpaOfflineClient:
    def __init__(self, url="ws://localhost:6006", chunk_bytes=262_144):
        self.url = url
        self.chunk_bytes = chunk_bytes
        self.ws = None

    async def connect(self):
        self.ws = await websockets.connect(self.url)
        print(f"Connected to Sherpa Offline WebSocket at {self.url}")

    async def transcribe(self, chunk: np.ndarray, sample_rate: int = 16000):
        if self.ws is None:
            raise Exception("WebSocket connection is not established")

        audio = np.ascontiguousarray(chunk.reshape(-1), dtype=np.float32)
        payload = audio.tobytes()

        header = (
            int(sample_rate).to_bytes(4, "little", signed=True)
            + len(payload).to_bytes(4, "little", signed=True)
        )

        await self.ws.send(header)

        for offset in range(0, len(payload), self.chunk_bytes):
            await self.ws.send(payload[offset:offset + self.chunk_bytes])

        return await self.ws.recv()

    async def send_audio_chunk(self, chunk: np.ndarray):
        if self.ws is None:
            raise Exception("WebSocket connection is not established")

        await self.ws.send(chunk.tobytes())
        print(f"Sent audio chunk of size {chunk.nbytes} bytes")

    async def disconnect(self):
        if self.ws is not None:
            try:
                await self.ws.send("Done")
            finally:
                await self.ws.close()
                self.ws = None
                print("Disconnected from Sherpa Offline WebSocket")

sherpa_offline_client = SherpaOfflineClient()
