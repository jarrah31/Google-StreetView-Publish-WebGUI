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

![Capto_Capture 2025-06-09_08-58-24_pm](https://github.com/user-attachments/assets/fa8c07e5-17e5-466b-b359-4c87e7c4c096)

![Capto_Capture 2025-06-09_09-01-24_pm](https://github.com/user-attachments/assets/a72fb8d3-3aca-4b05-81f0-240326eb9843)

![Capto_Capture 2025-06-09_09-03-08_pm](https://github.com/user-attachments/assets/a22592b1-7ef9-456a-a126-ec46283d365f)

![Capto_Capture 2025-04-22_08-01-09_pm](https://github.com/user-attachments/assets/5d698a9d-ac77-46e5-8177-56998cd8074b)


<img width="1342" height="767" alt="Capto_Capture 2025-08-15_07-15-48_pm" src="https://github.com/user-attachments/assets/c00378bd-909c-449f-b31f-afa4894e0b62" />
<img width="1325" height="980" alt="Capto_Capture 2025-08-30_10-58-54_am" src="https://github.com/user-attachments/assets/c1d7ba5e-3844-458e-b5bc-bac11f388a4c" />



<img width="1385" height="895" alt="Capto_Capture 2025-08-30_10-55-33_am" src="https://github.com/user-attachments/assets/906840c8-5123-4321-886e-b796d76a9f8c" />

![Capto_Capture 2025-04-22_08-06-25_pm](https://github.com/user-attachments/assets/fc88185b-cfd9-488b-b3ad-61588a97d684)



![IMG_6ABF6090499C-1](https://github.com/jarrah31/Google-StreetView-Publish-WebGUI/assets/3072303/ab519b4b-2cac-4ac8-8954-1f37625c43fb)


## My Drone Photosphere Workflow
I have a DJI Mini Pro 3 and I enjoy creating aerial StreetView photos and publishing them on Google Streetview for other people to find.

I start by ensuring my drone keeps all the panorama photos as separate jpg files (J + J option). I then stitch these together using the fabulous Panorama Stitcher app (https://www.panoramastitcher.com) on my Mac Mini which does an amazing job at creating flawless panoramas with just one click of a button. This results in a much more detailed (higher megapixel) panorama compared to the built-in drone stitching.  I then touch up the image using Luminar Neo (https://skylum.com/luminar), specifically the "Accent AI" and "Shadow" enchancements. When I'm happy with the results I then view the pano in Spherical Viewer (https://apps.apple.com/gb/app/spherical-viewer/id1489700765?mt=12), before uploading to Google using my web app.

# Installation Instructions
https://github.com/jarrah31/Google-StreetView-Publish-WebGUI/wiki/Installation-Instructions 


