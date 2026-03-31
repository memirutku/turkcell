export function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-8">
      <div className="h-16 w-16 rounded-full bg-turkcell-yellow flex items-center justify-center text-2xl font-bold text-turkcell-dark mb-6">
        T
      </div>
      <h2 className="text-xl font-semibold text-turkcell-dark mb-2">
        Merhaba! Size nasil yardimci olabilirim?
      </h2>
      <p className="text-sm text-gray-500 max-w-md">
        Fatura, tarife, paket ve teknik destek konularinda sorularinizi yazabilirsiniz.
      </p>
    </div>
  );
}
