/**
 * Browser audio capability detection utilities for voice features.
 */

/** Check if the browser supports MediaRecorder and getUserMedia */
export function checkMicrophoneSupport(): boolean {
  return (
    typeof navigator !== "undefined" &&
    !!navigator.mediaDevices &&
    typeof navigator.mediaDevices.getUserMedia === "function" &&
    typeof MediaRecorder !== "undefined"
  );
}

/** Check if the page is served over a secure context (HTTPS or localhost) */
export function checkSecureContext(): boolean {
  if (typeof window === "undefined") return false;
  return window.isSecureContext;
}

/** Get the best supported audio MIME type for MediaRecorder */
export function getAudioMimeType(): string {
  const types = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
  ];
  for (const type of types) {
    if (MediaRecorder.isTypeSupported(type)) return type;
  }
  return "audio/webm"; // fallback
}
