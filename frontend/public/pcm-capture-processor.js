/**
 * AudioWorklet processor that captures microphone audio as PCM16 chunks.
 *
 * Receives Float32 samples from the Web Audio API, converts to Int16 PCM,
 * and posts ArrayBuffer chunks to the main thread at regular intervals.
 *
 * Output format: 16kHz, mono, 16-bit signed little-endian PCM
 * (matches Gemini Live API's expected input format)
 */
class PCMCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = [];
    // Send chunks every ~100ms (1600 samples at 16kHz)
    this._chunkSize = 1600;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;

    const channelData = input[0]; // mono channel

    for (let i = 0; i < channelData.length; i++) {
      this._buffer.push(channelData[i]);
    }

    while (this._buffer.length >= this._chunkSize) {
      const chunk = this._buffer.splice(0, this._chunkSize);
      const int16 = new Int16Array(chunk.length);
      for (let i = 0; i < chunk.length; i++) {
        const s = Math.max(-1, Math.min(1, chunk[i]));
        int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }
      this.port.postMessage(int16.buffer, [int16.buffer]);
    }

    return true;
  }
}

registerProcessor("pcm-capture-processor", PCMCaptureProcessor);
