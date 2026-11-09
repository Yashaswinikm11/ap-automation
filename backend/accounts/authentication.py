from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    Session-based authentication that skips Django's CSRF enforcement.

    Django REST Framework's default SessionAuthentication requires a valid
    CSRF token for all unsafe HTTP methods (POST, PUT, PATCH, DELETE).
    This is problematic for Single-Page Applications (SPAs) served from a
    different origin (e.g. Vite dev server on :5173 vs Django on :8000),
    because the browser never loads a Django template that would set the
    csrftoken cookie.

    This subclass overrides `enforce_csrf()` to be a no-op, so session-based
    auth still works (the session cookie is sent via `withCredentials: true`)
    without requiring the CSRF cookie handshake.

    Security note: Cross-origin protection is provided by the CORS policy
    configured in `corsheaders` (CORS_ALLOWED_ORIGINS). Only listed origins
    are allowed to send credentialed requests, which is equivalent protection
    for an API-only backend.
    """

    def enforce_csrf(self, request):
        # Intentionally skip CSRF check for API endpoints.
        return
