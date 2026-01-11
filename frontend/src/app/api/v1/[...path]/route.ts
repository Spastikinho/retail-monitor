/**
 * Next.js API Route Proxy - forwards all /api/v1/* requests to Railway backend
 *
 * This solves the Vercel rewrite issues by using Next.js native route handlers
 * which have full control over request/response handling.
 */

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'https://web-production-9f63.up.railway.app';

async function proxyRequest(request: NextRequest, params: { path: string[] }) {
  const path = params.path.join('/');
  const url = new URL(request.url);

  // Build target URL
  const targetUrl = `${BACKEND_URL}/api/v1/${path}${url.search}`;

  // Forward headers (excluding host and some Next.js specific ones)
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    const lowerKey = key.toLowerCase();
    if (
      lowerKey !== 'host' &&
      lowerKey !== 'connection' &&
      !lowerKey.startsWith('x-vercel') &&
      !lowerKey.startsWith('x-forwarded')
    ) {
      headers.set(key, value);
    }
  });

  // Add forwarding headers
  headers.set('X-Forwarded-Host', url.host);
  headers.set('X-Forwarded-Proto', url.protocol.replace(':', ''));

  try {
    // Make the proxied request
    const response = await fetch(targetUrl, {
      method: request.method,
      headers,
      body: request.method !== 'GET' && request.method !== 'HEAD' ? await request.text() : undefined,
      // Don't follow redirects - let client handle them
      redirect: 'manual',
    });

    // Build response headers
    const responseHeaders = new Headers();
    response.headers.forEach((value, key) => {
      const lowerKey = key.toLowerCase();
      // Skip hop-by-hop headers
      if (
        lowerKey !== 'transfer-encoding' &&
        lowerKey !== 'connection' &&
        lowerKey !== 'keep-alive'
      ) {
        responseHeaders.set(key, value);
      }
    });

    // Handle redirects
    if (response.status >= 300 && response.status < 400) {
      const location = response.headers.get('location');
      if (location) {
        // Rewrite location header to point back to our proxy
        const locationUrl = new URL(location, targetUrl);
        if (locationUrl.origin === new URL(BACKEND_URL).origin) {
          const proxyLocation = locationUrl.pathname.replace('/api/v1/', '/api/v1/') + locationUrl.search;
          responseHeaders.set('location', proxyLocation);
        }
      }
    }

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
      },
      { status: 502 }
    );
  }
}

export async function GET(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, await params);
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, await params);
}

export async function PUT(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, await params);
}

export async function DELETE(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, await params);
}

export async function PATCH(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, await params);
}

// Handle OPTIONS for CORS preflight
export async function OPTIONS(request: NextRequest) {
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
