import os
from PIL import Image
import glob

def make_transparent(image_path):
    # Open the image
    img = Image.open(image_path)
    # Convert to RGBA if not already
    img = img.convert('RGBA')
    
    # Get the background color from the top-left corner
    background_color = img.getpixel((0, 0))
    
    # Create a new data array
    data = img.getdata()
    new_data = []
    
    # Define threshold for color matching (to handle slight variations)
    threshold = 30
    
    def colors_match(c1, c2, threshold):
        return all(abs(a - b) <= threshold for a, b in zip(c1[:3], c2[:3]))
    
    # Process all pixels
    for item in data:
        # If the pixel matches the background color (within threshold), make it transparent
        if colors_match(item, background_color, threshold):
            new_data.append((255, 255, 255, 0))  # Transparent white
        else:
            new_data.append(item)  # Keep original color
    
    # Update image with new data
    img.putdata(new_data)
    
    # Save the modified image back to the original file
    img.save(image_path)
    print(f'Processed: {os.path.basename(image_path)}')

def process_all_images():
    # Get the assets directory path
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
    
    # Find all PNG files in assets directory and its subdirectories
    png_files = glob.glob(os.path.join(assets_dir, '**', '*.png'), recursive=True)
    
    if not png_files:
        print('No PNG files found in the assets directory!')
        return
    
    print(f'Found {len(png_files)} PNG files to process')
    
    # Process each PNG file
    for image_path in png_files:
        try:
            make_transparent(image_path)
        except Exception as e:
            print(f'Error processing {os.path.basename(image_path)}: {str(e)}')

if __name__ == '__main__':
    process_all_images()