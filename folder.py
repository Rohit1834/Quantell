import os 

def get_all_folders(root_folder):
    ''' Recursively get all folders and subfolders that contain images'''
    
    folders_with_images = []
    
    for root, dirs, files in os.walk(root_folder):
        #Check if current folder contains any images
        image_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff', '.tif'))]
        if image_files:
            folders_with_images.append(root)
           
    return folders_with_images

# def get_all_folders(root_folder):
#     '''Recursively get all folders and subfolders that contain images'''
#     folders_with_images = []

#     for root, dirs, files in os.walk(root_folder):
#         # Sort files alphabetically for consistent results
#         files.sort()
#         dirs.sort()

#         image_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff', '.tif'))]
#         if image_files:
#             folders_with_images.append(root)

#     return folders_with_images

a=get_all_folders("test")
print(a)