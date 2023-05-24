# Google StreetView API Publish

This project helps you publish and view Google StreetView photosphere photos onto Google Maps.

Unlike the Google Maps app (RIP StreetView App), publishing photospheres without an associated listing is possible, and if you do choose a listing, it won't snap the blue dot to that location.

Features include:
- Local web server presenting a web GUI to interact with the API
- Publish photosphere photos to Google Maps
- Verify if a photo contains valid XMP photosphere metadata
- Optionally add Listings to a photosphere whilst maintaining blue dot GPS position
- View all your photospheres, showing their viewcount, publish and capture dates, and place names
- Edit existing photosphere maps by changing it's location and placeID
- Delete your photospheres

You will need to:
- Run this Python script within a venv environment on your local machine
- Create a Google Cloud Developer Project
- Create an API Key and OAuth 2.0 Client IDs
- Add your credit card for API billing. (I don't think you will be changed because interacting with your own photos doesn't cost anything, and Google lets you spend up to $200 for free a month anyway. Don't hold me to this though!)


The following instructions are a work in progress...

## Python Virtual Environment Setup Guide

This section provides instructions on how to set up a Python virtual environment (venv) on macOS and Windows.

### macOS

1. Open your terminal.

2. Navigate to the project directory:
    ```bash
    cd /path/to/your/project
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

### Windows

1. Open the Command Prompt.

2. Navigate to the project directory:
    ```cmd
    cd \path\to\your\project
    ```

3. Check your Python version by typing:
    ```cmd
    python --version
    ```
    This command should return Python 3.5 or higher. If not, you'll need to install a more recent version of Python.

4. To create a virtual environment, use the following command:
    ```cmd
    python -m venv streetview
    ```

5. To activate the virtual environment, type:
    ```cmd
    streetview\Scripts\activate
    ```

Now, you're inside your Python virtual environment!

Remember to always activate the virtual environment whenever you're running this app. When you're done, you can leave the virtual environment with the `deactivate` command. 


