/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const backendOrigin = process.env.BACKEND_ORIGIN;
    // Local dev doesn't need the proxy, so it skips this if the env var is missing
    if (!backendOrigin) {
      return [];
    }
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendOrigin}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig; // Use 'export default nextConfig;' if using .mjs