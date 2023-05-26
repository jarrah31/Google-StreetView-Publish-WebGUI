
import time
import requests
import json
import os
import tempfile
import google_auth_oauthlib.flow

from datetime import datetime
from functools import wraps
from pprint import pprint
from flask import Flask, render_template, request, redirect, jsonify, url_for, flash, redirect, session
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from math import radians, cos, sin, sqrt, atan2
from google.oauth2.credentials import Credentials

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

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

import os
import json
from google.oauth2.credentials import Credentials

def get_credentials():
    creds_file = 'creds.data'
    if not os.path.exists(creds_file):
        with open(creds_file, 'w') as f:
            # Write a default (invalid) credential data
            json.dump({
                'token': None,
                'refresh_token': None,
                'token_uri': 'https://accounts.google.com/o/oauth2/token',
                'client_id': None,
                'client_secret': None,
                'scopes': ['https://www.googleapis.com/auth/streetviewpublish']
            }, f)

    credentials = Credentials.from_authorized_user_file(
        creds_file, ['https://www.googleapis.com/auth/streetviewpublish'])

    if credentials is None or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            return None

    return credentials

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
    page_size = request.args.get('page_size', None)
    if page_size is not None:
        session['page_size'] = page_size  # Store as string
    else:
        page_size = session.get('page_size', 10) # Retrieve as string, with default value of "10"

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

    next_page_token = response.get('nextPageToken')

    return render_template('list_photos.html', photos_list=photos_list, page_size=page_size, next_page_token=next_page_token)


@app.route('/edit_photo/<photo_id>', methods=['GET'])
@token_required
def edit_photo(photo_id):
    print(f"Editing photo with ID: {photo_id}")
    # Retrieve the photo details from the Streetview API.
    credentials = get_credentials()
    response = get_photo(credentials.token, photo_id)

    page_token = session.get('page_token', None)
    page_size = session.get('page_size', None)

    # print(f"Response: {response}")
    # pretty-print the JSON response using the pprint function from the pprint module in Python.
    print("Photo details:")
    pprint(response)

    response['captureTime'] = format_capture_time(response['captureTime'])
    response['uploadTime'] = format_capture_time(response['uploadTime'])

    # passing the entire response dictionary to the render_template function
    # Render the 'edit_photo.html' template with the photo details.
    return render_template('edit_photo.html', photo=response, page_token=page_token, page_size=page_size)


@app.route('/update_photo/<photo_id>', methods=['POST'])
@token_required
def update_photo(photo_id):
    # Retrieve the photo details from the form.
    photo = {
        "pose": {
            "latLngPair": {
                "latitude": request.form.get('latitude'),
                "longitude": request.form.get('longitude')
            },
            "heading": int(float(request.form.get('heading'))) if request.form.get('heading') not in ['', None] else None,
            "pitch": int(float(request.form.get('pitch'))) if request.form.get('pitch') not in ['', None] else None,
            "roll": int(float(request.form.get('roll'))) if request.form.get('roll') not in ['', None] else None,
            "altitude": int(float(request.form.get('altitude'))) if request.form.get('altitude') not in ['', None] else None
        }
    }

    page_token = session.get('page_token', None)
    page_size = session.get('page_size', None)

    # If placeId is not empty, add it to the photo dictionary
    place_id = request.form.get('placeId')
    if place_id:
        photo["places"] = [{
            "placeId": place_id,
            "languageCode": "en"
        }]

    # Convert all fields to floats, ignoring any fields that are empty or not numeric.
    for key, value in photo["pose"].items():
        if key == "latLngPair":
            for subkey in value:
                try:
                    value[subkey] = round(float(value[subkey]), 7) if value[subkey] not in [None, ''] else None
                except ValueError:
                    pass
        else:
            try:
                photo["pose"][key] = round(float(value), 7) if value not in [None, ''] else None
            except ValueError:
                pass

    if photo["pose"]["heading"] is not None:
        if not 0 <= photo["pose"]["heading"] <= 360:
            flash("Heading must be between 0 and 360", "error")
            return redirect(url_for('edit_photo', photo_id=photo_id))

    if photo["pose"]["pitch"] is not None:
        if not -90 <= photo["pose"]["pitch"] <= 90:
            flash("Pitch must be between -90 and 90", "error")
            return redirect(url_for('edit_photo', photo_id=photo_id))

    print("Update_photo photo submission:")
    print(json.dumps(photo, indent=4))  # Add this line to print out the JSON data


    # Update the photo using the Streetview API.
    credentials = get_credentials()
    response = update_photo_api(credentials.token, photo_id, photo)

    
    # print("Update_photo Response:")
    # pprint(response)

    if response.status_code == 200:
        flash('Photo updated successfully', 'success')
        return render_template('delay_redirect.html', redirect_url=url_for('edit_photo', photo_id=photo_id), page_token=page_token, page_size=page_size)

        # return render_template('update_result.html', response=response_json)

    # If the status code is not 200, handle other possibilities
    if response.text:
        try:
            response_json = response.json()
        except json.JSONDecodeError:
            flash('Error: The server response could not be decoded.', 'error')
        else:
            # Render the update_result.html template with the response dictionary.
            return render_template('update_result.html', response=response_json)

    flash('Error: The server returned an unexpected response.', 'error')
    return redirect(url_for('edit_photo', photo_id=photo_id))

    # # Render the update_result.html template with the response dictionary.
    # return render_template('update_result.html', response=response)


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
        # print(request.form)
        # print(request.form['latitude'])
        # print(request.form['longitude'])
        credentials = get_credentials()

        # Start the upload
        upload_ref = start_upload(credentials.token)
        upload_ref_message = f"Created upload url: {upload_ref}"

        # Save the uploaded file to a temporary location on the server
        file = request.files['file']
        file_path = os.path.join(tempfile.gettempdir(), file.filename)
        file.save(file_path)

        # Upload the photo bytes to the Upload URL
        upload_status = upload_photo(credentials.token, upload_ref, file_path)
        upload_status_message = f"Upload status: {upload_status}"

        # Remove the temporary file
        os.remove(file_path)

        # Upload the metadata of the photo
        latitude = float(request.form['latitude'])
        longitude = float(request.form['longitude'])
        placeId = request.form['placeId']
        heading = "0"
        create_photo_response = create_photo(credentials.token, upload_ref, latitude, longitude, heading, placeId)
        create_photo_response_message = f"Create photo response: {create_photo_response}"

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




def list_photos(token, page_size=10, page_token=None):
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

def upload_photo(token, upload_ref, file_path):
    with open(file_path, "rb") as f:
        raw_data = f.read()
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "image/jpeg",
        "X-Goog-Upload-Protocol": "raw",
        "X-Goog-Upload-Content-Length": str(len(raw_data)),
    }
    response = requests.post(upload_ref["uploadUrl"], data=raw_data, headers=headers)
    return response.status_code

def create_photo(token, upload_ref, latitude, longitude, heading, placeId):
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
            "heading": heading,
        },
    }
    if placeId:
        body["places"] = [{"placeId": placeId}]

    response = requests.post(url, headers=headers, json=body)

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

def load_config():
    with open("config.json") as config_file:
        config = json.load(config_file)
    return config

if __name__ == '__main__':
    config = load_config()
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or config.get('SECRET_KEY')
    app.run(debug=True)
