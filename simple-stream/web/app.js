const SAMPLE_RATE = 16000;
const SEND_SAMPLES = 512;

const toggleButton = document.querySelector("#toggle");
const clearButton = document.querySelector("#clear");
const clearLogButton = document.querySelector("#clear-log");
const statusText = document.querySelector("#status");
const transcript = document.querySelector("#transcript");
const log = document.querySelector("#log");
const meterBar = document.querySelector("#meter-bar");

let streamState = null;

function socketUrl() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/asr`;
}

function logEvent(label, payload = {}) {
  const line = `[${new Date().toLocaleTimeString()}] ${label} ${JSON.stringify(payload)}`;
  log.textContent = log.textContent === "No events yet." ? line : `${log.textContent}\n${line}`;
  log.scrollTop = log.scrollHeight;
}

function setStatus(value) {
  statusText.textContent = value;
}

function appendTranscript(text) {
  if (!text) return;
  transcript.textContent = transcript.textContent === "No transcript yet." ? text : `${transcript.textContent} ${text}`;
}

function downsampleFloat32(samples, sourceRate, targetRate) {
  if (sourceRate === targetRate) {
    const copy = new Float32Array(samples.length);
    copy.set(samples);
    return copy;
  }

  const ratio = sourceRate / targetRate;
  const outputLength = Math.floor(samples.length / ratio);
  const output = new Float32Array(outputLength);

  for (let index = 0; index < outputLength; index += 1) {
    const start = Math.floor(index * ratio);
    const end = Math.min(samples.length, Math.floor((index + 1) * ratio));
    let total = 0;
    for (let sampleIndex = start; sampleIndex < end; sampleIndex += 1) {
      total += samples[sampleIndex];
    }
    output[index] = total / Math.max(1, end - start);
  }

  return output;
}

function queueSamples(samples, audioContext) {
  if (!streamState || streamState.websocket.readyState !== WebSocket.OPEN) return;

  let peak = 0;
  for (const sample of samples) peak = Math.max(peak, Math.abs(sample));
  meterBar.style.width = `${Math.max(2, Math.min(100, peak * 140))}%`;

  const downsampled = downsampleFloat32(samples, audioContext.sampleRate, SAMPLE_RATE);
  streamState.pending.push(downsampled);
  streamState.pendingSamples += downsampled.length;
  flushSamples(false);
}

function flushSamples(force) {
  if (!streamState || streamState.websocket.readyState !== WebSocket.OPEN) return;
  if (!force && streamState.pendingSamples < SEND_SAMPLES) return;
  if (streamState.pendingSamples <= 0) return;

  const payload = new Float32Array(streamState.pendingSamples);
  let offset = 0;
  for (const chunk of streamState.pending) {
    payload.set(chunk, offset);
    offset += chunk.length;
  }

  let cursor = 0;
  while (payload.length - cursor >= SEND_SAMPLES) {
    const packet = payload.slice(cursor, cursor + SEND_SAMPLES);
    streamState.websocket.send(packet.buffer);
    streamState.chunksSent += 1;
    cursor += SEND_SAMPLES;
  }

  const remaining = payload.slice(cursor);
  if (force && remaining.length > 0) {
    streamState.websocket.send(remaining.buffer);
    streamState.chunksSent += 1;
    streamState.pending = [];
    streamState.pendingSamples = 0;
  } else {
    streamState.pending = remaining.length ? [remaining] : [];
    streamState.pendingSamples = remaining.length;
  }
}

async function startStreaming() {
  setStatus("Starting microphone...");

  const mediaStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  });

  const audioContext = new AudioContext();
  await audioContext.audioWorklet.addModule("audio-worklet.js");

  const source = audioContext.createMediaStreamSource(mediaStream);
  const processor = new AudioWorkletNode(audioContext, "microphone-capture");
  source.connect(processor);

  const websocket = new WebSocket(socketUrl());
  websocket.binaryType = "arraybuffer";

  streamState = {
    audioContext,
    mediaStream,
    processor,
    source,
    websocket,
    pending: [],
    pendingSamples: 0,
    chunksSent: 0,
  };

  websocket.addEventListener("open", () => {
    processor.port.onmessage = (event) => queueSamples(event.data, audioContext);
    toggleButton.textContent = "Stop";
    setStatus("Listening");
    logEvent("websocket_open", { url: socketUrl(), browserSampleRate: audioContext.sampleRate });
  });

  websocket.addEventListener("message", (event) => {
    const payload = JSON.parse(event.data);
    logEvent(payload.type, payload);
    if (payload.type === "text") appendTranscript(payload.text || "");
    if (payload.type === "error") setStatus(payload.message || "Error");
    if (payload.type === "speech_start") setStatus("Speech detected");
    if (payload.type === "speech_end") setStatus("Transcribing...");
    if (payload.type === "started") setStatus("Listening");
    if (payload.type === "stopped") setStatus("Stopped");
  });

  websocket.addEventListener("error", () => {
    setStatus("WebSocket error");
    logEvent("websocket_error");
  });

  websocket.addEventListener("close", (event) => {
    logEvent("websocket_close", { code: event.code, reason: event.reason });
    stopStreaming(false);
  });
}

function stopStreaming(sendStop = true) {
  if (!streamState) return;

  const current = streamState;

  processorDisconnect(current);
  current.mediaStream.getTracks().forEach((track) => track.stop());
  current.audioContext.close();

  if (current.websocket.readyState === WebSocket.OPEN) {
    flushSamples(true);
    if (sendStop) current.websocket.send("stop");
  }

  streamState = null;
  toggleButton.textContent = "Start";
  meterBar.style.width = "0";
  setStatus("Stopped");
}

function processorDisconnect(current) {
  current.processor.port.onmessage = null;
  current.processor.disconnect();
  current.source.disconnect();
}

toggleButton.addEventListener("click", async () => {
  if (streamState) {
    stopStreaming(true);
    return;
  }

  try {
    await startStreaming();
  } catch (error) {
    setStatus(error.message || "Could not start");
    logEvent("start_error", { message: error.message || String(error) });
    stopStreaming(false);
  }
});

clearButton.addEventListener("click", () => {
  transcript.textContent = "No transcript yet.";
});

clearLogButton.addEventListener("click", () => {
  log.textContent = "No events yet.";
});
