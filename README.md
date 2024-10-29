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
https://github.com/jarrah31/Google-StreetView-Publish-WebGUI/wiki/Installation-Instructions 


