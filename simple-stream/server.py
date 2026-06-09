import json
import time
from pathlib import Path

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from sherpa_offline_client import SherpaOfflineClient
from vad_client import VadClient


SAMPLE_RATE = 16000
THRESHOLD = 0.4
SILENCE_SECONDS = 0.25
TARGET_SECONDS = 46
MIN_SPEECH_SECONDS = 0.3
PRE_ROLL_SECONDS = 0.3

WEB_DIR = Path(__file__).resolve().parent / "web"

app = FastAPI(title="Simple Stream ASR", version="0.1.0")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/styles.css", include_in_schema=False)
async def styles() -> FileResponse:
    return FileResponse(WEB_DIR / "styles.css")


@app.get("/app.js", include_in_schema=False)
async def script() -> FileResponse:
    return FileResponse(WEB_DIR / "app.js")


@app.get("/audio-worklet.js", include_in_schema=False)
async def audio_worklet() -> FileResponse:
    return FileResponse(WEB_DIR / "audio-worklet.js")


@app.websocket("/ws/asr")
async def stream_asr(websocket: WebSocket) -> None:
    await websocket.accept()
    session = BrowserAsrSession(websocket)
    await session.run()


class BrowserAsrSession:
    def __init__(self, websocket: WebSocket) -> None:
        self.websocket = websocket
        self.vad_client = VadClient()
        self.sherpa_client = SherpaOfflineClient()
        self.buffer = np.empty(0, dtype=np.float32)
        self.pre_roll_buffer = np.empty(0, dtype=np.float32)
        self.speech_start_time: float | None = None
        self.count_silence = 0

    async def run(self) -> None:
        try:
            await self.sherpa_client.connect()
            await self.websocket.send_json(
                {
                    "type": "started",
                    "sample_rate": SAMPLE_RATE,
                    "threshold": THRESHOLD,
                }
            )

            while True:
                message = await self.websocket.receive()
                if message["type"] == "websocket.disconnect":
                    break
                if message.get("text") == "stop":
                    await self.flush(final=True)
                    await self.websocket.send_json({"type": "stopped"})
                    break
                if message.get("bytes") is not None:
                    await self.process_audio(message["bytes"])
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            await self.websocket.send_json({"type": "error", "message": str(exc)})
        finally:
            await self.sherpa_client.disconnect()

    async def process_audio(self, payload: bytes) -> None:
        if len(payload) % 4 != 0:
            await self.websocket.send_json(
                {
                    "type": "error",
                    "message": f"Expected float32 audio bytes, got {len(payload)} bytes",
                }
            )
            return

        audio_float32 = np.frombuffer(payload, dtype=np.float32).reshape(-1)
        if audio_float32.size == 0:
            return

        vad_pcm16 = (np.clip(audio_float32, -1.0, 1.0) * 32767).astype(np.int16)
        result = self.vad_client.infer(vad_pcm16.reshape(1, -1))
        if "error" in result:
            await self.websocket.send_json({"type": "error", "message": result["error"]})
            return

        score = result["output"]
        if score is None:
            await self.websocket.send_json({"type": "error", "message": "No VAD score returned"})
            return

        probability = float(np.ravel(score)[0])
        if probability > THRESHOLD:
            await self.consume_speech(audio_float32, probability)
        else:
            await self.consume_silence(audio_float32, probability)

    async def consume_speech(self, audio_float32: np.ndarray, probability: float) -> None:
        self.count_silence = 0
        now = time.time()

        if self.speech_start_time is None:
            self.speech_start_time = now - (len(self.pre_roll_buffer) / SAMPLE_RATE)
            self.buffer = np.concatenate([self.pre_roll_buffer, audio_float32])
            self.pre_roll_buffer = np.empty(0, dtype=np.float32)
            await self.websocket.send_json({"type": "speech_start", "probability": probability})
        else:
            self.buffer = np.concatenate([self.buffer, audio_float32])

        if len(self.buffer) >= SAMPLE_RATE * TARGET_SECONDS:
            await self.decode_current_buffer(end=now)
            pre_roll_samples = int(PRE_ROLL_SECONDS * SAMPLE_RATE)
            self.pre_roll_buffer = self.buffer[-pre_roll_samples:].copy()
            self.buffer = self.pre_roll_buffer.copy()
            self.speech_start_time = now - (len(self.pre_roll_buffer) / SAMPLE_RATE)

    async def consume_silence(self, audio_float32: np.ndarray, probability: float) -> None:
        if self.speech_start_time is not None:
            self.buffer = np.concatenate([self.buffer, audio_float32])
            self.count_silence += len(audio_float32)
            if self.count_silence < int(SILENCE_SECONDS * SAMPLE_RATE):
                return

            await self.flush(final=False, probability=probability)
            return

        self.pre_roll_buffer = np.concatenate([self.pre_roll_buffer, audio_float32])
        pre_roll_samples = int(PRE_ROLL_SECONDS * SAMPLE_RATE)
        if len(self.pre_roll_buffer) > pre_roll_samples:
            self.pre_roll_buffer = self.pre_roll_buffer[-pre_roll_samples:]

    async def flush(self, *, final: bool, probability: float | None = None) -> None:
        if self.speech_start_time is not None and len(self.buffer) >= SAMPLE_RATE * MIN_SPEECH_SECONDS:
            await self.decode_current_buffer(end=time.time(), probability=probability)
        self.buffer = np.empty(0, dtype=np.float32)
        self.speech_start_time = None
        self.count_silence = 0
        if final:
            self.pre_roll_buffer = np.empty(0, dtype=np.float32)

    async def decode_current_buffer(self, *, end: float | None, probability: float | None = None) -> None:
        audio = self.buffer.copy()
        start = self.speech_start_time
        duration = (end - start) if start is not None and end is not None else len(audio) / SAMPLE_RATE
        await self.websocket.send_json(
            {
                "type": "speech_end",
                "samples": len(audio),
                "duration": round(duration, 3),
                "probability": probability,
            }
        )

        result_text = await self.sherpa_client.transcribe(audio, sample_rate=SAMPLE_RATE)
        text = sherpa_text(result_text)
        if text:
            await self.websocket.send_json({"type": "text", "text": text})


def sherpa_text(result: str | bytes) -> str:
    result_text = result.decode("utf-8") if isinstance(result, bytes) else str(result)
    try:
        payload = json.loads(result_text)
    except json.JSONDecodeError:
        return result_text if result_text != "<EMPTY>" else ""
    if isinstance(payload, dict) and isinstance(payload.get("text"), str):
        return payload["text"]
    return result_text
