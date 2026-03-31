"use client";

import { useEffect, useState } from "react";
import { HealthResponse } from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function StatusBadge({ status }: { status: string }) {
  const isGood = status === "connected" || status === "ready" || status === "healthy";
  const isDegraded = status === "degraded";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium ${
        isGood
          ? "bg-green-100 text-green-800"
          : isDegraded
            ? "bg-yellow-100 text-yellow-800"
            : "bg-red-100 text-red-800"
      }`}
    >
      <span
        className={`h-2 w-2 rounded-full ${
          isGood ? "bg-green-500" : isDegraded ? "bg-yellow-500" : "bg-red-500"
        }`}
      />
      {status}
    </span>
  );
}

function ServiceCard({
  name,
  status,
  details,
}: {
  name: string;
  status: string;
  details?: Record<string, unknown>;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">{name}</h3>
        <StatusBadge status={status} />
      </div>
      {details && (
        <div className="mt-2 space-y-1">
          {Object.entries(details).map(([key, value]) => (
            <p key={key} className="text-xs text-gray-500">
              {key}: {String(value)}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

export default function HealthPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<string>("");

  const checkHealth = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/health`, {
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data: HealthResponse = await response.json();
      setHealth(data);
      setError(null);
      setLastUpdated(new Date().toLocaleTimeString("tr-TR"));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Backend baglantisi kurulamadi"
      );
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      {/* Header */}
      <div className="mb-8 text-center">
        <h1 className="text-4xl font-bold text-turkcell-dark">
          Turkcell{" "}
          <span className="text-turkcell-blue">AI-Gen</span>
        </h1>
        <p className="mt-2 text-lg text-gray-600">
          Dijital Asistan Altyapi Durumu
        </p>
      </div>

      {/* Overall Status */}
      <div className="mb-8">
        {loading ? (
          <div className="flex items-center gap-2 text-gray-500">
            <svg
              className="h-5 w-5 animate-spin"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            Sistem durumu kontrol ediliyor...
          </div>
        ) : error ? (
          <div className="rounded-lg bg-red-50 p-4 text-center">
            <p className="text-red-800 font-medium">Backend Baglantisi Basarisiz</p>
            <p className="text-red-600 text-sm mt-1">{error}</p>
            <button
              onClick={checkHealth}
              className="mt-3 rounded bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700"
            >
              Tekrar Dene
            </button>
          </div>
        ) : health ? (
          <StatusBadge status={health.status} />
        ) : null}
      </div>

      {/* Service Grid */}
      {health && (
        <div className="grid w-full max-w-2xl gap-4 sm:grid-cols-3">
          <ServiceCard
            name="Redis"
            status={health.services.redis.status}
            details={{
              ...(health.services.redis.latency_ms !== undefined && {
                gecikme: `${health.services.redis.latency_ms}ms`,
              }),
            }}
          />
          <ServiceCard
            name="Milvus"
            status={health.services.milvus.status}
            details={{
              ...(health.services.milvus.latency_ms !== undefined && {
                gecikme: `${health.services.milvus.latency_ms}ms`,
              }),
            }}
          />
          <ServiceCard
            name="Mock BSS/OSS"
            status={health.services.mock_bss.status}
            details={{
              musteriler: health.services.mock_bss.customers ?? 0,
              tarifeler: health.services.mock_bss.tariffs ?? 0,
            }}
          />
        </div>
      )}

      {/* Version and refresh info */}
      {health && (
        <div className="mt-6 text-center text-xs text-gray-400">
          <p>API Versiyon: {health.version}</p>
          {lastUpdated && <p>Son guncelleme: {lastUpdated}</p>}
          <p className="mt-1">Her 30 saniyede otomatik guncellenir</p>
        </div>
      )}

      {/* Footer */}
      <footer className="mt-12 text-center text-xs text-gray-400">
        <p>Turkcell AI-Gen Dijital Asistan &copy; 2026</p>
      </footer>
    </main>
  );
}
