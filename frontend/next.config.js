/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',

  // Environment-aware API URL
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://web-production-9f63.up.railway.app',
  },

  // Rewrites for local development - production uses vercel.json rewrites
  async rewrites() {
    if (process.env.NODE_ENV === 'development') {
      return [
        {
          source: '/api/:path*',
          destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`,
        },
      ];
    }
    // Production rewrites handled by vercel.json
    return [];
  },
};

module.exports = nextConfig;
