from .models import PageAccessLog, WeeklyTrafficSummary
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
from datetime import date
import logging
import os

logger = logging.getLogger(__name__)


class TrafficLoggerMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        path = request.path
        if path.startswith('/static/') or path.startswith('/admin/') or path == '/favicon.ico':
            return response  # Skip static and admin routes

        status = response.status_code
        week_start = WeeklyTrafficSummary.get_week_start()

        try:
            # Save detailed log
            PageAccessLog.objects.create(
                path=path,
                method=request.method,
                status_code=status,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                referrer=request.META.get('HTTP_REFERER', '')
            )

            # Update weekly summary
            summary, _ = WeeklyTrafficSummary.objects.get_or_create(week_start=week_start)
            summary.total_requests += 1
            if status == 200:
                summary.total_200s += 1
            elif status == 404:
                summary.total_404s += 1
            else:
                summary.total_other += 1
            summary.save()

        except Exception as e:
            logger.error(f"Failed to log traffic data: {e}")

        return response

class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Adds consistent, production-safe security headers without blocking common external resources.
    """
    def process_response(self, request, response):
        # Basic protections
        response['X-XSS-Protection'] = '1; mode=block'
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Allow external images, fonts, and styles from trusted sources
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; "
            "style-src 'self' 'unsafe-inline' https:; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self' https:; "
            "media-src 'self' https:; "
            "object-src 'none'; "
            "frame-ancestors 'none';"
        )

        return response

class SecurityLoggingMiddleware(MiddlewareMixin):
    """
    Logs security-related events
    """
    def process_request(self, request):
        # Log suspicious patterns
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Log potential bot activity
        suspicious_agents = ['bot', 'crawler', 'spider', 'scraper']
        if any(agent in user_agent.lower() for agent in suspicious_agents):
            logger.info(f"Bot detected: {user_agent} accessing {request.path}")

        # Log unusual file access attempts
        if '/worlds/' in request.path and not request.path.endswith('.zip'):
            logger.warning(f"Unusual world access attempt: {request.path} from {request.META.get('REMOTE_ADDR')}")

    def process_response(self, request, response):
        # Log failed authentication attempts
        if response.status_code == 403:
            logger.warning(f"403 Forbidden: {request.path} from {request.META.get('REMOTE_ADDR')}")

        # Log server errors
        if response.status_code >= 500:
            logger.error(f"Server error {response.status_code}: {request.path}")

        return response
