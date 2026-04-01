/**
 * Voice Activity Detection configuration constants.
 * Single source of truth for all VAD tuning parameters.
 * Based on @ricky0123/vad-react with Silero VAD v5 model.
 */
export const VAD_CONFIG = {
  /** Probability threshold above which a frame is considered speech */
  positiveSpeechThreshold: 0.3,
  /** Probability threshold below which a frame is considered silence */
  negativeSpeechThreshold: 0.25,
  /** Milliseconds of silence before speech-end fires (1.4s default) */
  redemptionMs: 1400,
  /** Minimum speech duration in ms to avoid misfires (coughs, noise) */
  minSpeechMs: 400,
  /** Pre-speech padding in ms (audio before speech start is included) */
  preSpeechPadMs: 800,
  /** Silero VAD model version */
  model: "v5" as const,
  /** Path prefix for VAD assets (worklet, ONNX model) */
  baseAssetPath: "/_next/static/chunks/",
  /** Path prefix for ONNX Runtime WASM files */
  onnxWASMBasePath: "/_next/static/chunks/",
} as const;

/** Delay in ms before resuming VAD after TTS playback ends */
export const POST_PLAYBACK_DELAY_MS = 300;
