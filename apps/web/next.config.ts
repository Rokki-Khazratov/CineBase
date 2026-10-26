import type { NextConfig } from "next";

const apiUrl = (process.env.CINEBASE_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  // With NEXT_PUBLIC_CATALOG_SOURCE=api the browser calls /api/v1 on this origin and Next.js forwards it to
  // the CineBase API, so the API needs no CORS setup and its address stays server-side.
  async rewrites() {
    if (process.env.NEXT_PUBLIC_CATALOG_SOURCE !== "api") return [];
    return [{ source: "/api/v1/:path*", destination: `${apiUrl}/api/v1/:path*` }];
  },
};

export default nextConfig;
