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

![image](https://github.com/jarrah31/Google-StreetView-Publish/assets/3072303/a9214aba-229e-4087-a923-60741a624416)

![image](https://github.com/jarrah31/Google-StreetView-Publish/assets/3072303/bef2d8bc-9042-4fad-aa73-85f5aafe01fc)

![image](https://github.com/jarrah31/Google-StreetView-Publish/assets/3072303/c5e2ecdb-92a4-45a1-87ce-476684b247a1)

# Installation Instructions
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
6. **Install Required Python Libraries:** `pip install requests google-auth-oauthlib Flask google-auth`

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
   `pip install requests google-auth-oauthlib Flask google-auth`

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

4. Go back to the API library and enable "Places API" as well (not the "new" one though).

5. At this point you may need to go through a 2-step process to verify your account with a credit card and address details. It says that you won't be charged until you manually upgrade to a paid account. Once done, click "Start my free trial".

6. After filling in a short survey, you will be given your API key. Copy this somewhere safe.

7. Untick the "Enable all Google Maps APIs for this project", and leave the "Create budget alerts" option enabled. Next click "Go to Google Maps Platform"


## Setting Up OAuth 2.0 Client IDs

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

# Setting Up client_secrets.json and config.json

(for Windows, activate venv as described in the Windows instructions, and use notepad to edit the json files) 
1. **Navigate to Your Project Directory**: `cd Google-StreetView-Publish-WebGUI`
2. **Create a new file called "client_secrets.json":** (same place where app.py is located)
   **macOS:** `nano client_secrets.json`
   **Windows:** Create a new text file using notepad.
   **Caution on Windows**
   If you create a text file on Windows via File Explorer, it may actually be called `client_secrets.json.txt` even if it displays `client_secrets.json`. 
   To check, find the option to show filename extensions, and correct if necessary.
    
3. Paste in the json below and replace the following text within the quotes (keeping the quotes)
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
4. **Create a new file called "config.json"** and paste in the following:
    ```bash
    {
        "SECRET_KEY": "REPLACE_THIS_WITH_RANDOM_LETTERS"
    }
    ```
 
# Running the StreetView Web App
1. **Navigate to Your Project Directory**: `cd Google-StreetView-Publish-WebGUI`
2. **Start venv**:
   **macOS:** `source streetview/bin/activate`
   **Windows:** `.\streetview\Scripts\activate`
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
