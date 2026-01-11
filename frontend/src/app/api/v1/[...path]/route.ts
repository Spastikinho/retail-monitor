/**
 * Next.js API Route Proxy - forwards all /api/v1/* requests to Railway backend
 *
 * Architecture:
 * - Frontend calls same-origin /api/v1/* paths
 * - This route handler proxies requests to the Railway Django backend
 * - No CORS issues since requests are same-origin from browser perspective
 *
 * Trailing Slash Handling:
 * - Django requires trailing slashes (APPEND_SLASH = True)
 * - We normalize all paths to include trailing slash before forwarding
 * - We follow Django's 301 redirects internally to prevent redirect loops
 */

import { NextRequest, NextResponse } from 'next/server';

// Backend URL from environment or default to Railway production
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'https://web-production-9f63.up.railway.app';

// Validate backend URL is configured
function validateBackendUrl(): { valid: boolean; url: string; error?: string } {
  if (!BACKEND_URL) {
    return { valid: false, url: '', error: 'NEXT_PUBLIC_API_URL is not configured' };
  }
  try {
    new URL(BACKEND_URL);
    return { valid: true, url: BACKEND_URL };
  } catch {
    return { valid: false, url: BACKEND_URL, error: 'NEXT_PUBLIC_API_URL is not a valid URL' };
  }
}

async function proxyRequest(request: NextRequest, params: { path: string[] }) {
  const validation = validateBackendUrl();
  if (!validation.valid) {
    return NextResponse.json(
      {
        error: 'Backend configuration error',
        details: validation.error,
        configured_url: validation.url || '(not set)',
      },
      { status: 503 }
    );
  }

  const path = params.path.join('/');
  const url = new URL(request.url);

  // IMPORTANT: Always add trailing slash for Django compatibility
  // Django's APPEND_SLASH will 301 redirect without it, causing loops
  const normalizedPath = path.endsWith('/') ? path : `${path}/`;
  const targetUrl = `${BACKEND_URL}/api/v1/${normalizedPath}${url.search}`;

  // Forward headers (excluding hop-by-hop and Vercel-specific)
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    const lowerKey = key.toLowerCase();
    if (
      lowerKey !== 'host' &&
      lowerKey !== 'connection' &&
      lowerKey !== 'keep-alive' &&
      lowerKey !== 'transfer-encoding' &&
      !lowerKey.startsWith('x-vercel') &&
      !lowerKey.startsWith('x-forwarded')
    ) {
      headers.set(key, value);
    }
  });

  // Add forwarding headers for Django
  headers.set('X-Forwarded-Host', url.host);
  headers.set('X-Forwarded-Proto', url.protocol.replace(':', ''));
  headers.set('X-Forwarded-For', request.headers.get('x-forwarded-for') || request.ip || '');

  try {
    // Make the proxied request - follow redirects internally
    const response = await fetch(targetUrl, {
      method: request.method,
      headers,
      body: request.method !== 'GET' && request.method !== 'HEAD'
        ? await request.text()
        : undefined,
      // Follow redirects internally - don't pass them to client
      redirect: 'follow',
    });

    // Build response headers
    const responseHeaders = new Headers();
    response.headers.forEach((value, key) => {
      const lowerKey = key.toLowerCase();
      // Skip hop-by-hop headers and CORS headers (we handle CORS ourselves)
      if (
        lowerKey !== 'transfer-encoding' &&
        lowerKey !== 'connection' &&
        lowerKey !== 'keep-alive' &&
        !lowerKey.startsWith('access-control-')
      ) {
        responseHeaders.set(key, value);
      }
    });

    // Return proxied response
    return new NextResponse(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      {
        error: 'Backend connection failed',
        details: error instanceof Error ? error.message : 'Unknown error',
        target_url: targetUrl,
        backend_configured: BACKEND_URL,
      },
      { status: 502 }
    );
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(request, await params);
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(request, await params);
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(request, await params);
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(request, await params);
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(request, await params);
}

// Handle OPTIONS for CORS preflight (though not needed with same-origin proxy)
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-CSRFToken',
      'Access-Control-Max-Age': '86400',
    },
  });
}
