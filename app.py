
import time
import requests
import json
import os
import tempfile
import google_auth_oauthlib.flow
import piexif
import re


from datetime import datetime
from functools import wraps
from pprint import pprint
from flask import Flask, render_template, request, redirect, jsonify, url_for, flash, redirect, session
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from math import radians, cos, sin, sqrt, atan2
from google.oauth2.credentials import Credentials
from PIL import Image


# Find the placedID by using this page:
# https://developers.google.com/maps/documentation/places/web-service/place-id

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

debug = True  # Set this to True to enable debug messages, False to disable

uploads_dir = "uploads"
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)

app = Flask(__name__)
app.secret_key = os.urandom(24)

def load_secrets(file_path="client_secrets.json"):
    with open(file_path) as f:
        return json.load(f)

secrets = load_secrets()["web"]
client_config = {
    "web": {
        "client_id": secrets["client_id"],
        "client_secret": secrets["client_secret"],
        "redirect_uris": [secrets["redirect_uris"]],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://accounts.google.com/o/oauth2/token",
    }
}
api_key = secrets["api_key"]

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

@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('index'))

@app.route('/authorize')
def authorize():
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        client_config,
        scopes=['https://www.googleapis.com/auth/streetviewpublish'],
        redirect_uri=url_for('oauth2callback', _external=True, _scheme='http')
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
    )
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    flow = InstalledAppFlow.from_client_config(
        client_config,
        scopes=['https://www.googleapis.com/auth/streetviewpublish'],
        redirect_uri=url_for('oauth2callback', _external=True, _scheme='http')
    )
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials
    save_credentials(credentials)

    flash("Account successfully authenticated.")
    return redirect(url_for('index'))

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
    return render_template('edit_photo.html', photo=response, page_token=page_token, page_size=page_size, api_key=api_key)

@app.route('/edit_connections/<photo_id>', methods=['GET'])
@token_required
def edit_connections(photo_id):
    print(f"Editing connections with ID: {photo_id}")
    # Retrieve the photo details from the Streetview API.
    credentials = get_credentials()
    response = get_photo(credentials.token, photo_id)

    page_token = session.get('page_token', None)
    page_size = session.get('page_size', None)

    # Display json result in console
    if debug:
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
    if debug:
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
    return render_template('edit_connections.html', photo=response, nearby_photos=nearby_photos, distance=distance, page_token=page_token, page_size=page_size, api_key=api_key)

@app.route('/create_connections', methods=['POST'])
@token_required
def create_connections():
    request_data = request.get_json()
    credentials = get_credentials()

    if debug:
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

        if debug:
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
    response = update_photo_api(credentials.token, photo_id, photo)
    if response.status_code == 200:
        main_message = 'Photo updated successfully'
        details = "Please refresh the page after 30 seconds to see the changes."
        flash(f'{main_message}<br><span class="flash-details">{details}</span>', 'success')

        return redirect(url_for('edit_photo', photo_id=photo_id))  
      
    try:
        response_json = response.json()
    except json.JSONDecodeError:
        flash('Error: The server response could not be decoded.', 'error')
        return redirect(url_for('edit_photo', photo_id=photo_id))

    flash('Error: The server returned an unexpected response.', 'error')
    return render_template('update_result.html', response=response_json)



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

    places_info = get_nearby_places(latitude, longitude, radius, api_key)
    return jsonify(places_info)

@app.route('/upload', methods=['GET', 'POST'])
@token_required
def upload_photosphere():
    if request.method == 'POST':
        if debug:
            print("Received POST request for uploading photosphere.")
            print("Form data:", request.form)

        credentials = get_credentials()

        # Start the upload
        upload_ref = start_upload(credentials.token)
        upload_ref_message = f"Created upload url: {upload_ref}"
        if debug:
            print(upload_ref_message)

        # Save the uploaded file to a temporary location on the server
        file = request.files['file']
        file_path = os.path.join(tempfile.gettempdir(), file.filename)
        file.save(file_path)
        if debug:
            print(f"Saved file to {file_path}")

        # Get the heading value from the form
        heading = request.form['heading']

        # Upload the photo bytes to the Upload URL
        upload_status = upload_photo(credentials.token, upload_ref, file_path, heading)
        upload_status_message = f"Upload status: {upload_status}"
        if debug:
            print(upload_status_message)

        # Remove the temporary file
        os.remove(file_path)
        if debug:
            print(f"Removed temporary file {file_path}")

        # Upload the metadata of the photo
        latitude = float(request.form['latitude'])
        longitude = float(request.form['longitude'])
        placeId = request.form['placeId']

        create_photo_response = create_photo(credentials.token, upload_ref, latitude, longitude, placeId)
        create_photo_response_message = f"Create photo response: {create_photo_response}"
        if debug:
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
    if debug:
        print("list_photos params:", params)

    response = requests.get(url, headers=headers, params=params)
    return response.json()

def get_photo(token, photo_id):
    url = f"https://streetviewpublish.googleapis.com/v1/photo/{photo_id}"
    headers = {
        "Authorization": f"Bearer {token}",
    }
    response = requests.get(url, headers=headers)
    return response.json()

def update_photo_api(token, photo_id, photo):

    # Get the updateMask based on the photo dictionary.
    updateMask = []
    for key in photo:
        if key == 'pose':
            for subkey, subvalue in photo[key].items():
                if subvalue is not None:
                    if subkey == 'latLngPair':
                        for subsubkey, subsubvalue in subvalue.items():
                            if subsubvalue is not None:
                                updateMask.append(f'pose.latLngPair')
                                break  # We only need to add 'pose.latLngPair' once
                    else:
                        updateMask.append(f'pose.{subkey}')
        elif key == 'places' and photo[key]:
            # If 'places' is not empty, add it to the updateMask
            updateMask.append('places')
    updateMask = ','.join(updateMask)
    if debug:
        print(updateMask)


    # updateMask = "places"
    # pose.latLngPair.latitude,pose.latLngPair.longitude

    # print(f"update_photo_api update mask: {updateMask}")
    # print(f"update_photo_api photo_id: {photo_id}")

    url = f"https://streetviewpublish.googleapis.com/v1/photo/{photo_id}?updateMask={updateMask}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    # print(f"Update_photo_api URL: {url}")
    response = requests.put(url, headers=headers, json=photo)
    # print(f"Update_photo_api Response status code: {response.status_code}")
    # print(f"Update_photo_api Response: {response}")
    # return response.json()
    return response

def start_upload(token):
    url = "https://streetviewpublish.googleapis.com/v1/photo:startUpload"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    response = requests.post(url, headers=headers)
    return response.json()

def add_or_update_xmp_metadata(file_path, heading):
    # Read the image
    with open(file_path, "rb") as f:
        img_data = f.read()

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

    # Check if PoseHeadingDegrees exists, if not add it
    if '<GPano:PoseHeadingDegrees>' not in xmp_data:
        xmp_data = re.sub(
            r'(<rdf:Description[^>]*>)',
            r'\1<GPano:PoseHeadingDegrees>{}</GPano:PoseHeadingDegrees>'.format(heading),
            xmp_data
        )
    else:
        xmp_data = re.sub(
            r'<GPano:PoseHeadingDegrees>.*?</GPano:PoseHeadingDegrees>',
            f'<GPano:PoseHeadingDegrees>{heading}</GPano:PoseHeadingDegrees>',
            xmp_data
        )

    # Save the image with the new XMP metadata
    temp_file_path = file_path + "_temp.jpg"
    with open(temp_file_path, "wb") as out_file:
        out_file.write(img_data[:xmp_start])
        out_file.write(xmp_data.encode('utf-8'))
        out_file.write(img_data[xmp_end:])

    return temp_file_path

def upload_photo(token, upload_ref, file_path, heading):
    # Add XMP metadata to the photo
    temp_file_path = add_or_update_xmp_metadata(file_path, heading)
    if debug:
        print(temp_file_path)

    with open(temp_file_path, "rb") as f:
        raw_data = f.read()
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "image/jpeg",
        "X-Goog-Upload-Protocol": "raw",
        "X-Goog-Upload-Content-Length": str(len(raw_data)),
    }
    response = requests.post(upload_ref["uploadUrl"], data=raw_data, headers=headers)
    return response.status_code

def create_photo(token, upload_ref, latitude, longitude, placeId):

    url = "https://streetviewpublish.googleapis.com/v1/photo"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {
        "uploadReference": {"uploadUrl": upload_ref['uploadUrl']},
        "pose": {
            "latLngPair": {
                "latitude": latitude,
                "longitude": longitude
            },
        },
    }
    if placeId:
        body["places"] = [{"placeId": placeId}]

    if debug:
        print("Sending create_photo request with body:", json.dumps(body, indent=2))

    response = requests.post(url, headers=headers, json=body)

    if debug:
        print(f"Response status code: {response.status_code}")
        print(f"Response text: {response.text}")

    # print(f"Response status code: {response.status_code}")
    # print(f"Response text: {response.text}")

    if response.status_code == 200:
        return response.json()
    else:
        return None

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

def load_config():
    with open("config.json") as config_file:
        config = json.load(config_file)
    return config

if __name__ == '__main__':
    config = load_config()
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or config.get('SECRET_KEY')
    try:
        port = int(os.getenv('PORT', config.get('PORT', 5000)))
        app.run(debug=True, port=port)
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"Port {port} is already in use. Please specify a different port.")
        else:
            raise

