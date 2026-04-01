import CopyPlugin from "copy-webpack-plugin";

/** @type {import('next').NextConfig} */
const nextConfig = {
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
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.plugins.push(
        new CopyPlugin({
          patterns: [
            {
              from: "node_modules/@ricky0123/vad-web/dist/vad.worklet.bundle.min.js",
              to: "static/chunks/[name][ext]",
            },
            {
              from: "node_modules/@ricky0123/vad-web/dist/*.onnx",
              to: "static/chunks/[name][ext]",
            },
            {
              from: "node_modules/onnxruntime-web/dist/*.wasm",
              to: "static/chunks/[name][ext]",
            },
            {
              from: "node_modules/onnxruntime-web/dist/*.mjs",
              to: "static/chunks/[name][ext]",
            },
          ],
        })
      );
    }
    return config;
  },
};

export default nextConfig;
