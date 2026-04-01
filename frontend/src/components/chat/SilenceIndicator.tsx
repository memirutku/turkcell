"use client";

/**
 * Three animated dots that fade sequentially during the 1.4s silence window.
 * Decorative only -- parent VoiceStatusBanner provides accessible text.
 */
export function SilenceIndicator() {
  return (
    <span className="inline-flex items-center gap-1" aria-hidden="true">
      <span
        className="w-1 h-1 rounded-full bg-green-500 animate-silence-dot-1"
      />
      <span
        className="w-1 h-1 rounded-full bg-green-500 animate-silence-dot-2"
      />
      <span
        className="w-1 h-1 rounded-full bg-green-500 animate-silence-dot-3"
      />
    </span>
  );
}
