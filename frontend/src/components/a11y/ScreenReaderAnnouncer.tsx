"use client";
import { useChatStore } from "@/stores/chatStore";

/**
 * Centralized screen reader announcer.
 * Renders a single persistent aria-live="assertive" region
 * driven by the chatStore's srAnnouncement field.
 * Mounted once in layout, never unmounted.
 */
export function ScreenReaderAnnouncer() {
  const srAnnouncement = useChatStore((s) => s.srAnnouncement);

  return (
    <div
      className="sr-only"
      role="status"
      aria-live="assertive"
      aria-atomic="true"
    >
      {srAnnouncement}
    </div>
  );
}
