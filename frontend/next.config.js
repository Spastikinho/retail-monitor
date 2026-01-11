/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',

  // Environment-aware API URL
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://web-production-9f63.up.railway.app',
  },

  // No rewrites needed - using Next.js API route for proxy
  // See /src/app/api/v1/[...path]/route.ts
};

module.exports = nextConfig;
