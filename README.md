# Google StreetView Publish WebGUI

This project helps you publish and view Google StreetView photosphere/360 photos onto Google Maps using the StreetView API.

Unlike the Google Maps app (RIP StreetView App), publishing photospheres without an associated listing is possible, and if you do choose a listing, it won't snap the blue dot to that location.

Features include:
- Local web server presenting a web GUI to interact with the API
- Publish photosphere photos to Google Maps
- Verify if a photo contains valid XMP photosphere metadata
- Optionally add a Listing/PlaceID to a 360 photo whilst maintaining blue dot GPS position
- View all your photospheres, showing their viewcount, publish and capture dates, and place names
- Edit existing 360 photos by changing their location and placeID
- Delete your 360 photos

You will need to (full insructions below):
- Run this Python script within a venv environment on your local machine
- Create a Google Cloud Developer Project
- Create an API Key and OAuth 2.0 Client ID
- Add a credit card within your Google Cloud Developer project for API billing. (I don't think you will be changed because interacting with your own photos doesn't cost anything, and Google lets you spend up to $200 for free a month anyway. Don't hold me to this though!)

You can set up your Google Developer environment with a different Google account to what you use for publishing photospheres. 

I wrote this whole project with ChatGPT's assistance! I'm a techie but not a programmer, so chatGPT helped me write all the python, HTML, and javascript code from scratch. This wouldn't have been possible without it!

## Screenshots
![image](https://github.com/jarrah31/Google-StreetView-Publish/assets/3072303/a55a3d65-23ef-4222-93cf-18d190f7077c)

![image](https://github.com/jarrah31/Google-StreetView-Publish-WebGUI/assets/3072303/510c0d05-b3dc-4cb2-9cd1-4afb3800f845)

![Image](https://github.com/jarrah31/Google-StreetView-Publish-WebGUI/assets/3072303/050548c1-bdb6-436f-a933-7b33d5b00902)

![image](https://github.com/jarrah31/Google-StreetView-Publish-WebGUI/assets/3072303/22b35b5e-c390-4e30-8e9a-16803faf268e)

![image](https://github.com/jarrah31/Google-StreetView-Publish-WebGUI/assets/3072303/4c2c7245-ac05-4793-a433-333cf3fc0398)

![IMG_6ABF6090499C-1](https://github.com/jarrah31/Google-StreetView-Publish-WebGUI/assets/3072303/ab519b4b-2cac-4ac8-8954-1f37625c43fb)

<img width="1316" alt="image" src="https://github.com/user-attachments/assets/a9dd78f4-a0a1-488e-9272-de9b4d135936">


## My Drone Photosphere Workflow
I have a DJI Mini Pro 3 and I enjoy creating aerial StreetView photos and publishing them on Google Streetview for other people to find.

I start by ensuring my drone keeps all the panorama photos as separate jpg files (J + J option). I then stitch these together using the fabulous Panorama Stitcher app (https://www.panoramastitcher.com) on my Mac Mini which does an amazing job at creating flawless panoramas with just one click of a button. This results in a much more detailed (higher megapixel) panorama compared to the built-in drone stitching.  I then touch up the image using Luminar Neo (https://skylum.com/luminar), specifically the "Accent AI" and "Shadow" enchancements. When I'm happy with the results I then view the pano in Spherical Viewer (https://apps.apple.com/gb/app/spherical-viewer/id1489700765?mt=12), before uploading to Google using my web app.

# Installation Instructions
The comprehensive installation steps for the Google StreetView Publish WebGUI are required because this is a self-hosted setup. Due to the requirement to authenticate a Google user via OAuth you can only set up the web server locally and access it from the same machine via a localhost IP (127.0.0.1). It should be possible to host this on the internet with your own domain name, but that is outside the scope of this guide. 
It covers configuring your local environment with Python and Git, cloning the project repository, and setting up a virtual environment to manage dependencies. Additionally, you need to create a Google Cloud Developer Project to access the required APIs for publishing photospheres. This involves creating API keys and OAuth 2.0 credentials, ensuring secure and authenticated interactions with Google StreetView services. The detailed steps ensure your system is correctly configured to run the web app locally.
## macOS
### Install Python and Git
Before you start, you should have [Homebrew](https://brew.sh/) installed on your macOS. If it's not installed, open a terminal window and paste the following command:

`/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`

1. **Open Terminal:** You can open a Terminal window from Applications > Utilities > Terminal.
2. **Update Homebrew:** Before you install anything with Homebrew, you should always update it to get the latest packages. You can do this with the command: `brew update`
3. **Install Python:** After updating Homebrew, you can install Python with the command: `brew install python`
4. **Verify Installation:** To check that Python was installed correctly, you can use the command: `python3 --version`
5. **Install Git:** You can install Git with the command: `brew install git`
6. **Verify Installation:** To check that Git was installed correctly, you can use the command: `git --version`
Remember to periodically update Homebrew and the packages installed through it with the command: `brew update && brew upgrade`


### Git clone the project to your local machine

1. **Open your Terminal**
2. **Navigate to Your Project Directory**: Use the `cd` command to navigate to the directory where you want to create the virtual environment. The default location of your home folder will be fine.
3. **Clone the repository:** `git clone https://github.com/jarrah31/Google-StreetView-Publish-WebGUI.git`
4. **Navigate to the project directory:** `cd Google-StreetView-Publish-WebGUI`

To update the code with a new version, simply run "git pull" from within the Google-StreetView-Publish-WebGUI folder.

### Set Up Python Virtual Environment

1. **Open your terminal**
2. **Navigate to the project directory:** `cd ~/Google-StreetView-Publish-WebGUI`
3. **Check your Python version:** `python3 --version`
   This command should return Python 3.5 or higher. If not, you'll need to install a more recent version of Python.
4. **Create a virtual environment:** `python3 -m venv streetview`
5. **Activate Virtual Environment**: To start using the virtual environment, you need to activate it. In the command prompt, type `source streetview/bin/activate`. Your command prompt should now show `(streetview)` at the beginning of the line, indicating that the virtual environment is active.
6. **Install Required Python Libraries:** `pip install requests google-auth-oauthlib Flask google-auth piexif pillow`

Remember to always activate the virtual environment whenever you're running this app. When you're done, you can leave the virtual environment with the `deactivate` command. 

## Windows

### Install Python

1. **Download Python Installer**: Go to the official Python website [here](https://www.python.org/downloads/windows/). Click on the link for the latest Python version.

2. **Run Installer**: Once the installer is downloaded, run it.

3. **Choose Install Options**: On the first page of the installer, check the box that says `Add Python.exe to PATH`, then click on `Install Now`.

4. **Wait for Installation to Complete**: The installer will display a progress bar. Once it's finished, click `Close`.

5. **Verify Installation**: Open a new command prompt (press `Win + R`, type `cmd`, then press `Enter`). In the command prompt, type `python --version`. If Python is installed correctly, this command should print the Python version number.

### Install Git

1. **Download Git Installer**: Go to the official Git website [here](https://git-scm.com/download/win) and select `Click here to download`.

2. **Run Installer**: Once the installer is downloaded, run it.

3. **Choose Install Options**: You can leave the defaults checked for most of the installation, except for `Choosing the default editor for git`. Instead, select your preferred editor from the drop-down list.

4. **Wait for Installation to Complete**: The installer will display a progress bar. Once it's finished, click `Finish`.

5. **Verify Installation**: From the Start menu, select `Git` -> `Git Cmd`. In the command prompt, type `git --version`. If Git is installed correctly, this command should print the Git version number.

### Git Clone the Project and Set Up a Python Virtual Environment (venv)

1. **Open Git Cmd**: From the Start menu, select `Git` -> `Git Cmd`.

2. **Navigate to Your Project Directory**: Use the `cd` command to navigate to the directory where you want to create the virtual environment. The default location of your home folder will be fine.

3. **Git Clone the Project**: Run this command: `git clone https://github.com/jarrah31/Google-StreetView-Publish-WebGUI.git`

4. **Navigate to the Git Repository folder**: `cd Google-StreetView-Publish-WebGUI`

5. **Create Virtual Environment**: Type `python -m venv streetview`. This creates a new virtual environment in a directory called `streetview`.

6. **Activate Virtual Environment**: To start using the virtual environment, you need to activate it. In the command prompt, type `.\streetview\Scripts\activate`. Your command prompt should now show `(streetview)` at the beginning of the line, indicating that the virtual environment is active.

7. **Install Packages**: You can now install Python packages that will only be available in this virtual environment. 
   `pip install requests google-auth-oauthlib Flask google-auth piexif pillow`

8. **Deactivate Virtual Environment**: When you're done working in the virtual environment, you can deactivate it by typing `deactivate` in the command prompt. This returns you to your regular system Python environment.



# Setting Up a Google Cloud Developer Project

1. Visit the [Google Cloud Console](https://console.cloud.google.com).

2. Click on "Create or select a project" below Welcome, then click on "New Project".

3. In the New Project window, enter a project name (like "StreetView") and optionally select a location for the project. Click "Create".

4. After the project is created, click "SELECT PROJECT".

## Enabling APIs and Setting Up API Key

1. In your project dashboard, hover over "APIs and Services" in the left-hand menu bar and click on "Enabled APIs and Services". If you can't see the menu bar, press the hamburger icon top-left (three horizontal lines) which is named the Navigation Menu.

2. Click the blue "+ ENABLE APIS AND SERVICES" link from the bar along the top.

3. Search for "Street View Publish API" and enable it.

4. Go back to the API library and enable "Places API" (not the "new" one though), and "Maps JavaScript API".

5. At this point you may need to go through a 2-step process to verify your account with a credit card and address details. It says that you won't be charged until you manually upgrade to a paid account. Once done, click "Start my free trial".

6. After filling in a short survey, you will be given your API key. Copy this somewhere safe.

7. Untick the "Enable all Google Maps APIs for this project", and leave the "Create budget alerts" option enabled. Next click "Go to Google Maps Platform"


## Setting Up OAuth 2.0 Client IDs
The "Authorized redirect URIs" set up below only works with the localhost IP (127.0.0.1) for development purposes. This is because we need to log on as the Google user that publishes the photospheres, and the only alternative is to provide your own domain name instead and host it on the internet somewhere which is outside the scope of the guide.

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

9. Within "Authorized redirect URIs" click "+ADD URI" and paste in "http://127.0.0.1:5000/oauth2callback" (without the quotes)

10. Click "Create"

11. Your client ID and client secret will be created and shown to you. Note these down as you will need them for the project. Once done, press Ok.


Now your Google Cloud Developer Project is set up with an API Key and OAuth 2.0 Client IDs, and you have a billing account for API usage.

# Setting Up config.json

(for Windows, activate venv as described in the Windows instructions, and use notepad to edit the json files) 
1. **Navigate to Your Project Directory**: `cd Google-StreetView-Publish-WebGUI`
2. **Create a new file called "config.json":** (same place where app.py is located)
   
   macOS/Linux: `nano config.json`
  
   Windows: Create a new text file using notepad.
   
   **Caution on Windows**
   If you create a text file on Windows via File Explorer, it may actually be called `config.json.txt` even if it displays `config.json`. 
   To check, find the option to show filename extensions, and correct if necessary.
    
3. Paste in the json below and replace the following text within the quotes (keeping the quotes)
    ```
    REPLACE_THIS_WITH_RANDOM_LETTERS
    YOUR_OAUTH_CLIENT ID
    YOUR_OAUTH_CLIENT_SECRET
    YOUR_API_KEY
    ```
    ```bash
    {
        "SECRET_KEY": "REPLACE_THIS_WITH_RANDOM_LETTERS",
        "PORT": 5000,
        "web": {
          "client_id": "YOUR_OAUTH_CLIENT ID",
          "client_secret": "YOUR_OAUTH_CLIENT_SECRET",
          "api_key": "YOUR_API_KEY",
          "redirect_uris": "http://127.0.0.1:{port}/oauth2callback",
          "auth_uri": "https://accounts.google.com/o/oauth2/auth",
          "token_uri": "https://accounts.google.com/o/oauth2/token"
        }
    }
    ```
 
# Running the StreetView Web App
1. **Navigate to Your Project Directory**: `cd Google-StreetView-Publish-WebGUI`
2. **Start venv**:

   macOS: `source streetview/bin/activate`
   
   Windows: `.\streetview\Scripts\activate`
   
3. **Start the app**: `python app.py`
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
5. In your browser, navigate to: `http://127.0.0.1:5000`. You should see now see the icons!
 
6. Click "View Photos". You will be redirected to "Sign in with Google"

7. Select or sign into the account you use for publishing StreetView 360 photos

8. Click "Continue" if it says Google hasn't verified this app.

9. Click "Continue" to allow access to the StreetViewApp

10. You should now be authenticated!

# Updating to the latest version 
1. **Navigate to Your Project Directory**: `cd Google-StreetView-Publish-WebGUI`
2. **Fetch the latest changes from the remote repository**: `git fetch`
3. **Pull the latest changes from the remote repository**: `git pull`
4. **Start venv again**:
   
   macOS: `source streetview/bin/activate`
   
   Windows: `.\streetview\Scripts\activate`

   5. **Start the app**: `python app.py`
