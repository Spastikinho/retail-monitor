/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',

  // Disable trailing slash normalization to prevent redirect loops
  skipTrailingSlashRedirect: true,

  // Environment-aware API URL
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://web-production-9f63.up.railway.app',
  },

  // Rewrites - use beforeFiles to ensure they run before Next.js routing
  async rewrites() {
    const railwayUrl = process.env.NEXT_PUBLIC_API_URL || 'https://web-production-9f63.up.railway.app';

    return {
      beforeFiles: [
        // Proxy all /api/v1/* requests to Railway backend
        {
          source: '/api/v1/:path*',
          destination: `${railwayUrl}/api/v1/:path*`,
        },
      ],
      afterFiles: [],
      fallback: [],
    };
  },
};

module.exports = nextConfig;
