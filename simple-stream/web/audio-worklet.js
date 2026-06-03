class MicrophoneCaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;

    const samples = input[0];
    const copy = new Float32Array(samples.length);
    copy.set(samples);
    this.port.postMessage(copy, [copy.buffer]);
    return true;
  }
}

registerProcessor("microphone-capture", MicrophoneCaptureProcessor);
