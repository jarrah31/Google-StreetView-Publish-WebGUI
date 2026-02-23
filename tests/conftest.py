"""
Shared pytest fixtures for all test modules.
"""
import os
import sqlite3
import tempfile
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Ensure required env vars exist before app is imported
# ---------------------------------------------------------------------------
os.environ.setdefault('FLASK_SECRET_KEY', 'test-secret-key-for-pytest')
os.environ.setdefault('GOOGLE_CLIENT_ID', 'test-client-id')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'test-client-secret')
os.environ.setdefault('GOOGLE_MAPS_API_KEY', 'test-maps-key')
os.environ.setdefault('REDIRECT_URI', 'http://127.0.0.1:5001/oauth2callback')
os.environ.setdefault('OAUTHLIB_INSECURE_TRANSPORT', '1')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_photo_data(photo_id='test-photo-001', **overrides):
    """Return a minimal valid API photo payload."""
    data = {
        'photoId': {'id': photo_id},
        'captureTime': '2024-01-15T10:30:00Z',
        'uploadTime': '2024-01-15T11:00:00Z',
        'viewCount': 42,
        'mapsPublishStatus': 'PUBLISHED',
        'shareLink': f'https://maps.google.com/maps?q={photo_id}',
        'thumbnailUrl': f'https://example.com/thumb/{photo_id}.jpg',
        'pose': {
            'latLngPair': {'latitude': 51.5074, 'longitude': -0.1278},
            'heading': 180.0,
            'altitude': 10.0,
            'pitch': 0.0,
            'roll': 0.0,
        },
        'places': [
            {'placeId': 'ChIJdd4hrwug2EcRmSrV3Vo6llI', 'name': 'London', 'languageCode': 'en'}
        ],
        'connections': [],
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    """
    Provide a temporary SQLite database and patch database.DATABASE_PATH to use it.
    The database is fully initialised (tables + indexes) before each test.
    """
    import database as db_module
    db_file = str(tmp_path / 'test.db')
    monkeypatch.setattr(db_module, 'DATABASE_PATH', db_file)
    db_module.init_db()
    yield db_file


# ---------------------------------------------------------------------------
# Flask app / client fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def app_instance(tmp_path, monkeypatch):
    """
    Return a configured Flask test app with:
    - TESTING=True, WTF_CSRF_ENABLED=False
    - Rate limiting disabled
    - Temporary DB path
    - Uploads directory pointing to a temp folder
    - No real credential file required
    """
    import database as db_module

    # Patch DB path
    db_file = str(tmp_path / 'test.db')
    monkeypatch.setattr(db_module, 'DATABASE_PATH', db_file)
    db_module.init_db()

    # Patch uploads directory
    uploads_dir = str(tmp_path / 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)

    import app as app_module
    app_module.app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret',
        'RATELIMIT_ENABLED': False,
    })
    # Patch config so uploads point to tmp dir
    app_module.config['uploads']['directory'] = uploads_dir

    yield app_module.app


@pytest.fixture()
def client(app_instance):
    """Flask test client (unauthenticated)."""
    with app_instance.test_client() as c:
        yield c


@pytest.fixture()
def auth_client(app_instance, tmp_path):
    """
    Flask test client with a mock valid credential injected so that
    @token_required passes on every request.
    """
    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds.expired = False
    mock_creds.token = 'mock-bearer-token'
    mock_creds.expiry = None  # Avoid MagicMock appearing in JSON responses

    with patch('app.get_credentials', return_value=mock_creds):
        with app_instance.test_client() as c:
            yield c
