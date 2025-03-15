# EXIF Remover for Stable Diffusion WebUI
A Stable Diffusion WebUI extension to remove EXIF data, Stable Diffusion generation parameters, and steganographic watermarks from images.

In late February 2025, Stable Diffusion Forge (WebUI Forge) implemented a stealth feature that embeds generation information (infotext) into images using steganography techniques within the alpha channel, separate from visible watermarks. This extension provides a solution for users who require clean images for external uploads or personal projects, offering flexible options for privacy and content ownership control.

## Features
- **EXIF Data Removal**: Strips all EXIF metadata from images
- **Steganography Removal**: Effectively removes hidden data using multiple techniques:
  - Alpha channel processing to remove hidden data in transparency
  - Edge pixel noise addition to destroy border steganography
  - Complete metadata removal from PNG format
- **Batch Processing**: Process multiple images at once or entire folders
- **Subfolder Support**: Option to include all subfolders when processing a directory
- **Output Options**: Save to specified directory or replace files in their original location

## Install
1. Open your Stable Diffusion WebUI  
2. Go to the "Extensions" tab  
3. Click on "Install from URL"  
4. Paste the GitHub repository URL ```https://github.com/UltraK18/exif_remover.git``` 
5. Click Install  
6. Restart WebUI

## Usage
The extension adds an "EXIF Remover" tab to your WebUI with two main options:

### Process Individual Files

1. Select the "Upload Files" tab  
2. Drag and drop or select images to process  
3. (Optional) Specify an output directory in the "Output Path" field  
   - **Important:** Without a valid output path, image processing may fail.  
4. Click "Remove EXIF (Files)"  
5. Processed images will appear in the gallery with a success message

### Process Folders

1. Select the "Process Folder" tab  
2. Enter the path to the folder containing images  
3. Check "Include Subfolders" if you want to process all nested folders  
4. (Optional) Specify an output directory in the "Output Path" field  
   - **Important:** Without a valid output path, image processing may fail.  
5. Click "Remove EXIF (Folder)"  
6. Processed images will appear in the gallery with a success message

### Output Settings

- You can save your preferred output path by entering it and clicking "Save Output Path Setting".  
- The setting will persist between WebUI restarts.

## How It Works
The extension uses a multi-layered approach to remove metadata and hidden steganographic data:

1. **EXIF Metadata Removal**: Strips all standard EXIF data  
2. **Alpha Channel Processing**: Normalizes transparency to prevent data hiding in subtle alpha variations  
3. **Edge Pixel Treatment**: Adds minor noise to image borders to destroy edge-based steganography  
4. **Pixel Pattern Disruption**: Cleans specific patterns that could contain hidden data

> **Note:** Due to the alpha channel adjustments, images with transparency may be adversely affected or appear corrupted.

## Compatibility
- Works with Stable Diffusion WebUI and its forks  
- Tested with WebUI version f2.0.1v1.10.1  
- Supports PNG, JPG, JPEG, BMP, and WEBP file formats

## Privacy & Security
This extension operates entirely locally on your machine and does not send any data externally. It's specifically designed for privacy-conscious users who want to remove identifying metadata and watermarks from their AI-generated images.

## License
[MIT License](LICENSE)

## Acknowledgements
Thanks to all contributors and the Stable Diffusion community for their support and feedback.

### Developers
[@if-if-if](https://github.com/if-if-if), [@UltraK18](https://github.com/UltraK18)

## Caveats
- **Output Path Requirement**: For reliable image processing, a valid output path must be specified either in the "Output Path" field or via the "Save Output Path Setting" button.  
- **Transparency Issues**: The extension modifies the alpha channel during processing; therefore, images with transparency might be damaged or altered.
