export function TypingIndicator() {
  return (
    <div className="flex gap-3 items-start" role="status" aria-live="polite" aria-label="Asistan yaziyor">
      <div
        className="h-8 w-8 rounded-full bg-umay-yellow flex items-center justify-center text-sm font-bold text-umay-dark shrink-0"
        aria-hidden="true"
      >
        U
      </div>
      <div className="bg-card border border-border rounded-2xl rounded-tl-sm px-4 py-2">
        <div className="flex gap-1" aria-hidden="true">
          <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
          <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
          <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
        </div>
        <span className="sr-only">Asistan yanit hazirlaniyor...</span>
      </div>
    </div>
  );
}
