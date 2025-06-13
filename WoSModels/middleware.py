from datetime import date
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
from .models import PageAccessLog, WeeklyTrafficSummary
import logging

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
    Adds security headers to all responses
    """
    def process_response(self, request, response):
        # XSS Protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Content Type Options
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Frame Options (prevent clickjacking)
        response['X-Frame-Options'] = 'DENY'
        
        # Content Security Policy
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'"
        )
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
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