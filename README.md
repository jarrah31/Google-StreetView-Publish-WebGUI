# Google StreetView Publish

This project helps you publish and view Google StreetView photosphere/360 photos onto Google Maps using the StreetView API.

Unlike the Google Maps app (RIP StreetView App), publishing photospheres without an associated listing is possible, and if you do choose a listing, it won't snap the blue dot to that location.

Features include:
- Local web server presenting a web GUI to interact with the API
- Publish photosphere photos to Google Maps
- Verify if a photo contains valid XMP photosphere metadata
- Optionally add Listings to a 360 photo whilst maintaining blue dot GPS position
- View all your photospheres, showing their viewcount, publish and capture dates, and place names
- Edit existing 360 photos by changing their location and placeID
- Delete your 360 photos

You will need to:
- Run this Python script within a venv environment on your local machine
- Create a Google Cloud Developer Project
- Create an API Key and OAuth 2.0 Client ID
- Add your credit card for API billing. (I don't think you will be changed because interacting with your own photos doesn't cost anything, and Google lets you spend up to $200 for free a month anyway. Don't hold me to this though!)

You can set up your Google Developer environment with a different Google account to what you use for publishing photospheres. 

I wrote this whole project using ChatGPT's assistance! 

## Screenshots
![image](https://github.com/jarrah31/Google-StreetView-Publish/assets/3072303/a55a3d65-23ef-4222-93cf-18d190f7077c)

![image](https://github.com/jarrah31/Google-StreetView-Publish/assets/3072303/b3120e30-0c8d-4ec3-b75d-2cc3912beb07)

![image](https://github.com/jarrah31/Google-StreetView-Publish/assets/3072303/bef2d8bc-9042-4fad-aa73-85f5aafe01fc)

![image](https://github.com/jarrah31/Google-StreetView-Publish/assets/3072303/81b68220-6a4c-4cce-86e7-d5b0262a74c8)



## Git clone the project to your local machine

1. Open your terminal.

2. Navigate to your home folder or directory where you wish to run the project from
    ```bash
    cd ~
    ```

3. Clone the repository
    ```bash
    git clone https://github.com/jarrah31/Google-StreetView-Publish.git
    cd Google-StreetView-Publish
    ```

## Python Virtual Environment Setup Guide

This section provides instructions on how to set up a Python virtual environment (venv) in Linux/macOS.

1. Open your terminal.

2. Navigate to the project directory:
    ```bash
    cd ~/Google-StreetView-Publish
    ```

3. Check your Python version by typing:
    ```bash
    python3 --version
    ```
    This command should return Python 3.5 or higher. If not, you'll need to install a more recent version of Python.

4. To create a virtual environment, use the following command:
    ```bash
    python3 -m venv streetview
    ```

5. To activate the virtual environment, type:
    ```bash
    source streetview/bin/activate
    ```

Now, you're inside your Python virtual environment!

Remember to always activate the virtual environment whenever you're running this app. When you're done, you can leave the virtual environment with the `deactivate` command. 

## Installing Required Libraries

After setting up and activating your virtual environment, you need to install the required libraries within venv to run the project. 
```bash
pip install requests google-auth-oauthlib Flask google-auth
```

## Setting Up a Google Cloud Developer Project

1. Visit the [Google Cloud Console](https://console.cloud.google.com).

2. Click on "Create or select a project" below Welcome, then click on "New Project".

3. In the New Project window, enter a project name (like "StreetView") and optionally select a location for the project. Click "Create".

4. After the project is created, click "SELECT PROJECT".

### Enabling APIs and Setting Up API Key

1. In your project dashboard, hover over "APIs and Services" in the left-hand menu bar and click on "Enabled APIs and Services". If you can't see the menu bar, press the hamburger icon top-left (three horizontal lines) which is named the Navigation Menu.

2. Click the blue "+ ENABLE APIS AND SERVICES" link from the bar along the top.

3. Search for "Street View Publish API" and enable it.

4. Go back to the API library and enable "Places API" as well (not the "new" one though).

5. At this point you may need to go through a 2-step process to verify your account with a credit card and address details. It says that you won't be charged until you manually upgrade to a paid account. Once done, click "Start my free trial".

6. After filling in a short survey, you will be given your API key. Copy this somewhere safe.

7. Untick the "Enable all Google Maps APIs for this project", and leave the "Create budget alerts" option enabled. Next click "Go to Google Maps Platform"


### Setting Up OAuth 2.0 Client IDs

1. Navigate to the Credentials page by clicking the Navigation (hamburger) menu -> APIs and Services -> Enabled APIs and Services -> Crendentials

2. Click on "+ CREATE CREDENTIALS" from the top bar and select "OAuth client ID".

2. To create OAuth client ID, you need to configure the OAuth consent screen. Click on "CONFIGURE CONSENT SCREEN".

3. On the Consent screen, select "External" and click "Create".

4. Fill out the necessary details like App name (e.g. StreetViewApp), User support email (your gmail account), Developer contact information (just the mandatory fields). Click "Save and Continue".

5. In the (2)Scopes section, click on "Save and Continue".

7. In the (3)Test Users section, if you use another Google account for publishing 360 photos, enter that account's email address by pressing "+ Add Users". Click "Save and Continue" when done.

6. On the Summary page, click "Back to Dashboard".

7. Go back to "Credentials", click on "+ CREATE CREDENTIALS", select "OAuth client ID".

8. Select "Web application" as the Application type and give it a name such as "StreetViewOAuth"

10. Within "Authorized redirect URIs" click "+ADD URI" and paste in "http://127.0.0.1:5000/oauth2callback" (without the quotes)

11. Click "Create"

9. Your client ID and client secret will be created and shown to you. Note these down as you will need them for the project. Once done, press Ok.


Now your Google Cloud Developer Project is set up with an API Key and OAuth 2.0 Client IDs, and you have a billing account for API usage.

## Setting Up client_secrets.json and config.json

1. Within the terminal, navigate to project directory
    ```bash
    cd ~/Google-StreetView-Publish
    ```
2. Start venv if not done so already
    ```bash
    source streetview/bin/activate
    ```
3. Create a new file called "client_secrets.json" within the root of project direcotry (same place where app.py is located)
    ```bash
    nano client_secrets.json
    ```
4. Paste in the json below and replace the following text within the quotes (keeping the quotes)
    ```
    YOUR_OAUTH_CLIENT ID
    YOUR_OAUTH_CLIENT_SECRET
    YOUR_API_KEY
    ```
    ```bash
    {
        "web": {
          "client_id": "YOUR_OAUTH_CLIENT ID",
          "client_secret": "YOUR_OAUTH_CLIENT_SECRET",
          "api_key": "YOUR_API_KEY",
          "redirect_uris": "http://127.0.0.1:5000/oauth2callback",
          "auth_uri": "https://accounts.google.com/o/oauth2/auth",
          "token_uri": "https://accounts.google.com/o/oauth2/token"
        }
    }
    ```
5. Create a new file called "config.json" and paste in the following
    ```bash
    {
        "SECRET_KEY": "REPLACE_THIS_WITH_RANDOM_LETTERS"
    }
    ```
## Running the StreetView Web App
1. Within the terminal, navigate to project directory
    ```bash
    cd ~/Google-StreetView-Publish
    ```
2. Start venv if not done so already
    ```bash
    source streetview/bin/activate
    ```
3. Start the app
    ```bash
    python app.py
    ```
4. This should start the Flask web server and will look like this:
    ```
     * Serving Flask app 'app'
     * Debug mode: on
    WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
     * Running on http://127.0.0.1:5000
    Press CTRL+C to quit
     * Restarting with stat
     * Debugger is active!
     * Debugger PIN: 200-769-643
    ```
5. In your browser, navigate to: http://127.0.0.1:5000. You should see tow icons!
 
6. Click "View Photos". You will be redirected to "Sign in with Google"

7. Select or sign into the account you use for publishing StreetView 360 photos

8. Click "Continue" if it says Google hasn't verified this app.

9. Click "Continue" to allow access to the StreetViewApp

10. You should now be authenticated!
