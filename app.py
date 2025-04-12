import time
import requests
import json
import os
import tempfile
import google_auth_oauthlib.flow
import google.auth.exceptions
import re
import logging
import traceback
import shutil
import sqlite3  # Add sqlite3 import
from logging.handlers import RotatingFileHandler
from datetime import datetime
from functools import wraps
from pprint import pprint
from flask import Flask, render_template, request, redirect, jsonify, url_for, flash, redirect, session, g
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from math import radians, cos, sin, sqrt, atan2
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv


# Find the placedID by using this page:
# https://developers.google.com/maps/documentation/places/web-service/place-id

# Load environment variables from .env file
load_dotenv()

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Initialize Flask app
app = Flask(__name__)

def migrate_to_userdata_structure():
    """
    Migrate existing files and directories to the userdata structure.
    This ensures compatibility with existing installations.
    """
    import shutil  # Import once at the top of the function
    
    app.logger.info("Checking userdata directory structure...")
    
    # Create userdata directory if it doesn't exist
    if not os.path.exists("userdata"):
        app.logger.info("Creating userdata directory")
        os.makedirs("userdata")
    
    # Migrate uploads directory
    if os.path.exists("uploads") and not os.path.exists("userdata/uploads"):
        app.logger.info("Moving uploads directory to userdata/")
        shutil.move("uploads", "userdata/uploads")
    elif not os.path.exists("userdata/uploads"):
        app.logger.info("Creating userdata/uploads directory")
        os.makedirs("userdata/uploads")
    
    # Migrate logs directory
    if os.path.exists("logs") and not os.path.exists("userdata/logs"):
        app.logger.info("Moving logs directory to userdata/")
        shutil.move("logs", "userdata/logs")
    elif not os.path.exists("userdata/logs"):
        app.logger.info("Creating userdata/logs directory")
        os.makedirs("userdata/logs")
    
    # Migrate creds.data file
    if os.path.exists("creds.data") and not os.path.exists("userdata/creds.data"):
        app.logger.info("Moving creds.data to userdata/")
        shutil.move("creds.data", "userdata/creds.data")
    
    # Migrate config.json file - with special handling as requested
    if os.path.exists("config.json"):
        app.logger.info("Moving/copying config.json to userdata/")
        # Always use the root config.json, even if one exists in userdata
        shutil.copy("config.json", "userdata/config.json")
        # Remove the original after copying
        os.remove("config.json")
    # Note: We don't create a default config.json if it doesn't exist
    # as per your requirement

# Function Definitions
def get_default_config():
    """Return default configuration values"""
    return {
        "app": {
            "debug": True,
            "port": 5001,
            "host": "0.0.0.0"
        },
        "logging": {
            "level": "INFO",
            "file": "userdata/logs/streetview.log",
            "max_bytes": 1048576,
            "backup_count": 10,
            "format": "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
        },
        "uploads": {
            "directory": "userdata/uploads",
            "allowed_extensions": ["jpg", "jpeg"],
            "max_file_size": 67108864
        },
        "api": {
            "places": {
                "max_results": 60,
                "default_radius": 300
            },
            "photos": {
                "default_page_size": 10,
                "table_page_size": 100,
                "max_nearby_photos": 50
            }
        }
    }

def load_config():
    """Load configuration from userdata/config.json or create with defaults if it doesn't exist"""
    config_path = "userdata/config.json"
    
    try:
        # Check if config file exists and is not empty
        if os.path.exists(config_path) and os.path.getsize(config_path) > 0:
            with open(config_path) as config_file:
                config = json.load(config_file)
                app.logger.info("Loaded existing configuration from userdata/config.json")
        else:
            # Create default configuration
            config = get_default_config()
            
            # Ensure userdata directory exists
            os.makedirs("userdata", exist_ok=True)
            
            # Write default config to file
            with open(config_path, 'w') as config_file:
                json.dump(config, config_file, indent=2)
            app.logger.info("Created default configuration in userdata/config.json")

        # Set logging level
        config['logging']['level'] = getattr(logging, config['logging']['level'].upper())

        return config
    except Exception as e:
        app.logger.error(f"Error loading configuration: {str(e)}")
        raise

def get_client_config(config):
    """Get OAuth client configuration"""
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    redirect_uris = os.getenv('REDIRECT_URI')
    
    if not client_id or not client_secret:
        raise AuthenticationError("Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET environment variables")
    
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "project_id": "streetview-app",  # This is optional but recommended
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",  # Use standard Google OAuth endpoints
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": redirect_uris
        },
        "api_key": api_key
    }

# Custom Exception Classes
class StreetViewError(Exception):
    """Base exception class for StreetView application"""
    pass

class APIError(StreetViewError):
    """Handles Google API related errors"""
    def __init__(self, message, status_code=None, response=None):
        self.status_code = status_code
        self.response = response
        super().__init__(message)

class AuthenticationError(StreetViewError):
    """Handles authentication and authorization errors"""
    pass

class FileOperationError(StreetViewError):
    """Handles file upload and processing errors"""
    pass

class ValidationError(StreetViewError):
    """Handles input validation errors"""
    pass

# Configure Logging
def setup_logging(app, config):
    """Configure application logging based on settings"""
    log_dir = os.path.dirname(config['logging']['file'])
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # File handler for logging to a file
    file_handler = RotatingFileHandler(
        config['logging']['file'],
        maxBytes=config['logging']['max_bytes'],
        backupCount=config['logging']['backup_count']
    )
    file_handler.setFormatter(logging.Formatter(config['logging']['format']))
    file_handler.setLevel(config['logging']['level'])
    
    # Stream handler for logging to stdout/stderr (captured by Docker)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(config['logging']['format']))
    stream_handler.setLevel(config['logging']['level'])
    
    # Remove existing handlers to avoid duplicates
    app.logger.handlers = []
    
    # Add both handlers
    app.logger.addHandler(file_handler)
    app.logger.addHandler(stream_handler)
    app.logger.setLevel(config['logging']['level'])
    
    # Log startup information
    app.logger.info('StreetView application starting')
    app.logger.info(f"Environment: debug={config['app']['debug']}")
    app.logger.info(f"Uploads directory: {config['uploads']['directory']}")
    app.logger.info(f"Log level: {logging.getLevelName(config['logging']['level'])}")

def log_error(error_type, error):
    """Centralized error logging function"""
    app.logger.error(f'{error_type}: {str(error)}')
    if hasattr(error, 'response'):
        app.logger.error(f'Response: {error.response}')
    app.logger.error(f'Stack trace: {traceback.format_exc()}')






# Error Handlers
@app.errorhandler(APIError)
def handle_api_error(error):
    """Handle API-related errors"""
    log_error("API Error", error)
    flash(f"API Error: {str(error)}", "error")
    return render_template('error.html', 
                         error_type="API Error",
                         message=str(error),
                         status_code=error.status_code), error.status_code or 500

@app.errorhandler(AuthenticationError)
def handle_auth_error(error):
    """Handle authentication errors"""
    log_error("Authentication Error", error)
    if "Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET" in str(error):
        flash("Missing Google API credentials. Please check your environment variables.", "error")
        return render_template('error.html', 
                         error_type="Configuration Error",
                         message="Missing Google API credentials. Please ensure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set in your environment variables."), 500
    if "invalid_client" in str(error):
        flash("Invalid Google API credentials. Please check your client ID and secret.", "error")
        return render_template('error.html',
                         error_type="Authentication Error",
                         message="The provided Google API credentials are invalid. Please ensure your GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are correct."), 401
    flash("Authentication failed. Please try logging in again.", "error")
    return redirect(url_for('authorize'))

@app.errorhandler(FileOperationError)
def handle_file_error(error):
    """Handle file operation errors"""
    log_error("File Operation Error", error)
    flash(f"File operation failed: {str(error)}", "error")
    return redirect(url_for('upload_photosphere'))

@app.errorhandler(ValidationError)
def handle_validation_error(error):
    """Handle input validation errors"""
    log_error("Validation Error", error)
    flash(f"Validation Error: {str(error)}", "error")
    return redirect(request.referrer or url_for('index'))

@app.errorhandler(Exception)
def handle_unexpected_error(error):
    """Handle any unhandled exceptions"""
    log_error("Unexpected Error", error)
    flash("An unexpected error occurred. Please try again later.", "error")
    return render_template('error.html',
                         error_type="Unexpected Error",
                         message="An internal server error occurred."), 500

# Request Context Logging
@app.before_request
def log_request_info():
    """Log information about each request"""
    # app.logger.info(f"Request: {request.method} {request.url}")
    app.logger.debug(f"Headers: {dict(request.headers)}")
    if request.method in ['POST', 'PUT']:
        app.logger.debug(f"Form Data: {request.form}")
        app.logger.debug(f"Files: {request.files}")

# @app.after_request
# def log_response_info(response):
#     """Log information about each response"""
#     app.logger.debug(f"Response: {response.status}")
#     return response

def format_capture_time(capture_time):
    dt = datetime.fromisoformat(capture_time[:-1])
    return dt.strftime('%d %b %Y')

def refresh_credentials(credentials):
    try:
        credentials.refresh(Request())
    except google.auth.exceptions.RefreshError:
        os.remove('userdata/creds.data')
        return None
    save_credentials(credentials)
    return credentials

def get_credentials():
    creds_file = 'userdata/creds.data'
    if os.path.exists(creds_file):
        credentials = Credentials.from_authorized_user_file(creds_file, ['https://www.googleapis.com/auth/streetviewpublish'])
        if credentials is None or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                return refresh_credentials(credentials)
            os.remove(creds_file)
            return None
        return credentials
    return None


def save_credentials(credentials):
    with open('userdata/creds.data', 'w') as f:
        f.write(credentials.to_json())

def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        credentials = get_credentials()
        if credentials is None or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                save_credentials(credentials)
            else:
                return redirect(url_for('authorize'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('icons8-menu-96-favicon.png')

@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('index'))

@app.route('/authorize')
def authorize():
    redirect_uri = os.getenv('REDIRECT_URI')
    try:
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            client_config,
            scopes=['https://www.googleapis.com/auth/streetviewpublish'],
            redirect_uri=redirect_uri
        )
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # Force consent screen to get refresh token
        )
        session['oauth_state'] = state  # Store state in session
        return redirect(authorization_url)
    except Exception as e:
        if "invalid_client" in str(e):
            raise AuthenticationError(f"invalid_client: {str(e)}")
        raise

@app.route('/oauth2callback')
def oauth2callback():
    redirect_uri = os.getenv('REDIRECT_URI')
    state = session.get('oauth_state')  # Get state from session
    if not state:
        flash("OAuth state missing. Please try authenticating again.", "error")
        return redirect(url_for('authorize'))
        
    flow = InstalledAppFlow.from_client_config(
        client_config,
        scopes=['https://www.googleapis.com/auth/streetviewpublish'],
        redirect_uri=redirect_uri,
        state=state
    )
    authorization_response = request.url
    try:
        flow.fetch_token(authorization_response=authorization_response)
        credentials = flow.credentials
        save_credentials(credentials)
        flash("Account successfully authenticated.")
        return redirect(url_for('index'))
    except Exception as e:
        if "invalid_client" in str(e):
            raise AuthenticationError(f"invalid_client: {str(e)}")
        raise

@app.route('/list_photos', methods=['GET'])
@token_required
def list_photos_page():

    page_size = request.args.get('page_size', session.get('page_size', str(config['api']['photos']['default_page_size'])))
    session['page_size'] = page_size

    action = request.args.get('action', None)
    page_token = request.args.get('page_token', None)

    # Initialize the page tokens stack in the session if it doesn't exist
    if 'page_tokens' not in session:
        session['page_tokens'] = []

    if action == 'next':
        # Push the current page token onto the stack before going to the next page
        session['page_tokens'].append(session.get('page_token', None))
    elif action == 'prev' and session['page_tokens']:
        # Pop the last page token from the stack to go to the previous page
        page_token = session['page_tokens'].pop()

    # Save the current page token in the session
    session['page_token'] = page_token

    credentials = get_credentials()
    response = list_photos(credentials.token, page_size=int(page_size), page_token=page_token)
    photos_list = response.get("photos", [])

    photoId_to_filename = get_filenames(config['uploads']['directory'])

    for photo in photos_list:
        photo['captureTime'] = format_capture_time(photo['captureTime'])
        photo['uploadTime'] = format_capture_time(photo['uploadTime'])
        photo['filename'] = photoId_to_filename.get(photo['photoId']['id'])
        # Retrieve heading if available
        if 'pose' in photo and 'heading' in photo['pose']:
            heading_value = photo['pose']['heading']
            if isinstance(heading_value, str) and heading_value.lower() == 'nan':
                photo['heading'] = None
            else:
                try:
                    photo['heading'] = float(heading_value)
                except ValueError:
                    photo['heading'] = None
        else:
            photo['heading'] = None

    
    next_page_token = response.get('nextPageToken')

    return render_template('list_photos.html', photos_list=photos_list, page_size=page_size, next_page_token=next_page_token)

@app.route('/photos', methods=['GET'])
@token_required
def photos_page():
    return list_photos_table_page()

# Keep the original route for backward compatibility
@app.route('/list_photos_table', methods=['GET'])
@token_required
def list_photos_table_page():
    """Display all photos from the database in a table format with pagination"""
    try:
        import database
        
        # Check if database exists
        if not os.path.exists(database.DATABASE_PATH):
            flash("Database not yet created. Please use the 'Create Database' button on the Photo Database page first.", "error")
            # Instead of redirecting, still render the photos template but with empty data
            return render_template(
                'photos.html',
                photos=[],
                total_photos=0,
                total_places=0,
                total_connections=0,
                last_updated="N/A",
                sort_by='upload_time',
                sort_order='desc',
                db_exists=False,
                page=1,
                per_page=25,
                total_pages=1,
                total_records=0,
                status_values=[]
            )
        
        # Get sorting parameters
        sort_by = request.args.get('sort_by', 'upload_time')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Get pagination parameters
        per_page = request.args.get('per_page', '25')
        page = request.args.get('page', '1')
        
        # Get filter parameters
        status_filter = request.args.getlist('status_filter')
        places_filter = request.args.get('places_filter', '')
        capture_date_from = request.args.get('capture_date_from', '')
        capture_date_to = request.args.get('capture_date_to', '')
        upload_date_from = request.args.get('upload_date_from', '')
        upload_date_to = request.args.get('upload_date_to', '')
        
        # Store pagination settings in session
        session['per_page'] = per_page
        session['page'] = page
        
        # Convert to integers with fallbacks
        try:
            page = int(page)
            if page < 1:
                page = 1
        except (ValueError, TypeError):
            page = 1
            
        try:
            per_page_int = int(per_page)
            if per_page_int < 1:
                per_page_int = 25
        except (ValueError, TypeError):
            per_page_int = 25
            
        # Get database connection
        conn = sqlite3.connect(database.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get valid columns for sorting
        valid_columns = ['photo_id', 'latitude', 'longitude', 'capture_time', 
                         'upload_time', 'view_count', 'maps_publish_status', 'updated_at',
                         'place_names']
        
        if sort_by not in valid_columns:
            sort_by = 'upload_time'
        
        if sort_order not in ['asc', 'desc']:
            sort_order = 'desc'
        
        # Fetch all unique maps_publish_status values for filtering
        cursor.execute("SELECT DISTINCT maps_publish_status FROM photos WHERE maps_publish_status IS NOT NULL")
        status_values = [row[0] for row in cursor.fetchall()]
        
        # Build base query
        base_query = """
        SELECT p.*, 
               GROUP_CONCAT(DISTINCT pl.name) as place_names,
               COUNT(DISTINCT c.target_photo_id) as connection_count
        FROM photos p
        LEFT JOIN places pl ON p.photo_id = pl.photo_id
        LEFT JOIN connections c ON p.photo_id = c.source_photo_id
        """
        
        # Add filter conditions
        where_clauses = []
        query_params = []
        
        # Status filter
        if status_filter and 'all' not in status_filter:
            placeholders = ','.join(['?' for _ in status_filter])
            where_clauses.append(f"p.maps_publish_status IN ({placeholders})")
            query_params.extend(status_filter)
        
        # Places filter
        if places_filter:
            app.logger.info(f"Places filter applied with value: '{places_filter}'")
            
            # Execute a completely separate query when places filter is used
            place_query = """
            SELECT p.*, 
                   GROUP_CONCAT(DISTINCT places.name) as place_names,
                   COUNT(DISTINCT c.target_photo_id) as connection_count
            FROM photos p
            JOIN places ON p.photo_id = places.photo_id
            LEFT JOIN connections c ON p.photo_id = c.source_photo_id
            WHERE places.name LIKE ? COLLATE NOCASE
            GROUP BY p.photo_id
            ORDER BY {} {}
            """.format(sort_by, sort_order)
            
            search_param = f"%{places_filter}%"
            app.logger.info(f"Place search query: {place_query}")
            app.logger.info(f"Place search parameter: {search_param}")
            
            # Execute the query to get filtered photos
            cursor.execute(place_query, [search_param])
            photos = [dict(row) for row in cursor.fetchall()]
            
            # Count total filtered records
            count_query = """
            SELECT COUNT(DISTINCT p.photo_id)
            FROM photos p
            JOIN places ON p.photo_id = places.photo_id
            WHERE places.name LIKE ? COLLATE NOCASE
            """
            cursor.execute(count_query, [search_param])
            total_records = cursor.fetchone()[0]
            
            app.logger.info(f"Found {total_records} photos matching places filter")
            
            # Calculate pagination
            if per_page != 'all' and total_records > 0:
                total_pages = (total_records + per_page_int - 1) // per_page_int
                if page > total_pages:
                    page = total_pages
                
                # Apply pagination to the results if needed
                start_idx = (page - 1) * per_page_int
                end_idx = start_idx + per_page_int
                photos = photos[start_idx:end_idx]
            else:
                total_pages = 1
                
            # Skip the rest of the query processing since we've handled everything here
            query_executed = True
        else:
            # Initialize for normal query flow
            query_executed = False
        
        # Capture date filter
        if capture_date_from:
            where_clauses.append("p.capture_time >= ?")
            query_params.append(f"{capture_date_from}-01T00:00:00Z")
            
        if capture_date_to:
            # Get the last day of the month for the end date
            year, month = map(int, capture_date_to.split('-'))
            last_day = (datetime(year, month % 12 + 1, 1) - timedelta(days=1)).day
            where_clauses.append("p.capture_time <= ?")
            query_params.append(f"{capture_date_to}-{last_day}T23:59:59Z")
        
        # Upload date filter
        if upload_date_from:
            where_clauses.append("p.upload_time >= ?")
            query_params.append(f"{upload_date_from}-01T00:00:00Z")
            
        if upload_date_to:
            # Get the last day of the month for the end date
            year, month = map(int, upload_date_to.split('-'))
            last_day = (datetime(year, month % 12 + 1, 1) - timedelta(days=1)).day
            where_clauses.append("p.upload_time <= ?")
            query_params.append(f"{upload_date_to}-{last_day}T23:59:59Z")
        
        # Complete the query
        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)
        
        # Add grouping
        base_query += " GROUP BY p.photo_id"
        
        # Count total filtered records
        count_query = f"SELECT COUNT(*) FROM ({base_query})"
        cursor.execute(count_query, query_params)
        total_records = cursor.fetchone()[0]
        
        # Add sorting
        base_query += f" ORDER BY {sort_by} {sort_order}"
        
        # Add pagination
        if per_page != 'all':
            offset = (page - 1) * per_page_int
            base_query += f" LIMIT {per_page_int} OFFSET {offset}"
        
        # Execute final query
        if not query_executed:
            cursor.execute(base_query, query_params)
            photos = [dict(row) for row in cursor.fetchall()]
        
        # Calculate pagination
        total_pages = 1
        if per_page != 'all' and total_records > 0:
            total_pages = (total_records + per_page_int - 1) // per_page_int
            if page > total_pages:
                page = total_pages
        
        # Get total counts for statistics (unfiltered)
        cursor.execute("SELECT COUNT(*) FROM photos")
        total_photos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM places")
        total_places = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM connections")
        total_connections = cursor.fetchone()[0]
        
        # Get the last update time from the database
        cursor.execute("SELECT MAX(updated_at) FROM photos")
        last_updated_row = cursor.fetchone()
        last_updated = last_updated_row[0] if last_updated_row[0] else "N/A"
        
        # Format the last_updated timestamp if it exists
        if last_updated != "N/A":
            try:
                # Convert ISO format string to datetime object
                dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                # Format as a user-friendly string
                last_updated = dt.strftime('%d %b %Y %H:%M')
            except (ValueError, AttributeError):
                # If there's any error in parsing, just use the raw value
                pass
        
        conn.close()
        
        return render_template(
            'photos.html', 
            photos=photos, 
            total_photos=total_photos,
            total_places=total_places,
            total_connections=total_connections,
            last_updated=last_updated,
            sort_by=sort_by,
            sort_order=sort_order,
            db_exists=True,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total_records=total_records,
            status_values=status_values,
            status_filter=status_filter,
            places_filter=places_filter,
            capture_date_from=capture_date_from,
            capture_date_to=capture_date_to,
            upload_date_from=upload_date_from,
            upload_date_to=upload_date_to
        )
        
    except Exception as e:
        app.logger.error(f"Error displaying database content: {str(e)}")
        flash(f"Error retrieving data from database: {str(e)}", "error")
        # Instead of redirecting, render the list_photos_table template with error information
        return render_template(
            'photos.html',
            photos=[],
            total_photos=0,
            total_places=0,
            total_connections=0,
            last_updated="N/A",
            sort_by='upload_time',
            sort_order='desc',
            db_exists=False,
            db_error=str(e),
            page=1,
            per_page=25,
            total_pages=1,
            total_records=0,
            status_values=[]
        )

@app.route('/edit_photo/<photo_id>', methods=['GET'])
@token_required
def edit_photo(photo_id):
    print(f"Editing photo with ID: {photo_id}")
    # Retrieve the photo details from the Streetview API.
    credentials = get_credentials()
    response = get_photo(credentials.token, photo_id)

    page_token = session.get('page_token', None)
    page_size = session.get('page_size', None)

    # Display json result in console
    # pretty-print the JSON response using the pprint function from the pprint module in Python.
    print("Photo details:")
    pprint(response)

    response['captureTime'] = format_capture_time(response['captureTime'])
    response['uploadTime'] = format_capture_time(response['uploadTime'])

    # passing the entire response dictionary to the render_template function
    # Render the 'edit_photo.html' template with the photo details.
    return render_template('edit_photo.html', photo=response, page_token=page_token, page_size=page_size, api_key=client_config['api_key'])

@app.route('/edit_connections/<photo_id>', methods=['GET'])
@token_required
def edit_connections(photo_id):
    print(f"Editing connections with ID: {photo_id}")
    # Retrieve the photo details from the Streetview API.
    credentials = get_credentials()
    response = get_photo(credentials.token, photo_id)

    page_session_token = session.get('page_token', None)
    page_session_size = session.get('page_size', None)

    # Display json result in console
    if app.debug:
        print("Photo details:")
        pprint(response)

    response['captureTime'] = format_capture_time(response['captureTime'])
    response['uploadTime'] = format_capture_time(response['uploadTime'])

    # Validate and filter connections
    connections = response.get('connections', [])
    valid_connections = [conn for conn in connections if conn.get('target') and conn['target'].get('id')]

    response['connections'] = valid_connections

    # Get the distance from the query parameters or use a default value
    distance = request.args.get('distance', 200, type=int)
    if app.debug:
        print(f"Distance: {distance}")

    nearby_photos = []
    if 'pose' in response and 'latLngPair' in response['pose']:
        latitude = response['pose']['latLngPair']['latitude']
        longitude = response['pose']['latLngPair']['longitude']
        response['latitude'] = latitude
        response['longitude'] = longitude
        
        min_lat, max_lat, min_lng, max_lng = calculate_bounding_box(latitude, longitude, distance)
        filters = f"min_latitude={min_lat} max_latitude={max_lat} min_longitude={min_lng} max_longitude={max_lng}"
        
        page_token = None
        while True:
            try:
                nearby_photos_response = list_photos(credentials.token, page_size=50, page_token=page_token, filters=filters)
                photos = nearby_photos_response.get('photos', [])
                
                for nearby_photo in photos:
                    if 'pose' in nearby_photo and 'latLngPair' in nearby_photo['pose']:
                        nearby_lat = nearby_photo['pose']['latLngPair']['latitude']
                        nearby_lng = nearby_photo['pose']['latLngPair']['longitude']
                        distance_to_photo = calculate_distance(latitude, longitude, nearby_lat, nearby_lng)
                        if distance_to_photo > 0:  # Exclude the source photo
                            nearby_photo['distance'] = round(distance_to_photo, 2)
                            nearby_photo['formattedCaptureTime'] = format_capture_time(nearby_photo['captureTime'])
                            nearby_photos.append(nearby_photo)
                
                page_token = nearby_photos_response.get('nextPageToken')
                if not page_token:
                    break
            except requests.exceptions.RequestException as e:
                print(f"Error fetching nearby photos: {e}")
                break
        
        # Sort the nearby photos by distance
        nearby_photos.sort(key=lambda x: x['distance'])
        
        # Assign labels after sorting
        for index, photo in enumerate(nearby_photos):
            photo['label'] = str(index + 1)  # Generate labels 1, 2, 3, ...

    # passing the entire response dictionary to the render_template function
    # Render the 'edit_connections.html' template with the photo details.
    return render_template('edit_connections.html', photo=response, nearby_photos=nearby_photos, distance=distance, page_token=page_session_token, page_size=page_session_size, api_key=client_config['api_key'])

@app.route('/get_connections', methods=['POST'])
def get_connections():
    data = request.json
    photo_ids = data.get('photoIds', [])

    # if debug:
    #     print(f"Received request to fetch connections for photo_ids: {photo_ids}")

    all_connections = []
    for photo_id in photo_ids:
        try:
            # if debug:
            #     print(f"Fetching connections for photo_id {photo_id}")
            photo = get_photo_by_id(photo_id)
            if photo and 'connections' in photo:
                for conn in photo['connections']:
                    all_connections.append({
                        'source': photo_id,
                        'target': conn['target']['id']
                    })
                # if debug:
                #     print(f"Found connections for photo_id {photo_id}: {photo['connections']}")
        except Exception as e:
            print(f"Error fetching connections for photo_id {photo_id}: {e}")

    # if debug:
    #     print(f"Returning all connections:")
    #     pprint(all_connections)

    return jsonify(connections=all_connections), 200


@app.route('/create_connections', methods=['POST'])
@token_required
def create_connections():
    request_data = request.get_json()
    credentials = get_credentials()

    if app.debug:
        # Debug: Print the request data
        print("Connections Request Data:")
        pprint(request_data)

    try:
        response = requests.post(
            'https://streetviewpublish.googleapis.com/v1/photos:batchUpdate',
            headers={
                'Authorization': f'Bearer {credentials.token}',
                'Content-Type': 'application/json'
            },
            json=request_data
        )
        response.raise_for_status()

        if app.debug:
            print("Connections Response:")
            print(response.json())        

        main_message = 'Connections created successfully'
        details = "Please allow up to 10 mins for the new connections to be visible on this page. It will take several hours to appear on the photosphere itself."
        flash(f'{main_message}<br><span class="flash-details">{details}</span>', 'success')

        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Error creating connections: {e}")
        flash('Failed to create connections', 'error')
        return jsonify({'error': 'Failed to create connections'}), 500

@app.route('/update_photo/<photo_id>', methods=['POST'])
@token_required
def update_photo(photo_id):
    def parse_float(value):
        try:
            return round(float(value), 7) if value not in [None, ''] else None
        except ValueError:
            return None

    photo = {
        "pose": {
            "latLngPair": {
                "latitude": parse_float(request.form.get('latitude')),
                "longitude": parse_float(request.form.get('longitude'))
            },
            "heading": parse_float(request.form.get('heading'))
        }
    }

    if not (0 <= photo["pose"]["heading"] < 360 if photo["pose"]["heading"] is not None else True):
        flash("Heading must be between 0 and 360", "error")
        return redirect(url_for('edit_photo', photo_id=photo_id))

    place_id = request.form.get('placeId')
    if place_id:
        photo["places"] = [{"placeId": place_id, "languageCode": "en"}]

    credentials = get_credentials()
    try:
        response = update_photo_api(credentials.token, photo_id, photo)
        # If we get here, the update was successful since update_photo_api would raise an APIError on failure
        main_message = 'Photo updated successfully'
        details = "Please refresh the page after 30 seconds to see the changes."
        flash(f'{main_message}<br><span class="flash-details">{details}</span>', 'success')
        return redirect(url_for('edit_photo', photo_id=photo_id))
    except APIError as e:
        flash(f'Error updating photo: {str(e)}', 'error')
        return redirect(url_for('edit_photo', photo_id=photo_id))



@app.route('/nearby_places', methods=['GET'])
def nearby_places():
    latitude = request.args.get('latitude')
    longitude = request.args.get('longitude')
    radius = request.args.get('radius', default=config['api']['places']['default_radius'])  # use configured default radius

    # convert latitude and longitude to floats
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except ValueError:
        return jsonify({"error": "Invalid latitude or longitude"}), 400

    places_info = get_nearby_places(latitude, longitude, radius, client_config['api_key'])
    return jsonify(places_info)

@app.route('/upload', methods=['GET', 'POST'])
@token_required
def upload_photosphere():
    if request.method == 'POST':
        if app.debug:
            print("Received POST request for uploading photosphere.")
            print("Form data:", request.form)

        credentials = get_credentials()

        # Start the upload
        upload_ref = start_upload(credentials.token)
        upload_ref_message = f"Created upload url: {upload_ref}"
        if app.debug:
            print(upload_ref_message)

        # Save the uploaded file to a temporary location on the server
        file = request.files['file']
        file_path = os.path.join(tempfile.gettempdir(), file.filename)
        file.save(file_path)
        if app.debug:
            print(f"Saved file to {file_path}")

        # Get the heading value from the form
        heading = request.form['heading']

        # Upload the photo bytes to the Upload URL
        upload_status = upload_photo(credentials.token, upload_ref, file_path, heading)
        upload_status_message = f"Upload status: {upload_status}"
        if app.debug:
            print(upload_status_message)

        # Remove the temporary file
        os.remove(file_path)
        if app.debug:
            print(f"Removed temporary file {file_path}")

        # Upload the metadata of the photo
        latitude = float(request.form['latitude'])
        longitude = float(request.form['longitude'])
        placeId = request.form['placeId']

        create_photo_response = create_photo(credentials.token, upload_ref, latitude, longitude, placeId)
        create_photo_response_message = f"Create photo response: {create_photo_response}"
        if app.debug:
            print(f"Metadata - Latitude: {latitude}, Longitude: {longitude}, Place ID: {placeId}")
            print(create_photo_response_message)

        # Save the create_photo_response JSON data to a file named after the photo filename
        # uploads_directory = "uploads"
        uploads_directory = config['uploads']['directory']
        os.makedirs(uploads_directory, exist_ok=True)

        # Prepare initial filename
        base_filename = os.path.splitext(file.filename)[0]
        counter = 0
        json_filename = f"{base_filename}.json"

        # Iterate through possible filenames
        while os.path.exists(os.path.join(uploads_directory, json_filename)):
            counter += 1
            json_filename = f"{base_filename}_{counter}.json"

        # Write to the new file
        json_filepath = os.path.join(uploads_directory, json_filename)
        with open(json_filepath, 'w') as f:
            json.dump(create_photo_response, f, indent=2)


        return render_template('upload_result.html', upload_ref_message=upload_ref_message, upload_status_message=upload_status_message, create_photo_response=create_photo_response, create_photo_response_message=create_photo_response_message, photo_filename = file.filename)

    return render_template('upload.html')

@app.route('/delete_photo', methods=['POST'])
@token_required
def delete_photo():
    credentials = get_credentials()
    photo_id = request.form.get("photo_id").strip("{'id': }")

    # Call the Street View Publish API to delete the photo
    url = f'https://streetviewpublish.googleapis.com/v1/photo/{photo_id}?photoId={photo_id}'
    headers = {'Authorization': f'Bearer {credentials.token}'}
    response = requests.delete(url, headers=headers)

    # print(f"Response object: {response}")
    # print(f"Response status code: {response.status_code}")
    # print(f"Response text: {response.text}")

    if response.status_code != 200:
        flash(f'Failed to delete photo. Error: {response.text}', 'error')
    else:
        flash('Photo deleted successfully.', 'success')


    return redirect(url_for('list_photos_page'))

def get_filenames(directory):
    mapping = {}
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            with open(os.path.join(directory, filename), 'r') as f:
                try:
                    content = json.load(f)
                    if isinstance(content, dict):
                        photoId = content.get('photoId', {}).get('id')
                        if photoId:
                            # print(f"Processing file: {filename}")  # Print the filename being processed
                            mapping[photoId] = filename
                except json.JSONDecodeError:
                    print(f"Skipping file due to JSONDecodeError: {filename}")
    return mapping

def list_photos(token, page_size=10, page_token=None, filters=None):
    """List photos with error handling and validation"""
    try:
        url = "https://streetviewpublish.googleapis.com/v1/photos"
        headers = {
            "Authorization": f"Bearer {token}",
        }
        params = {
            "pageSize": page_size,
            "view": "BASIC",
        }
        if page_token is not None:
            params["pageToken"] = page_token
        if filters is not None:
            params["filter"] = filters
        
        app.logger.info(f"Fetching photos with params: {params}")
        response = requests.get(url, headers=headers, params=params)
        return handle_api_response(response, "Failed to list photos")
    except Exception as e:
        app.logger.error(f"Error in list_photos: {str(e)}")
        raise APIError("Failed to list photos", response=getattr(e, 'response', None))

def get_photo(token, photo_id):
    """Get a single photo with error handling"""
    try:
        url = f"https://streetviewpublish.googleapis.com/v1/photo/{photo_id}"
        headers = {
            "Authorization": f"Bearer {token}",
        }
        app.logger.info(f"Fetching photo with ID: {photo_id}")
        response = requests.get(url, headers=headers)        
        return handle_api_response(response, f"Failed to get photo {photo_id}")
    except Exception as e:
        app.logger.error(f"Error in get_photo: {str(e)}")
        raise APIError(f"Failed to get photo {photo_id}", response=getattr(e, 'response', None))

def get_photo_by_id(photo_id):
    """Get photo by ID with comprehensive error handling"""
    try:
        credentials = get_credentials()
        if not credentials:
            raise AuthenticationError("No valid credentials available")
        
        app.logger.info(f"Fetching photo details for ID: {photo_id}")
        return get_photo(credentials.token, photo_id)
    except Exception as e:
        app.logger.error(f"Error fetching photo details for photo_id {photo_id}: {str(e)}")
        if isinstance(e, (APIError, AuthenticationError)):
            raise
        raise APIError(f"Failed to get photo {photo_id}", response=getattr(e, 'response', None))

def update_photo_api(token, photo_id, photo):
    """Update photo with validation and error handling"""
    try:
        # Validate coordinates if present
        if 'pose' in photo and 'latLngPair' in photo['pose']:
            lat = photo['pose']['latLngPair'].get('latitude')
            lng = photo['pose']['latLngPair'].get('longitude')
            if lat is not None and lng is not None:
                validate_coordinates(lat, lng)

        # Validate heading if present
        if 'pose' in photo and 'heading' in photo['pose']:
            photo['pose']['heading'] = validate_heading(photo['pose']['heading'])

        # Build update mask
        updateMask = []
        for key in photo:
            if key == 'pose':
                for subkey, subvalue in photo[key].items():
                    if subvalue is not None:
                        if subkey == 'latLngPair':
                            for subsubkey, subsubvalue in subvalue.items():
                                if subsubvalue is not None:
                                    updateMask.append('pose.latLngPair')
                                    break
                        else:
                            updateMask.append(f'pose.{subkey}')
            elif key == 'places' and photo[key]:
                updateMask.append('places')
        
        updateMask = ','.join(updateMask)
        app.logger.info(f"Updating photo {photo_id} with mask: {updateMask}")

        url = f"https://streetviewpublish.googleapis.com/v1/photo/{photo_id}?updateMask={updateMask}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        response = requests.put(url, headers=headers, json=photo)
        return handle_api_response(response, f"Failed to update photo {photo_id}")
    except ValidationError:
        raise
    except Exception as e:
        app.logger.error(f"Error updating photo {photo_id}: {str(e)}")
        if isinstance(e, APIError):
            raise
        raise APIError(f"Failed to update photo {photo_id}", response=getattr(e, 'response', None))

def start_upload(token):
    """Start a new photo upload with error handling"""
    try:
        url = "https://streetviewpublish.googleapis.com/v1/photo:startUpload"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        app.logger.info("Starting new photo upload")
        response = requests.post(url, headers=headers)
        return handle_api_response(response, "Failed to start upload")
    except Exception as e:
        app.logger.error(f"Error in start_upload: {str(e)}")
        raise APIError("Failed to start upload", response=getattr(e, 'response', None))

def add_or_update_xmp_metadata(file_path, heading):
    """Add or update XMP metadata with error handling"""
    try:
        # Validate heading
        validated_heading = validate_heading(heading)
        
        # Read the image
        try:
            with open(file_path, "rb") as f:
                img_data = f.read()
        except IOError as e:
            raise FileOperationError(f"Failed to read image file: {str(e)}")

        # Search for existing XMP metadata
        start_marker = b"<?xpacket begin="
        end_marker = b"<?xpacket end="
        xmp_start = img_data.find(start_marker)
        xmp_end = img_data.find(end_marker)

        if (xmp_start != -1) and (xmp_end != -1):
            xmp_data = img_data[xmp_start:xmp_end + len(end_marker)].decode("utf-8")
        else:
            xmp_data = """
            <x:xmpmeta xmlns:x="adobe:ns:meta/">
                <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
                    <rdf:Description rdf:about=""
                        xmlns:GPano="http://ns.google.com/photos/1.0/panorama/">
                    </rdf:Description>
                </rdf:RDF>
            </x:xmpmeta>
            """

        # Update XMP data
        if '<GPano:PoseHeadingDegrees>' not in xmp_data:
            xmp_data = re.sub(
                r'(<rdf:Description[^>]*>)',
                r'\1<GPano:PoseHeadingDegrees>{}</GPano:PoseHeadingDegrees>'.format(validated_heading),
                xmp_data
            )
        else:
            xmp_data = re.sub(
                r'<GPano:PoseHeadingDegrees>.*?</GPano:PoseHeadingDegrees>',
                f'<GPano:PoseHeadingDegrees>{validated_heading}</GPano:PoseHeadingDegrees>',
                xmp_data
            )

        # Save the updated image
        temp_file_path = file_path + "_temp.jpg"
        try:
            with open(temp_file_path, "wb") as out_file:
                out_file.write(img_data[:xmp_start])
                out_file.write(xmp_data.encode('utf-8'))
                out_file.write(img_data[xmp_end:])
        except IOError as e:
            raise FileOperationError(f"Failed to write temporary file: {str(e)}")

        return temp_file_path
    except Exception as e:
        app.logger.error(f"Error in add_or_update_xmp_metadata: {str(e)}")
        if isinstance(e, (ValidationError, FileOperationError)):
            raise
        raise FileOperationError(f"Failed to process image metadata: {str(e)}")

def upload_photo(token, upload_ref, file_path, heading):
    """Upload photo with validation and error handling"""
    try:
        # Add XMP metadata to the photo
        temp_file_path = add_or_update_xmp_metadata(file_path, heading)
        app.logger.info(f"Created temporary file with metadata: {temp_file_path}")

        try:
            with open(temp_file_path, "rb") as f:
                raw_data = f.read()
        except IOError as e:
            raise FileOperationError(f"Failed to read temporary file: {str(e)}")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "image/jpeg",
            "X-Goog-Upload-Protocol": "raw",
            "X-Goog-Upload-Content-Length": str(len(raw_data)),
        }

        app.logger.info("Uploading photo data")
        response = requests.post(upload_ref["uploadUrl"], data=raw_data, headers=headers)
        return handle_api_response(response, "Failed to upload photo")
    except Exception as e:
        app.logger.error(f"Error in upload_photo: {str(e)}")
        if isinstance(e, (ValidationError, FileOperationError, APIError)):
            raise
        raise APIError("Failed to upload photo", response=getattr(e, 'response', None))
    finally:
        # Clean up temporary file
        if 'temp_file_path' in locals():
            try:
                os.remove(temp_file_path)
                app.logger.info(f"Cleaned up temporary file: {temp_file_path}")
            except OSError as e:
                app.logger.warning(f"Failed to clean up temporary file: {str(e)}")

def create_photo(token, upload_ref, latitude, longitude, placeId):
    """Create photo with validation and error handling"""
    try:
        # Validate coordinates
        validated_lat, validated_lng = validate_coordinates(latitude, longitude)

        url = "https://streetviewpublish.googleapis.com/v1/photo"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        body = {
            "uploadReference": {"uploadUrl": upload_ref['uploadUrl']},
            "pose": {
                "latLngPair": {
                    "latitude": validated_lat,
                    "longitude": validated_lng
                },
            },
        }
        if placeId:
            body["places"] = [{"placeId": placeId, "languageCode": "en"}]

        app.logger.info(f"Creating photo with coordinates: {validated_lat}, {validated_lng}")
        response = requests.post(url, headers=headers, json=body)
        return handle_api_response(response, "Failed to create photo")
    except Exception as e:
        app.logger.error(f"Error in create_photo: {str(e)}")
        if isinstance(e, (ValidationError, APIError)):
            raise
        raise APIError("Failed to create photo", response=getattr(e, 'response', None))

def calculate_distance(lat1, lon1, lat2, lon2):
    # approximate radius of earth in km
    R = 6371.0

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c

    # convert to miles and round to two decimal places
    distance = round(distance * 0.621371, 2)
    return distance

def get_nearby_places(latitude, longitude, radius, api_key):
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    
    params = {
        "location": f"{latitude},{longitude}",
        "radius": radius, # in meters
        "key": api_key
    }
    
    places_info = []
    next_page_token = None

    while True:
        if next_page_token:
            params['pagetoken'] = next_page_token

        response = requests.get(url, params=params)
        data = response.json()

        # debug - print the number of results
        # print("Number of results: ", len(data["results"]))

        for place in data["results"]:
            place_id = place["place_id"]
            place_name = place["name"]
            place_icon = place["icon"]
            place_lat = place["geometry"]["location"]["lat"]
            place_lng = place["geometry"]["location"]["lng"]

            # calculate the distance
            distance = calculate_distance(latitude, longitude, place_lat, place_lng)
            places_info.append({
                "place_id": place_id,
                "icon": place_icon,
                "name": place_name,
                "distance": distance  # in miles
            })

        next_page_token = data.get('next_page_token')

        # if there is no next page token or we've gathered enough places, break
        if not next_page_token or len(places_info) >= config['api']['places']['max_results']:
            break

        # Important: There is a short delay between when a next_page_token is issued, and when it will become valid.
        time.sleep(2)

    return places_info

def calculate_bounding_box(lat, lng, radius):
    # Latitude: 1 degree = 111.32 km
    lat_diff = radius / 111320
    # Longitude: 1 degree = 111.32 * cos(latitude) km
    lng_diff = radius / (111320 * cos(radians(lat)))

    min_lat = lat - lat_diff
    max_lat = lat + lat_diff
    min_lng = lng - lng_diff
    max_lng = lng + lng_diff

    return min_lat, max_lat, min_lng, max_lng

# Second calculate_distance function removed as it duplicates functionality

def validate_coordinates(latitude, longitude):
    """Validate latitude and longitude values"""
    try:
        lat = float(latitude)
        lng = float(longitude)
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            raise ValidationError("Invalid coordinates: Latitude must be between -90 and 90, Longitude between -180 and 180")
        return lat, lng
    except (TypeError, ValueError):
        raise ValidationError("Invalid coordinates: Must be valid numbers")

def validate_heading(heading):
    """Validate heading value"""
    if heading is None:
        return None
    try:
        heading_float = float(heading)
        if not (0 <= heading_float < 360):
            raise ValidationError("Heading must be between 0 and 360 degrees")
        return heading_float
    except ValueError:
        raise ValidationError("Invalid heading: Must be a valid number")

def handle_api_response(response, error_message="API request failed"):
    """Handle API response and raise appropriate exceptions"""
    try:
        response.raise_for_status()
        return response.json() if response.content else None
    except requests.exceptions.RequestException as e:
        try:
            error_data = response.json()
            error_detail = error_data.get('error', {}).get('message', str(e))
        except (ValueError, AttributeError):
            error_detail = str(e)
        
        raise APIError(
            f"{error_message}: {error_detail}",
            status_code=response.status_code if hasattr(response, 'status_code') else None,
            response=response
        )

def fetch_all_photos(credentials, page_size=100):
    """
    Fetch all photos from the Street View API and return them as a list.
    This function handles pagination and fetches all available photos.
    Also stores the photos in a SQLite database for local access.
    
    Args:
        credentials: The OAuth2 credentials object
        page_size: Number of photos to fetch per page
        
    Returns:
        List of photo objects from the API
    """
    app.logger.info("Fetching all photos from Street View API")
    photos_list = []
    page_token = None
    
    while True:
        response = list_photos(credentials.token, page_size=int(page_size), page_token=page_token)
        batch = response.get("photos", [])
        photos_list.extend(batch)
        
        app.logger.info(f"Fetched {len(batch)} photos, total so far: {len(photos_list)}")
        
        # Check if there's a next page
        if 'nextPageToken' in response:
            page_token = response['nextPageToken']
        else:
            break

    # Output to a JSON file in userdata
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join("userdata", "data")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"all_photos_{timestamp}.json")
    
    with open(output_file, 'w') as f:
        json.dump(photos_list, f, indent=2)
    
    app.logger.info(f"Saved {len(photos_list)} photos to {output_file}")
    
    # Store in SQLite database
    try:
        import database
        # Initialize database if needed
        database.init_db()
        
        # Store each photo in the database
        success_count = 0
        for photo in photos_list:
            if database.insert_or_update_photo(photo):
                success_count += 1
        
        app.logger.info(f"Stored {success_count}/{len(photos_list)} photos in SQLite database")
        
        # Get database statistics
        stats = database.get_db_stats()
        app.logger.info(f"Database stats: {stats}")
    except Exception as e:
        app.logger.error(f"Error storing photos in database: {str(e)}")
    
    return photos_list

@app.route('/photo_database')
@token_required
def photo_database():
    """Display the photo database page with statistics"""
    stats = {}
    json_files = []
    
    # Get database statistics if database exists
    try:
        import database
        if os.path.exists(database.DATABASE_PATH):
            stats = database.get_db_stats()
    except Exception as e:
        app.logger.error(f"Error getting database stats: {str(e)}")
        flash(f"Error retrieving database statistics: {str(e)}", "error")
    
    # List JSON files in the data directory
    try:
        data_dir = os.path.join("userdata", "data")
        if os.path.exists(data_dir):
            for filename in os.listdir(data_dir):
                if filename.endswith('.json') and filename.startswith('all_photos_'):
                    file_path = os.path.join(data_dir, filename)
                    file_stats = os.stat(file_path)
                    # Format date as DD MMM YYYY HH:MM
                    file_date = datetime.fromtimestamp(file_stats.st_mtime).strftime('%d %b %Y %H:%M')
                    # Format file size as KB or MB
                    file_size = file_stats.st_size
                    if file_size < 1024 * 1024:
                        size_str = f"{file_size / 1024:.1f} KB"
                    else:
                        size_str = f"{file_size / (1024 * 1024):.1f} MB"
                    
                    json_files.append({
                        'name': filename,
                        'date': file_date,
                        'size': size_str
                    })
            # Sort by date (newest first)
            json_files.sort(key=lambda x: x['name'], reverse=True)
    except Exception as e:
        app.logger.error(f"Error listing JSON files: {str(e)}")
        flash(f"Error listing JSON export files: {str(e)}", "error")
    
    return render_template('photo_database.html', stats=stats, json_files=json_files)

@app.route('/create_database', methods=['POST'])
@token_required
def create_database():
    """Create/update the database with all photos from the API"""
    try:
        credentials = get_credentials()
        
        # Fetch all photos from the API
        photos_list = fetch_all_photos(credentials, page_size=100)
        
        # Get database statistics
        import database
        stats = database.get_db_stats()
        
        flash(f"Successfully created database with {stats['photo_count']} photos", "success")
    except Exception as e:
        app.logger.error(f"Error creating database: {str(e)}")
        flash(f"Error creating database: {str(e)}", "error")
    
    return redirect(url_for('photo_database'))

@app.route('/database_viewer', methods=['GET'])
@token_required
def database_viewer():
    """Display all photos from the database in a table format"""
    try:
        import database
        
        # Check if database exists
        if not os.path.exists(database.DATABASE_PATH):
            flash("Database not yet created. Please use the 'Create Database' button on the Photo Database page first.", "error")
            # Instead of redirecting, still render the database_viewer template but with empty data
            return render_template(
                'database_viewer.html',
                photos=[],
                total_photos=0,
                total_places=0,
                total_connections=0,
                sort_by='upload_time',
                sort_order='desc',
                db_exists=False
            )
        
        # Get sorting parameters
        sort_by = request.args.get('sort_by', 'upload_time')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Get database connection
        conn = sqlite3.connect(database.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get photos with sorting
        valid_columns = ['photo_id', 'latitude', 'longitude', 'capture_time', 
                         'upload_time', 'view_count', 'maps_publish_status', 'updated_at']
        
        if sort_by not in valid_columns:
            sort_by = 'upload_time'
        
        if sort_order not in ['asc', 'desc']:
            sort_order = 'desc'
        
        query = f"""
        SELECT p.*, 
               GROUP_CONCAT(DISTINCT pl.name) as place_names,
               COUNT(DISTINCT c.target_photo_id) as connection_count
        FROM photos p
        LEFT JOIN places pl ON p.photo_id = pl.photo_id
        LEFT JOIN connections c ON p.photo_id = c.source_photo_id
        GROUP BY p.photo_id
        ORDER BY {sort_by} {sort_order}
        """
        
        cursor.execute(query)
        photos = [dict(row) for row in cursor.fetchall()]
        
        # Get total counts for statistics
        cursor.execute("SELECT COUNT(*) FROM photos")
        total_photos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM places")
        total_places = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM connections")
        total_connections = cursor.fetchone()[0]
        
        conn.close()
        
        return render_template(
            'database_viewer.html', 
            photos=photos, 
            total_photos=total_photos,
            total_places=total_places,
            total_connections=total_connections,
            sort_by=sort_by,
            sort_order=sort_order,
            db_exists=True
        )
        
    except Exception as e:
        app.logger.error(f"Error displaying database content: {str(e)}")
        flash(f"Error retrieving data from database: {str(e)}", "error")
        # Instead of redirecting, render the database_viewer template with error information
        return render_template(
            'database_viewer.html',
            photos=[],
            total_photos=0,
            total_places=0,
            total_connections=0,
            sort_by='upload_time',
            sort_order='desc',
            db_exists=False,
            db_error=str(e)
        )

def init_app():
    """Initialize the application"""
    # Set up basic console logging before migration
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        app.logger.addHandler(console_handler)
        app.logger.setLevel(logging.INFO)

        # Userdata migration
        migrate_to_userdata_structure()

        # Load configuration and initialize app settings
        # Explicitly declare these as global to modify the module-level variables
        global config, client_config 
        config = load_config()
        client_config = get_client_config(config)

        # Initialize logging and configure application
        setup_logging(app, config)

        # Configure Flask application
        app.config.update({
            'SECRET_KEY': os.getenv('GOOGLE_CLIENT_SECRET'),  # Use the Google Client Secret as the Flask secret key
            'DEBUG': config['app']['debug'],
            'MAX_CONTENT_LENGTH': config['uploads']['max_file_size'],
            'UPLOAD_FOLDER': config['uploads']['directory'],
            'ALLOWED_EXTENSIONS': set(config['uploads']['allowed_extensions'])
        })

        # Create upload directory if it doesn't exist
        if not os.path.exists(config['uploads']['directory']):
            os.makedirs(config['uploads']['directory'])

        # Log application configuration
        app.logger.info("StreetView application configured")
        app.logger.info(f"Environment: debug={app.config['DEBUG']}")
        app.logger.info(f"Uploads directory: {app.config['UPLOAD_FOLDER']}")
        app.logger.info(f"Max upload size: {app.config['MAX_CONTENT_LENGTH']} bytes")

# Initialize the application
init_app()

if __name__ == '__main__':
    # Run the Flask development server
    # Use configuration values loaded by init_app()
    app.run(host=config['app']['host'], port=config['app']['port'], debug=config['app']['debug'])
