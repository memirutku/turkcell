/**
 * PCM16 audio utilities for Gemini Live API.
 *
 * Capture: raw PCM16 16kHz mono (mic → Gemini input)
 * Playback: raw PCM16 24kHz mono (Gemini output → speaker)
 */

const CAPTURE_SAMPLE_RATE = 16000;
const OUTPUT_SAMPLE_RATE = 24000;

/**
 * Set up microphone capture that outputs PCM16 chunks via callback.
 *
 * Uses an AudioWorklet processor to convert Float32 mic input to Int16 PCM
 * at 16kHz. Each chunk is ~100ms of audio (1600 samples = 3200 bytes).
 *
 * @returns Cleanup function that stops capture and releases resources.
 */
export async function startPCMCapture(
  onChunk: (pcmData: ArrayBuffer) => void,
): Promise<() => void> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      sampleRate: CAPTURE_SAMPLE_RATE,
    },
  });

  const audioContext = new AudioContext({ sampleRate: CAPTURE_SAMPLE_RATE });

  await audioContext.audioWorklet.addModule("/pcm-capture-processor.js");

  const source = audioContext.createMediaStreamSource(stream);
  const workletNode = new AudioWorkletNode(audioContext, "pcm-capture-processor");

  workletNode.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
    onChunk(event.data);
  };

  source.connect(workletNode);
  // Don't connect to destination — we don't want to play back mic audio

  return () => {
    workletNode.port.onmessage = null;
    source.disconnect();
    workletNode.disconnect();
    audioContext.close();
    stream.getTracks().forEach((track) => track.stop());
  };
}

/**
 * PCM16 audio player that queues and plays raw PCM chunks seamlessly.
 *
 * Uses AudioContext buffer scheduling to play PCM16 chunks in order
 * with no gaps. Tracks playback state and calls onPlaybackEnd when
 * all queued audio has finished playing.
 */
export class PCMPlayer {
  private _audioContext: AudioContext;
  private _nextStartTime: number = 0;
  private _isPlaying: boolean = false;
  private _scheduledCount: number = 0;
  private _finishedCount: number = 0;
  private _onPlaybackEnd: (() => void) | null;

  constructor(onPlaybackEnd?: () => void) {
    this._audioContext = new AudioContext({ sampleRate: OUTPUT_SAMPLE_RATE });
    this._onPlaybackEnd = onPlaybackEnd ?? null;
  }

  get isPlaying(): boolean {
    return this._isPlaying;
  }

  /**
   * Enqueue a raw PCM16 chunk for playback.
   * Chunks are scheduled back-to-back with no gaps.
   */
  enqueue(pcmData: ArrayBuffer): void {
    const int16 = new Int16Array(pcmData);
    const float32 = new Float32Array(int16.length);

    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / (int16[i] < 0 ? 0x8000 : 0x7fff);
    }

    const buffer = this._audioContext.createBuffer(1, float32.length, OUTPUT_SAMPLE_RATE);
    buffer.copyToChannel(float32, 0);

    const source = this._audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(this._audioContext.destination);

    const now = this._audioContext.currentTime;
    const startTime = Math.max(now, this._nextStartTime);
    this._nextStartTime = startTime + buffer.duration;

    this._scheduledCount++;
    this._isPlaying = true;

    source.onended = () => {
      this._finishedCount++;
      if (this._finishedCount >= this._scheduledCount) {
        this._isPlaying = false;
        this._onPlaybackEnd?.();
      }
    };

    source.start(startTime);
  }

  /**
   * Stop all playback and reset state.
   */
  stop(): void {
    this._audioContext.close();
    this._audioContext = new AudioContext({ sampleRate: OUTPUT_SAMPLE_RATE });
    this._nextStartTime = 0;
    this._scheduledCount = 0;
    this._finishedCount = 0;
    this._isPlaying = false;
  }

  /**
   * Clean up audio context.
   */
  destroy(): void {
    this._audioContext.close();
  }
}
