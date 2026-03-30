import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Proxy API requests to backend in development
  // In production, Traefik handles routing
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
