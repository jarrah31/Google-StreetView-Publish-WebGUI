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
![Capto_Capture 2025-04-22_07-55-17_pm](https://github.com/user-attachments/assets/0006c7c6-178b-48a6-b65f-8779897d6f96)

![Capto_Capture 2025-04-22_07-58-54_pm](https://github.com/user-attachments/assets/5129a7f5-a062-4536-b847-dd6b162a0e76)

![Capto_Capture 2025-04-22_08-00-22_pm](https://github.com/user-attachments/assets/6c04bcfd-aa6b-43a4-8ac9-d99c8604379d)

![Capto_Capture 2025-04-22_08-01-09_pm](https://github.com/user-attachments/assets/5d698a9d-ac77-46e5-8177-56998cd8074b)

![Capto_Capture 2025-04-18_04-06-48_pm](https://github.com/user-attachments/assets/a4432e1d-0974-489d-86ab-fa1ca47631cc)

![Capto_Capture 2025-04-22_08-11-05_pm](https://github.com/user-attachments/assets/b56c2310-faf1-490d-8823-4f5f2ad526fe)

![Capto_Capture 2025-04-22_08-05-36_pm](https://github.com/user-attachments/assets/bbd99a57-9095-4d71-95bd-da548e02872a)

![Capto_Capture 2025-04-22_08-06-25_pm](https://github.com/user-attachments/assets/fc88185b-cfd9-488b-b3ad-61588a97d684)

![Capto_Capture 2025-02-16_07-52-05_pm](https://github.com/user-attachments/assets/37399be9-8e68-40dd-9126-97ca210e17c0)

![IMG_6ABF6090499C-1](https://github.com/jarrah31/Google-StreetView-Publish-WebGUI/assets/3072303/ab519b4b-2cac-4ac8-8954-1f37625c43fb)


## My Drone Photosphere Workflow
I have a DJI Mini Pro 3 and I enjoy creating aerial StreetView photos and publishing them on Google Streetview for other people to find.

I start by ensuring my drone keeps all the panorama photos as separate jpg files (J + J option). I then stitch these together using the fabulous Panorama Stitcher app (https://www.panoramastitcher.com) on my Mac Mini which does an amazing job at creating flawless panoramas with just one click of a button. This results in a much more detailed (higher megapixel) panorama compared to the built-in drone stitching.  I then touch up the image using Luminar Neo (https://skylum.com/luminar), specifically the "Accent AI" and "Shadow" enchancements. When I'm happy with the results I then view the pano in Spherical Viewer (https://apps.apple.com/gb/app/spherical-viewer/id1489700765?mt=12), before uploading to Google using my web app.

# Installation Instructions
https://github.com/jarrah31/Google-StreetView-Publish-WebGUI/wiki/Installation-Instructions 


