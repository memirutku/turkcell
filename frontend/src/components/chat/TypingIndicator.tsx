export function TypingIndicator() {
  return (
    <div className="flex gap-3 items-start">
      <div className="h-8 w-8 rounded-full bg-turkcell-yellow flex items-center justify-center text-sm font-bold text-turkcell-dark shrink-0">
        T
      </div>
      <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-2">
        <div className="flex gap-1" aria-label="Asistan yaziyor..." role="status">
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
        </div>
      </div>
    </div>
  );
}
