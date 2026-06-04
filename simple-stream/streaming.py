import argparse
import asyncio
from dataclasses import dataclass
import sys
from pathlib import Path
import json
from vad_client import vad_client
from sherpa_offline_client import sherpa_offline_client
from pyrnnoise import RNNoise

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

def asr_worker_thread():
    asyncio.run(asr_worker())

async def asr_worker():
    print("ASR worker started")
    await sherpa_offline_client.connect()

    while True:
        item = speech_queue.get()

        audio = item.get("audio")
        start = item.get("start")
        end = item.get("end")

        print(
            f"ASR "
            f"duration={end - start:.2f}s"
            if start is not None and end is not None
            else f"start={start:.2f}s"
            f",samples={len(audio)}.",
            end=" "
        )

        text = await sherpa_offline_client.transcribe(audio)
        json_text = json.loads(text)
        print(f"Text:{json_text.get('text', '')}", end="\n")
        # if end:
        #     print("\n")

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

    sample_rate = 16000
    sample_per_read = int(0.032 * sample_rate)  # read XX second of audio
    buffer = np.empty(0, dtype=np.float32)
    threshold = 0.4 # VAD threshold probability
    silence_samples = int(0.25 * sample_rate) # silence duration to consider end of speech
    count_silence = 0
    target_seconds = 46
    min_speech_seconds = 0.3
    pre_roll_seconds = 0.3
    pre_roll_buffer = np.empty(0, dtype=np.float32)

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
                if speech_start_time is None:
                    speech_start_time = current_time - pre_roll_seconds
                    buffer = np.concatenate([pre_roll_buffer, audio_float32])
                    pre_roll_buffer = np.empty(0, dtype=np.float32)
                    print("---Speech started---")
                else:
                    buffer = np.concatenate([buffer, audio_float32])
                
                if len(buffer) >= sample_rate * target_seconds:
                    print(f"Reached {target_seconds} seconds")
                    speech_queue.put({
                        "audio": buffer.copy(),
                        "start": speech_start_time,
                    })
                    pre_roll_buffer = buffer[-int(pre_roll_seconds * sample_rate):]
                    buffer = pre_roll_buffer.copy()
                    speech_start_time = current_time - pre_roll_seconds

                # print(f"Signal: {signal}, Score: {score}")
                # print("Voice detected")
                
            else:
                buffer = np.concatenate([buffer, audio_float32])
                count_silence += len(audio_float32)
                if count_silence < silence_samples:
                    continue

                count_silence = 0

                if len(buffer) >= sample_rate * min_speech_seconds:
                    # print(f"Silence detected, clearing buffer, Signal: {signal}, Score: {score}")
                    speech_queue.put({
                        "audio": buffer.copy(),
                        "start": speech_start_time,
                        "end": current_time,
                    })
                if len(buffer) > 0:
                    buffer = np.empty(0, dtype=np.float32)
                speech_start_time = None

                pre_roll_buffer = np.concatenate([pre_roll_buffer, audio_float32])
                pre_roll_samples = int(pre_roll_seconds * sample_rate)
                if len(pre_roll_buffer) > pre_roll_samples:
                    pre_roll_buffer = pre_roll_buffer[-pre_roll_samples:]

            


if __name__ == "__main__":
    try:
        threading.Thread(target=asr_worker_thread, daemon=True).start()
        main()
    except KeyboardInterrupt:
        print("Exiting")
        sys.exit(0)