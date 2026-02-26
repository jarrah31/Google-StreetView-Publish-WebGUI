# Google StreetView Publish WebGUI

This project helps you publish and view Google StreetView photosphere/360 photos onto Google Maps using the StreetView API.

Unlike the Google Maps app (RIP StreetView App), publishing photospheres without an associated listing using this project is possible, and if you do choose a listing, it won't snap the blue dot to that location.

Features include:
- Local web server presenting a web GUI to interact with the API
- Publish photosphere photos to Google Maps
- Verify if a photo contains valid XMP photosphere metadata
- Optionally add a Listing/PlaceID to a 360 photo whilst maintaining blue dot GPS position
- View all your photospheres, showing their viewcount, publish and capture dates, and place names
- Edit existing 360 photos by changing their location and placeID
- Delete your 360 photos
- Add and edit connections between photospheres for navigating between images

You will need to (full insructions below):
- Run the application within a Docker container
- Create a Google Cloud Developer Project
- Create an API Key and OAuth 2.0 Client ID
- Add a credit card within your Google Cloud Developer project for API billing. (I don't think you will be changed because interacting with your own photos doesn't cost anything, and Google lets you spend up to $200 for free a month anyway. Don't hold me to this though!)

You can set up your Google Developer environment with a different Google account to what you use for publishing photospheres. 

## Screenshots
<img width="949" height="877" alt="Capto_Capture 2026-02-26_07-39-48_pm" src="https://github.com/user-attachments/assets/ce3674d1-3072-4c1d-87e5-c721deb57f1b" />

<img width="951" height="759" alt="Capto_Capture 2026-02-26_07-46-45_pm" src="https://github.com/user-attachments/assets/4a8a1401-0a92-43a3-bc5e-e9704a1f494b" />

<img width="1203" height="600" alt="Capto_Capture 2026-02-26_07-50-18_pm" src="https://github.com/user-attachments/assets/70acee96-151a-4779-b987-8ef989230755" />

<img width="1205" height="735" alt="Capto_Capture 2026-02-26_07-52-03_pm" src="https://github.com/user-attachments/assets/1f7e5b2d-fd26-4b6b-a589-1ee8cc33d5f2" />

<img width="630" height="696" alt="Capto_Capture 2026-02-26_07-53-49_pm" src="https://github.com/user-attachments/assets/c2777965-72fb-404c-9cc1-de3797c76bde" />

<img width="1342" height="767" alt="Capto_Capture 2025-08-15_07-15-48_pm" src="https://github.com/user-attachments/assets/c00378bd-909c-449f-b31f-afa4894e0b62" />


<img width="1519" height="1085" alt="Capto_Capture 2026-02-26_07-56-42_pm" src="https://github.com/user-attachments/assets/bcca7ce8-33eb-4637-bce8-a7e64c2cb2a5" />

<img width="1526" height="905" alt="Capto_Capture 2026-02-26_08-02-20_pm" src="https://github.com/user-attachments/assets/245413f9-2996-474a-a200-a3d5d9f0be54" />

<img width="908" height="730" alt="Capto_Capture 2026-02-26_08-03-39_pm" src="https://github.com/user-attachments/assets/5d43b2a3-1c5c-4e82-bd4f-c763b54c2125" />


![IMG_6ABF6090499C-1](https://github.com/jarrah31/Google-StreetView-Publish-WebGUI/assets/3072303/ab519b4b-2cac-4ac8-8954-1f37625c43fb)


## My Drone Photosphere Workflow
I have a DJI Mini Pro 3 and I enjoy creating aerial StreetView photos and publishing them on Google Streetview for other people to find.

I start by ensuring my drone keeps all the panorama photos as separate jpg files (J + J option). I then stitch these together using the fabulous Panorama Stitcher app (https://www.panoramastitcher.com) on my Mac Mini which does an amazing job at creating flawless panoramas with just one click of a button. This results in a much more detailed (higher megapixel) panorama compared to the built-in drone stitching.  I then touch up the image using Luminar Neo (https://skylum.com/luminar), specifically the "Accent AI" and "Shadow" enchancements. When I'm happy with the results I then view the pano in Spherical Viewer (https://apps.apple.com/gb/app/spherical-viewer/id1489700765?mt=12), before uploading to Google using my web app.

# Installation Instructions
https://github.com/jarrah31/Google-StreetView-Publish-WebGUI/wiki/Installation-Instructions 


