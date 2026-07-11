/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      // Proxy /api/chat/* to FastAPI during local dev. In production the
      // FastAPI brain sits behind the same URL via a single Fly.io origin.
      {
        source: "/api/chat/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/chat/:path*`,
      },
    ];
  },
};

export default nextConfig;