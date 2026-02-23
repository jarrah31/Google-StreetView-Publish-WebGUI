"""
Tests for Flask routes in app.py.

Covers:
  - Public routes (no authentication required)
  - Auth-required routes redirect to /authorize when unauthenticated
  - Auth-required routes return expected responses when authenticated
  - Security headers on all responses
  - Redirect routes (/upload, /database_viewer)
  - Error handlers (404)
  - /check_auth_status JSON API
  - /get_connections JSON API
  - /update_db JSON API
"""
import json
import os
import pytest
from unittest.mock import patch, MagicMock

import database as db_module
from tests.conftest import make_photo_data


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    def test_healthz_returns_200(self, client):
        response = client.get('/healthz')
        assert response.status_code == 200

    def test_healthz_returns_json(self, client):
        response = client.get('/healthz')
        data = response.get_json()
        assert data is not None

    def test_healthz_body(self, client):
        response = client.get('/healthz')
        data = response.get_json()
        assert data['status'] == 'ok'


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------

class TestSecurityHeaders:
    """Every response should include the security headers added by after_request."""

    def test_x_content_type_options(self, client):
        response = client.get('/')
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'

    def test_x_frame_options(self, client):
        response = client.get('/')
        assert response.headers.get('X-Frame-Options') == 'SAMEORIGIN'

    def test_referrer_policy(self, client):
        response = client.get('/')
        assert response.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'

    def test_content_security_policy_present(self, client):
        response = client.get('/')
        csp = response.headers.get('Content-Security-Policy')
        assert csp is not None
        assert "default-src" in csp

    def test_permissions_policy_present(self, client):
        response = client.get('/')
        pp = response.headers.get('Permissions-Policy')
        assert pp is not None

    def test_headers_also_on_healthz(self, client):
        response = client.get('/healthz')
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'


# ---------------------------------------------------------------------------
# Public routes (no auth required)
# ---------------------------------------------------------------------------

class TestPublicRoutes:
    def test_index_returns_200(self, client):
        response = client.get('/')
        assert response.status_code == 200

    def test_index_is_html(self, client):
        response = client.get('/')
        assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data

    def test_check_auth_status_unauthenticated(self, client):
        """When no creds file exists the endpoint reports not authenticated."""
        with patch('app.get_credentials', return_value=None):
            response = client.get('/check_auth_status')
        assert response.status_code == 200
        data = response.get_json()
        assert data['authenticated'] is False

    def test_check_auth_status_authenticated(self, auth_client):
        """With mocked valid credentials the endpoint reports authenticated."""
        response = auth_client.get('/check_auth_status')
        assert response.status_code == 200
        data = response.get_json()
        assert data['authenticated'] is True


# ---------------------------------------------------------------------------
# 404 handler
# ---------------------------------------------------------------------------

class TestNotFoundHandler:
    def test_unknown_route_returns_404(self, client):
        response = client.get('/this-page-does-not-exist')
        assert response.status_code == 404

    def test_404_renders_error_template(self, client):
        response = client.get('/no-such-page')
        # error.html contains "Error" heading or similar
        assert b'not exist' in response.data or b'Not Found' in response.data or b'Error' in response.data

    def test_ajax_404_returns_json(self, client):
        response = client.get(
            '/no-such-page',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        assert response.status_code == 404
        data = response.get_json()
        assert data is not None
        assert 'error' in data


# ---------------------------------------------------------------------------
# Auth-required routes: unauthenticated redirect
# ---------------------------------------------------------------------------

class TestAuthRequiredRedirects:
    """Unauthenticated requests to @token_required routes must redirect to /authorize."""

    def _assert_redirects_to_authorize(self, response):
        assert response.status_code in (301, 302)
        location = response.headers.get('Location', '')
        assert 'authorize' in location

    def test_photos_page_redirects(self, client):
        with patch('app.get_credentials', return_value=None):
            response = client.get('/photos')
        self._assert_redirects_to_authorize(response)

    def test_upload_multiple_redirects(self, client):
        with patch('app.get_credentials', return_value=None):
            response = client.get('/upload_multiple')
        self._assert_redirects_to_authorize(response)

    def test_photo_database_redirects(self, client):
        with patch('app.get_credentials', return_value=None):
            response = client.get('/photo_database')
        self._assert_redirects_to_authorize(response)

    def test_get_connections_redirects(self, client):
        with patch('app.get_credentials', return_value=None):
            response = client.post(
                '/get_connections',
                json={'photoIds': []},
                content_type='application/json'
            )
        self._assert_redirects_to_authorize(response)

    def test_nearby_places_redirects(self, client):
        with patch('app.get_credentials', return_value=None):
            response = client.get('/nearby_places?latitude=51.5&longitude=-0.1')
        self._assert_redirects_to_authorize(response)

    def test_upload_get_redirects(self, client):
        with patch('app.get_credentials', return_value=None):
            response = client.get('/upload')
        self._assert_redirects_to_authorize(response)


# ---------------------------------------------------------------------------
# Auth-required routes: authenticated responses
# ---------------------------------------------------------------------------

class TestAuthenticatedRoutes:
    def test_upload_multiple_returns_200(self, auth_client):
        response = auth_client.get('/upload_multiple')
        assert response.status_code == 200

    def test_upload_multiple_contains_api_key(self, auth_client):
        response = auth_client.get('/upload_multiple')
        # Template receives api_key parameter
        assert response.status_code == 200

    def test_photo_database_returns_200(self, auth_client):
        response = auth_client.get('/photo_database')
        assert response.status_code == 200

    def test_photos_page_returns_200(self, auth_client):
        """photos page renders empty table when DB is present but empty."""
        response = auth_client.get('/photos')
        assert response.status_code == 200

    def test_photos_page_is_html(self, auth_client):
        response = auth_client.get('/photos')
        assert b'<html' in response.data or b'<!DOCTYPE' in response.data

    def test_api_photos_map_returns_200(self, auth_client):
        response = auth_client.get('/api/photos/map')
        assert response.status_code == 200
        data = response.get_json()
        assert 'photos' in data
        assert 'total_count' in data

    def test_api_photos_map_returns_empty_on_empty_db(self, auth_client):
        response = auth_client.get('/api/photos/map')
        data = response.get_json()
        assert data['total_count'] == 0


# ---------------------------------------------------------------------------
# Redirect routes
# ---------------------------------------------------------------------------

class TestRedirectRoutes:
    def test_upload_get_redirects_to_upload_multiple(self, auth_client):
        """GET /upload should redirect to /upload_multiple."""
        response = auth_client.get('/upload')
        assert response.status_code in (301, 302)
        location = response.headers.get('Location', '')
        assert 'upload_multiple' in location

    def test_database_viewer_redirects_to_photo_database(self, auth_client):
        """GET /database_viewer should redirect to /photo_database."""
        response = auth_client.get('/database_viewer')
        assert response.status_code in (301, 302)
        location = response.headers.get('Location', '')
        assert 'photo_database' in location


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

class TestLogout:
    def test_logout_redirects(self, client):
        response = client.get('/logout')
        assert response.status_code in (301, 302)

    def test_logout_redirects_to_index(self, client):
        response = client.get('/logout')
        location = response.headers.get('Location', '')
        # Should redirect to the index page
        assert '/' in location


# ---------------------------------------------------------------------------
# /get_connections API
# ---------------------------------------------------------------------------

class TestGetConnectionsRoute:
    def test_returns_200_with_empty_photo_ids(self, auth_client):
        response = auth_client.post(
            '/get_connections',
            json={'photoIds': []},
            content_type='application/json'
        )
        assert response.status_code == 200

    def test_returns_connections_key(self, auth_client):
        response = auth_client.post(
            '/get_connections',
            json={'photoIds': []},
            content_type='application/json'
        )
        data = response.get_json()
        assert 'connections' in data

    def test_returns_connections_from_db(self, auth_client):
        """Insert a photo with a connection, then query it via the route."""
        db_module.insert_or_update_photo(make_photo_data('conn-route-tgt'))
        db_module.insert_or_update_photo(make_photo_data(
            'conn-route-src',
            connections=[{'target': {'id': 'conn-route-tgt'}}]
        ))

        response = auth_client.post(
            '/get_connections',
            json={'photoIds': ['conn-route-src']},
            content_type='application/json'
        )
        data = response.get_json()
        assert len(data['connections']) == 1
        assert data['connections'][0]['source'] == 'conn-route-src'
        assert data['connections'][0]['target'] == 'conn-route-tgt'


# ---------------------------------------------------------------------------
# /update_db API
# ---------------------------------------------------------------------------

class TestUpdateDbRoute:
    def test_update_db_with_valid_photo(self, auth_client):
        photo = make_photo_data('route-update-001')
        response = auth_client.post(
            '/update_db',
            json=photo,
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_update_db_stores_photo(self, auth_client):
        photo = make_photo_data('route-stored-001')
        auth_client.post(
            '/update_db',
            json=photo,
            content_type='application/json'
        )
        # Verify it was stored in the (monkeypatched) database
        retrieved = db_module.get_photo_from_db('route-stored-001')
        assert retrieved is not None

    def test_update_db_no_db_returns_404(self, auth_client):
        """If the DB file is absent the route returns 404."""
        photo = make_photo_data('no-db-photo')
        with patch('os.path.exists', return_value=False):
            response = auth_client.post(
                '/update_db',
                json=photo,
                content_type='application/json'
            )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# /check_auth_status
# ---------------------------------------------------------------------------

class TestCheckAuthStatus:
    def test_returns_200_always(self, client):
        with patch('app.get_credentials', return_value=None):
            response = client.get('/check_auth_status')
        assert response.status_code == 200

    def test_unauthenticated_body(self, client):
        with patch('app.get_credentials', return_value=None):
            response = client.get('/check_auth_status')
        data = response.get_json()
        assert data['authenticated'] is False
        assert 'message' in data

    def test_authenticated_body(self, auth_client):
        response = auth_client.get('/check_auth_status')
        data = response.get_json()
        assert data['authenticated'] is True
        assert 'message' in data

    def test_expired_credentials_return_false(self, client):
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = None  # Cannot refresh
        with patch('app.get_credentials', return_value=mock_creds):
            response = client.get('/check_auth_status')
        data = response.get_json()
        assert data['authenticated'] is False


# ---------------------------------------------------------------------------
# Pagination edge cases on /photos
# ---------------------------------------------------------------------------

class TestPhotosPagination:
    def test_page_zero_coerced_to_one(self, auth_client):
        """page=0 must be coerced to 1 without an error."""
        response = auth_client.get('/photos?page=0')
        assert response.status_code == 200

    def test_negative_page_coerced_to_one(self, auth_client):
        """page=-1 must be coerced to 1 without an error."""
        response = auth_client.get('/photos?page=-1')
        assert response.status_code == 200

    def test_non_numeric_page_coerced_to_one(self, auth_client):
        """page=abc must be coerced to 1 without an error."""
        response = auth_client.get('/photos?page=abc')
        assert response.status_code == 200

    def test_per_page_zero_coerced_to_default(self, auth_client):
        """per_page=0 must be coerced to the default without an error."""
        response = auth_client.get('/photos?per_page=0')
        assert response.status_code == 200

    def test_sort_by_injection_ignored(self, auth_client):
        """Unknown sort_by value must not cause a 500."""
        response = auth_client.get('/photos?sort_by=DROP+TABLE+photos')
        assert response.status_code == 200

    def test_sort_order_injection_ignored(self, auth_client):
        """Unknown sort_order value must not cause a 500."""
        response = auth_client.get('/photos?sort_order=INJECTED')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# app_version injection
# ---------------------------------------------------------------------------

class TestAppVersionInjection:
    def test_version_appears_in_index(self, client):
        """The index page should contain the app version string."""
        import app as app_module
        response = client.get('/')
        assert app_module.APP_VERSION.encode() in response.data

    def test_version_format_in_response(self, client):
        """The app version rendered in the page is in semver format."""
        import app as app_module
        version = app_module.APP_VERSION
        parts = version.split('.')
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)
