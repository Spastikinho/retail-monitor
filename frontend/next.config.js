/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',

  // CRITICAL: Match Django's APPEND_SLASH behavior to prevent redirect loops
  // Without this, Vercel 308s to remove slash, Django 301s to add it back = infinite loop
  trailingSlash: true,

  // Environment-aware API URL - used by the proxy route handler
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://web-production-9f63.up.railway.app',
  },

  // Skip trailing slash redirect for API routes (handled by route handler)
  skipTrailingSlashRedirect: true,
};

module.exports = nextConfig;
