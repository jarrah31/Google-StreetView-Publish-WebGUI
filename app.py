
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

# Function Definitions
def load_config():
    """Load configuration from config.json"""
    try:
        # Load main configuration
        with open("config.json") as config_file:
            config = json.load(config_file)

        # Process configuration
        port = config['app']['port']
        if 'web' in config and 'redirect_uris' in config['web']:
            config['web']['redirect_uris'] = config['web']['redirect_uris'].replace("{PORT}", str(port))

        # Set logging level
        config['logging']['level'] = getattr(logging, config['logging']['level'].upper())

        return config
    except Exception as e:
        print(f"Error loading configuration: {str(e)}")
        raise

def get_client_config(config):
    """Get OAuth client configuration"""
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    
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
            "redirect_uris": [config['web']['redirect_uris']],
            "javascript_origins": [f"http://{config['app']['host']}:{config['app']['port']}"]
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
    
    file_handler = RotatingFileHandler(
        config['logging']['file'],
        maxBytes=config['logging']['max_bytes'],
        backupCount=config['logging']['backup_count']
    )
    
    file_handler.setFormatter(logging.Formatter(config['logging']['format']))
    file_handler.setLevel(config['logging']['level'])
    
    # Remove existing handlers to avoid duplicates
    app.logger.handlers = []
    
    app.logger.addHandler(file_handler)
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
    """Handle validation errors"""
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
    app.logger.info(f"Request: {request.method} {request.url}")
    app.logger.debug(f"Headers: {dict(request.headers)}")
    if request.method in ['POST', 'PUT']:
        app.logger.debug(f"Form Data: {request.form}")
        app.logger.debug(f"Files: {request.files}")

@app.after_request
def log_response_info(response):
    """Log information about each response"""
    app.logger.info(f"Response: {response.status}")
    return response

def format_capture_time(capture_time):
    dt = datetime.fromisoformat(capture_time[:-1])
    return dt.strftime('%d %b %Y')

def refresh_credentials(credentials):
    try:
        credentials.refresh(Request())
    except google.auth.exceptions.RefreshError:
        os.remove('creds.data')
        return None
    save_credentials(credentials)
    return credentials

def get_credentials():
    creds_file = 'creds.data'
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
    with open('creds.data', 'w') as f:
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
    redirect_uri = config['web']['redirect_uris']
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
    redirect_uri = config['web']['redirect_uris']
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

    page_size = request.args.get('page_size', session.get('page_size', '10'))
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

    photoId_to_filename = get_filenames('uploads')

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

@app.route('/list_photos_table', methods=['GET'])
@token_required
def list_photos_table_page():
    page_size = request.args.get('page_size', 100)  # Default to 100 items per page
    credentials = get_credentials()
    
    photos_list = []
    page_token = None
    
    while True:
        response = list_photos(credentials.token, page_size=int(page_size), page_token=page_token)
        photos_list.extend(response.get("photos", []))
        
        # Check if there's a next page
        if 'nextPageToken' in response:
            page_token = response['nextPageToken']
        else:
            break

    photoId_to_filename = get_filenames('uploads')

    for photo in photos_list:
        photo['captureTime'] = format_capture_time(photo['captureTime'])
        photo['uploadTime'] = format_capture_time(photo['uploadTime'])
        photo['filename'] = photoId_to_filename.get(photo['photoId']['id'])

    return render_template('list_photos_table.html', photos_list=photos_list, page_size=page_size)


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
    radius = request.args.get('radius', default=300)  # use a default value of 300 if no radius is provided

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
        uploads_directory = "uploads"
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

        if xmp_start != -1 and xmp_end != -1:
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
        if not next_page_token or len(places_info) >= 60:
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

def calculate_distance(lat1, lon1, lat2, lon2):
    # Radius of the Earth in meters
    R = 6371000
    # Convert coordinates from degrees to radians
    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)
    
    # Compute differences
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    # Haversine formula
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    # Distance in meters
    distance = R * c
    return distance



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

# Load configuration and initialize app settings
config = load_config()
client_config = get_client_config(config)

if __name__ == '__main__':
    try:
        # Initialize logging first for proper error tracking
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
        
        # Log application startup
        app.logger.info("Starting StreetView application")
        app.logger.info(f"Environment: debug={app.config['DEBUG']}")
        app.logger.info(f"Uploads directory: {app.config['UPLOAD_FOLDER']}")
        app.logger.info(f"Max upload size: {app.config['MAX_CONTENT_LENGTH']} bytes")
        
        # Start server
        port = int(os.getenv('PORT', config['app']['port']))
        app.logger.info(f"Starting server on {config['app']['host']}:{port}")
        app.run(
            host=config['app']['host'],
            port=port,
            debug=config['app']['debug']
        )
    except OSError as e:
        if e.errno == 98:  # Address already in use
            error_msg = f"Port {port} is already in use. Please specify a different port."
            app.logger.error(error_msg)
            print(error_msg)
        else:
            app.logger.error(f"Error starting server: {str(e)}")
            raise
    except Exception as e:
        app.logger.error(f"Failed to start application: {str(e)}")
        raise
