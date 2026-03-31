"use client";
import { LiveAudioVisualizer } from "react-audio-visualize";

interface AudioWaveformProps {
  mediaRecorder: MediaRecorder | null;
}

export function AudioWaveform({ mediaRecorder }: AudioWaveformProps) {
  if (!mediaRecorder) {
    return <div className="flex-1 flex items-center min-w-[120px]" aria-hidden="true" />;
  }

  return (
    <div className="flex-1 flex items-center min-w-[120px]" aria-hidden="true">
      <LiveAudioVisualizer
        mediaRecorder={mediaRecorder}
        width={300}
        height={40}
        barWidth={3}
        gap={2}
        barColor="#0066CC"
        smoothingTimeConstant={0.8}
      />
    </div>
  );
}
