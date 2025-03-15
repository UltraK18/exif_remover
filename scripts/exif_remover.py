import os
import modules.scripts as scripts
from modules import script_callbacks, shared
from modules.shared import opts
import gradio as gr
from PIL import Image, PngImagePlugin
import numpy as np
import multiprocessing
import time
import io

def on_ui_settings():
    section = ("exif_remover", "EXIF Remover")
    default_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    shared.opts.add_option("exif_remover_output_dir", 
                          shared.OptionInfo(default_dir, "Output directory for images with removed EXIF", gr.Textbox, section=section))

def clean_stealth_data(image):
    img_array = np.array(image)
    
    if image.mode in ('RGB', 'RGBA'):
        if img_array.shape[0] > 1:
            img_array[-1, :] = img_array[-2, :]
        if img_array.shape[1] > 1:
            img_array[:, -1] = img_array[:, -2]
            
    return Image.fromarray(img_array)

def process_alpha_channel(img):
    if img.mode != 'RGBA':
        return img
    
    r, g, b, a = img.split()
    binary_alpha = a.point(lambda x: 0 if x < 128 else 255)
    alpha_array = np.array(binary_alpha)
    alpha_array = np.clip(alpha_array + np.random.randint(-2, 3, alpha_array.shape), 0, 255).astype(np.uint8)
    binary_alpha = Image.fromarray(alpha_array)
    
    return Image.merge('RGBA', (r, g, b, binary_alpha))

def process_edge_pixels(img, edge_width=5):
    img_array = np.array(img)
    height, width = img_array.shape[:2]
    
    if img.mode == 'RGBA':
        for i in range(3):
            noise = np.random.randint(-3, 4, (edge_width, width)).astype(np.int16)
            img_array[:edge_width, :, i] = np.clip(img_array[:edge_width, :, i].astype(np.int16) + noise, 0, 255).astype(np.uint8)
            
            noise = np.random.randint(-3, 4, (edge_width, width)).astype(np.int16)
            img_array[-edge_width:, :, i] = np.clip(img_array[-edge_width:, :, i].astype(np.int16) + noise, 0, 255).astype(np.uint8)
            
            noise = np.random.randint(-3, 4, (height - 2*edge_width, edge_width)).astype(np.int16)
            img_array[edge_width:-edge_width, :edge_width, i] = np.clip(img_array[edge_width:-edge_width, :edge_width, i].astype(np.int16) + noise, 0, 255).astype(np.uint8)
            
            noise = np.random.randint(-3, 4, (height - 2*edge_width, edge_width)).astype(np.int16)
            img_array[edge_width:-edge_width, -edge_width:, i] = np.clip(img_array[edge_width:-edge_width, -edge_width:, i].astype(np.int16) + noise, 0, 255).astype(np.uint8)
    else:
        channels = img_array.shape[2] if len(img_array.shape) > 2 else 1
        
        for i in range(channels):
            if channels > 1:
                noise = np.random.randint(-3, 4, (edge_width, width)).astype(np.int16)
                img_array[:edge_width, :, i] = np.clip(img_array[:edge_width, :, i].astype(np.int16) + noise, 0, 255).astype(np.uint8)
                
                noise = np.random.randint(-3, 4, (edge_width, width)).astype(np.int16)
                img_array[-edge_width:, :, i] = np.clip(img_array[-edge_width:, :, i].astype(np.int16) + noise, 0, 255).astype(np.uint8)
                
                noise = np.random.randint(-3, 4, (height - 2*edge_width, edge_width)).astype(np.int16)
                img_array[edge_width:-edge_width, :edge_width, i] = np.clip(img_array[edge_width:-edge_width, :edge_width, i].astype(np.int16) + noise, 0, 255).astype(np.uint8)
                
                noise = np.random.randint(-3, 4, (height - 2*edge_width, edge_width)).astype(np.int16)
                img_array[edge_width:-edge_width, -edge_width:, i] = np.clip(img_array[edge_width:-edge_width, -edge_width:, i].astype(np.int16) + noise, 0, 255).astype(np.uint8)
            else:
                noise = np.random.randint(-3, 4, (edge_width, width)).astype(np.int16)
                img_array[:edge_width, :] = np.clip(img_array[:edge_width, :].astype(np.int16) + noise, 0, 255).astype(np.uint8)
                
                noise = np.random.randint(-3, 4, (edge_width, width)).astype(np.int16)
                img_array[-edge_width:, :] = np.clip(img_array[-edge_width:, :].astype(np.int16) + noise, 0, 255).astype(np.uint8)
                
                noise = np.random.randint(-3, 4, (height - 2*edge_width, edge_width)).astype(np.int16)
                img_array[edge_width:-edge_width, :edge_width] = np.clip(img_array[edge_width:-edge_width, :edge_width].astype(np.int16) + noise, 0, 255).astype(np.uint8)
                
                noise = np.random.randint(-3, 4, (height - 2*edge_width, edge_width)).astype(np.int16)
                img_array[edge_width:-edge_width, -edge_width:] = np.clip(img_array[edge_width:-edge_width, -edge_width:].astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    return Image.fromarray(img_array)

def remove_all_metadata(image_path, output_dir):
    try:
        if not output_dir or output_dir.strip() == "":
            output_dir = shared.opts.exif_remover_output_dir
        os.makedirs(output_dir, exist_ok=True)
        filename = os.path.basename(image_path)
        output_filename = f"a-{filename}"
        output_path = os.path.join(output_dir, output_filename)
        with Image.open(image_path) as img:
            new_img = clean_stealth_data(img)
            new_img = process_alpha_channel(new_img)
            new_img = process_edge_pixels(new_img, edge_width=5)
            if hasattr(new_img, 'text'):
                new_img.text.clear()
            empty_pnginfo = PngImagePlugin.PngInfo()
            new_img.save(output_path, "PNG", pnginfo=empty_pnginfo)
        print(f"Saved to: {output_path}")
        return output_path, True
    except Exception as e:
        print(f"Error: {e}")
        return str(e), False

def process_single_image(args):
    image_path, output_dir = args
    return remove_all_metadata(image_path, output_dir)

def on_ui_tabs():
    with gr.Blocks(analytics_enabled=False) as exif_remover_tab:
        with gr.Row():
            gr.Markdown("# EXIF Remover")
            gr.Markdown("Remove EXIF data, Stable Diffusion parameters, and steganography from image files and save as new files.")
        saved_output_dir = shared.opts.exif_remover_output_dir if hasattr(shared.opts, "exif_remover_output_dir") else ""
        with gr.Row():
            with gr.Column():
                with gr.Tabs() as tabs:
                    with gr.TabItem("Upload Files", id="tab_files") as tab_files:
                        image_input = gr.File(
                            label="Image File(s)",
                            file_types=["image"],
                            file_count="multiple"
                        )
                        remove_files_button = gr.Button("Remove EXIF (Files)", variant="primary")
                    with gr.TabItem("Process Folder", id="tab_folder") as tab_folder:
                        folder_input = gr.Textbox(
                            label="Image Folder Path",
                            placeholder="Example: C:/my_images",
                            info="Enter the folder path containing images to process."
                        )
                        include_subfolders = gr.Checkbox(
                            label="Include Subfolders",
                            value=True,
                            info="When checked, images in all subfolders will also be processed."
                        )
                        remove_folder_button = gr.Button("Remove EXIF (Folder)", variant="primary")
                output_dir = gr.Textbox(
                    label="Output Path (default: extension output folder)",
                    placeholder="Example: C:/exif_removed_images",
                    value=saved_output_dir
                )
            with gr.Column():
                output_gallery = gr.Gallery(label="Processed Images")
                output_message = gr.Markdown("Results will be displayed here.")
        with gr.Row():
            save_path_button = gr.Button("Save Output Path Setting")
        def save_output_path(path):
            if path is not None:
                try:
                    shared.opts.exif_remover_output_dir = path
                    shared.opts.save("config.json")
                    return f"✅ Path saved: {path}"
                except Exception as e:
                    print(f"Error saving path: {e}")
                    shared.opts.exif_remover_output_dir = path
                    return "✅ Path set for current session only"
            return "❌ Please enter a valid path."
        def get_actual_file_path(file_obj):
            temp_file_path = file_obj.name
            actual_file_path = temp_file_path
            if "gradio" in temp_file_path and "temp" in temp_file_path:
                try:
                    import tempfile
                    temp_dir = tempfile.gettempdir()
                    perm_file_path = os.path.join(temp_dir, "exif_remover_" + os.path.basename(temp_file_path))
                    import shutil
                    shutil.copy2(temp_file_path, perm_file_path)
                    actual_file_path = perm_file_path
                except Exception as e:
                    print(f"Warning: Could not copy file from Gradio temp location: {e}")
            return actual_file_path
        def process_images(files, output_directory):
            if not files:
                return None, "Please upload image files."
            processing_list = []
            for file in files:
                file_path = get_actual_file_path(file)
                processing_list.append((file_path, output_directory))
            successful = 0
            failed = 0
            processed_images = []
            start_time = time.time()
            if len(files) > 5:
                num_cores = max(1, int(multiprocessing.cpu_count() * 0.75))
                with multiprocessing.Pool(processes=num_cores) as pool:
                    for result_path, success in pool.imap_unordered(process_single_image, processing_list):
                        if success:
                            successful += 1
                            processed_images.append(result_path)
                        else:
                            failed += 1
            else:
                for file_path, out_dir in processing_list:
                    result_path, success = remove_all_metadata(file_path, out_dir)
                    if success:
                        successful += 1
                        processed_images.append(result_path)
                    else:
                        failed += 1
            processing_time = time.time() - start_time
            location = output_directory if output_directory and output_directory.strip() else shared.opts.exif_remover_output_dir
            msg = f"✅ Processed {successful} images. Saved to {location}"
            if failed > 0:
                msg += f". Failed: {failed}"
            return processed_images, msg
        def process_folder(folder_path, include_subfolders, output_directory):
            if not folder_path or not os.path.exists(folder_path):
                return None, "❌ Please enter a valid folder path."
            supported_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.webp')
            image_files = []
            folder_path = os.path.abspath(folder_path)
            if include_subfolders:
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        if file.lower().endswith(supported_extensions):
                            image_files.append(os.path.join(root, file))
            else:
                for file in os.listdir(folder_path):
                    if file.lower().endswith(supported_extensions):
                        image_files.append(os.path.join(folder_path, file))
            if not image_files:
                return None, "❌ No image files found in the specified folder."
            successful = 0
            failed = 0
            processed_images = []
            start_time = time.time()
            for file_path in image_files:
                result_path, success = remove_all_metadata(file_path, output_directory)
                if success:
                    successful += 1
                    if len(processed_images) < 50:
                        processed_images.append(result_path)
                else:
                    failed += 1
            processing_time = time.time() - start_time
            location = output_directory if output_directory and output_directory.strip() else shared.opts.exif_remover_output_dir
            msg = f"✅ Processed {successful}/{len(image_files)} images. Saved to {location}"
            if failed > 0:
                msg += f". Failed: {failed}"
            if len(processed_images) < successful and len(processed_images) > 0:
                msg += f"\nNote: Showing {len(processed_images)} of {successful} processed images"
            return processed_images, msg
        remove_files_button.click(
            fn=process_images,
            inputs=[image_input, output_dir],
            outputs=[output_gallery, output_message]
        )
        remove_folder_button.click(
            fn=process_folder,
            inputs=[folder_input, include_subfolders, output_dir],
            outputs=[output_gallery, output_message]
        )
        save_path_button.click(
            fn=save_output_path,
            inputs=[output_dir],
            outputs=[output_message]
        )
        return [(exif_remover_tab, "EXIF Remover", "exif_remover_tab")]

script_callbacks.on_ui_tabs(on_ui_tabs)
script_callbacks.on_ui_settings(on_ui_settings)
