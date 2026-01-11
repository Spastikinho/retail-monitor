"""
Security middleware for Retail Monitor.
"""

import logging
from django.conf import settings
from django.http import HttpResponseForbidden
from django.contrib.auth import logout

logger = logging.getLogger(__name__)


class AdminIPRestrictionMiddleware:
    """
    Middleware to restrict access to /admin/ based on IP allowlist.

    Configure ADMIN_IP_ALLOWLIST in settings to restrict access.
    Empty list = allow all (default for development).

    Example:
        ADMIN_IP_ALLOWLIST = ['127.0.0.1', '10.0.0.0/8', '192.168.1.100']
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.allowlist = getattr(settings, 'ADMIN_IP_ALLOWLIST', [])

    def __call__(self, request):
        # Only check /admin/ paths
        if request.path.startswith('/admin/'):
            if not self._is_ip_allowed(request):
                client_ip = self._get_client_ip(request)
                logger.warning(
                    f'Admin access denied for IP: {client_ip} '
                    f'(path: {request.path})'
                )
                return HttpResponseForbidden(
                    'Access denied. Your IP is not in the allowlist.'
                )

        return self.get_response(request)

    def _get_client_ip(self, request):
        """Get the client's real IP address, handling proxies."""
        # Check for X-Forwarded-For header (common in proxies/load balancers)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Take the first IP (client IP before proxies)
            return x_forwarded_for.split(',')[0].strip()

        # Check for X-Real-IP (nginx)
        x_real_ip = request.META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            return x_real_ip.strip()

        # Fall back to REMOTE_ADDR
        return request.META.get('REMOTE_ADDR', '')

    def _is_ip_allowed(self, request):
        """Check if the client IP is in the allowlist."""
        # If allowlist is empty, allow all (for development)
        if not self.allowlist:
            return True

        client_ip = self._get_client_ip(request)

        # Check direct IP match
        if client_ip in self.allowlist:
            return True

        # Check CIDR ranges (basic implementation)
        try:
            import ipaddress
            client_addr = ipaddress.ip_address(client_ip)

            for allowed in self.allowlist:
                try:
                    # Try as network (CIDR notation)
                    if '/' in allowed:
                        network = ipaddress.ip_network(allowed, strict=False)
                        if client_addr in network:
                            return True
                    # Try as single IP
                    elif ipaddress.ip_address(allowed) == client_addr:
                        return True
                except ValueError:
                    # Invalid IP/network in allowlist, skip
                    continue

        except ValueError:
            # Invalid client IP, deny access
            logger.error(f'Invalid client IP address: {client_ip}')
            return False

        return False


class SecureHeadersMiddleware:
    """
    Additional security headers middleware.

    Adds headers not covered by Django's SecurityMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only add headers in production (when DEBUG is False)
        if not settings.DEBUG:
            # Prevent MIME type sniffing
            response['X-Content-Type-Options'] = 'nosniff'

            # Enable XSS filter
            response['X-XSS-Protection'] = '1; mode=block'

            # Referrer policy
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

            # Permissions policy (formerly Feature-Policy)
            response['Permissions-Policy'] = (
                'camera=(), microphone=(), geolocation=(), '
                'payment=(), usb=()'
            )

        return response


class RequestLoggingMiddleware:
    """
    Logs all requests for security auditing.

    Only logs in non-DEBUG mode to avoid noise in development.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Log security-relevant requests in production
        if not settings.DEBUG:
            # Log admin access attempts
            if request.path.startswith('/admin/'):
                logger.info(
                    f'Admin access: {request.method} {request.path} '
                    f'user={request.user} status={response.status_code}'
                )

            # Log authentication attempts
            if request.path in ['/api/v1/auth/login/', '/login/']:
                status = 'success' if response.status_code == 200 else 'failed'
                logger.info(
                    f'Auth attempt ({status}): {request.method} {request.path} '
                    f'status={response.status_code}'
                )

        return response
