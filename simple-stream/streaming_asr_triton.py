import argparse
import asyncio
from dataclasses import dataclass
import sys
from pathlib import Path
import json
from vad_client import vad_client
from asr_triton_client import asr_triton_client

import queue
import threading
import time

import sounddevice as sd
import numpy as np

@dataclass
class SpeechSegment:
    audio: np.ndarray
    start: float
    end: float

speech_queue = queue.Queue()
speech_start_time = None

SAMPLE_RATE = 16000
MIN_SPEECH_SECONDS = 0.3
PRE_ROLL_SECONDS = 0.3
SILENCE_SECONDS = 0.25
TARGET_BYTES = 4600


def asr_worker_thread():
    asyncio.run(asr_worker())

async def asr_worker():
    print("ASR worker started")

    while True:
        item = speech_queue.get()
        try:
            audio = item.get("audio")
            start = item.get("start")
            end = item.get("end")

            if audio is None or len(audio) == 0:
                print("ASR skipped empty audio segment")
                continue

            duration = end - start if start is not None and end is not None else len(audio) / SAMPLE_RATE
            print(f"ASR duration={duration:.2f}s,samples={len(audio)}.")

            result = asr_triton_client.infer(audio, callid="1001", domain="macostest", endpoint=1)

            if "error" in result:
                print(f"Error: {result['error']}")
                continue
            print(f"ASR result: {result}")
            transcript = result.get("text", "")
            print(f"Text:{transcript}", end="\n")
        except Exception as exc:
            print(f"ASR error: {exc}")
        finally:
            speech_queue.task_done()

def main():

    global speech_start_time

    devices = sd.query_devices()
    if len(devices) == 0:
        print("No audio devices found")
        sys.exit(-1)

    print(devices)
    default_input_device_idx = sd.default.device[0]
    print(f"Default input device: {devices[default_input_device_idx]['name']}")

    sample_rate = SAMPLE_RATE
    sample_per_read = int(0.032 * sample_rate)  # read XX second of audio
    buffer = np.empty(0, dtype=np.float32)
    threshold = 0.4 # VAD threshold probability
    silence_samples = int(SILENCE_SECONDS * sample_rate) # silence duration to consider end of speech
    count_silence = 0
    pre_roll_samples = int(PRE_ROLL_SECONDS * sample_rate)
    min_speech_samples = int(MIN_SPEECH_SECONDS * sample_rate)

    with sd.InputStream(channels=1, dtype="float32", samplerate=sample_rate) as s:
        while True:
            current_time = time.time()

            samples, _ = s.read(sample_per_read)
            audio_float32 = samples.reshape(-1)

            vad_pcm16 = (np.clip(audio_float32, -1.0, 1.0)* 32767).astype(np.int16)

            result = vad_client.infer(vad_pcm16.reshape(1, -1))
            if "error" in result:
                print(f"Error: {result['error']}")
                continue

            signal = result["signal"]
            score = result["output"]
            if score is None:
                print("No score returned")
                continue

            if float(score[0]) > threshold:
                count_silence = 0
                if speech_start_time is None:
                    speech_start_time = current_time
                    buffer = audio_float32.copy()
                    print("---Speech started---")
                else:
                    buffer = np.concatenate([buffer, audio_float32])
                
                if buffer.nbytes >= TARGET_BYTES:
                    print(f"Reached target bytes: buffer size={buffer.nbytes} bytes, duration={len(buffer)/sample_rate:.2f}s")
                    speech_queue.put({
                        "audio": buffer.copy(),
                        "start": speech_start_time,
                        "end": current_time,
                    })
                    speech_start_time = current_time
                    buffer = np.empty(0, dtype=np.float32)

                # print(f"Signal: {signal}, Score: {score}")
                # print("Voice detected")
                
            else:

                buffer = np.concatenate([buffer, audio_float32])
                count_silence += len(audio_float32)
                if count_silence < silence_samples:
                    continue

                if len(buffer) >= min_speech_samples:
                    # print(f"Silence detected, clearing buffer, Signal: {signal}, Score: {score}")
                    speech_queue.put({
                        "audio": buffer.copy(),
                        "start": speech_start_time,
                        "end": current_time,
                    })
                if len(buffer) > 0:
                    buffer = np.empty(0, dtype=np.float32)
                speech_start_time = None
                count_silence = 0
            


if __name__ == "__main__":
    try:
        threading.Thread(target=asr_worker_thread, daemon=True).start()
        main()
    except KeyboardInterrupt:
        print("Exiting")
        sys.exit(0)
