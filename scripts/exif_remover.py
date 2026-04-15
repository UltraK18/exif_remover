import os
import modules.scripts as scripts
from modules import script_callbacks, shared
from modules.shared import opts
import gradio as gr
from PIL import Image, PngImagePlugin
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import time
import re


def on_ui_settings():
    section = ("exif_remover", "EXIF Remover")
    default_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    shared.opts.add_option("exif_remover_output_dir",
                          shared.OptionInfo(default_dir, "Output directory for images with removed EXIF", gr.Textbox, section=section))


def get_dated_output_dir(root_dir):
    """루트 경로에서 오늘 날짜 기반 MM\\MMDD 하위 폴더 경로를 생성하고 반환"""
    now = datetime.now()
    mm = now.strftime("%m")
    mmdd = now.strftime("%m%d")
    dated_dir = os.path.join(root_dir, mm, mmdd)
    os.makedirs(dated_dir, exist_ok=True)
    return dated_dir


def get_next_index(output_dir):
    """출력 폴더에서 ai_N.png 파일의 최대 번호를 찾아 다음 번호를 반환"""
    max_index = 0
    if os.path.exists(output_dir):
        pattern = re.compile(r'^ai_(\d+)\.png$', re.IGNORECASE)
        for filename in os.listdir(output_dir):
            match = pattern.match(filename)
            if match:
                idx = int(match.group(1))
                if idx > max_index:
                    max_index = idx
    return max_index + 1


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

    # 이미지가 edge_width의 2배보다 작으면 스킵
    if height <= edge_width * 2 or width <= edge_width * 2:
        return img

    channels = img_array.shape[2] if len(img_array.shape) > 2 else 0

    def apply_noise(region):
        noise = np.random.randint(-3, 4, region.shape).astype(np.int16)
        return np.clip(region.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    if channels > 0:
        ch_range = 3 if img.mode == 'RGBA' else channels
        for i in range(ch_range):
            img_array[:edge_width, :, i] = apply_noise(img_array[:edge_width, :, i])
            img_array[-edge_width:, :, i] = apply_noise(img_array[-edge_width:, :, i])
            img_array[edge_width:-edge_width, :edge_width, i] = apply_noise(img_array[edge_width:-edge_width, :edge_width, i])
            img_array[edge_width:-edge_width, -edge_width:, i] = apply_noise(img_array[edge_width:-edge_width, -edge_width:, i])
    else:
        img_array[:edge_width, :] = apply_noise(img_array[:edge_width, :])
        img_array[-edge_width:, :] = apply_noise(img_array[-edge_width:, :])
        img_array[edge_width:-edge_width, :edge_width] = apply_noise(img_array[edge_width:-edge_width, :edge_width])
        img_array[edge_width:-edge_width, -edge_width:] = apply_noise(img_array[edge_width:-edge_width, -edge_width:])

    return Image.fromarray(img_array)


def remove_all_metadata(image_path, output_dir, file_index):
    """단일 이미지 처리. output_dir과 file_index는 호출 시점에 확정된 값."""
    try:
        output_filename = f"ai_{file_index}.png"
        output_path = os.path.join(output_dir, output_filename)

        with Image.open(image_path) as img:
            new_img = clean_stealth_data(img)
            new_img = process_alpha_channel(new_img)
            new_img = process_edge_pixels(new_img, edge_width=5)
            empty_pnginfo = PngImagePlugin.PngInfo()
            new_img.save(output_path, "PNG", pnginfo=empty_pnginfo)

        print(f"Saved to: {output_path}")
        return output_path, True
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return str(e), False


def is_already_processed(filename):
    """ai_ 접두사 파일은 이미 처리된 것으로 판단하여 스킵"""
    return os.path.basename(filename).lower().startswith("ai_")


def resolve_output_dir(output_directory):
    """출력 경로를 확정하고 날짜 폴더를 생성하여 반환"""
    root = output_directory.strip() if output_directory and output_directory.strip() else ""
    if not root:
        root = getattr(shared.opts, 'exif_remover_output_dir', '')
    if not root:
        root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    return get_dated_output_dir(root)


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
                    label="Output Root Path (auto-creates MM\\MMDD subfolder)",
                    placeholder="Example: R:\\PC\\바탕화면\\정리\\share\\ExifRemover\\pixiv\\2026",
                    value=saved_output_dir
                )

            with gr.Column():
                output_gallery = gr.Gallery(label="Processed Images")
                output_message = gr.Markdown("Results will be displayed here.")

        with gr.Row():
            save_path_button = gr.Button("Save Output Path Setting")

        def save_output_path(path):
            if path is not None and path.strip():
                try:
                    shared.opts.exif_remover_output_dir = path.strip()
                    shared.opts.save("config.json")
                    return f"✅ Path saved: {path.strip()}"
                except Exception as e:
                    print(f"Error saving path: {e}")
                    shared.opts.exif_remover_output_dir = path.strip()
                    return f"✅ Path set for current session: {path.strip()}"
            return "❌ Please enter a valid path."

        def process_images(files, output_directory):
            if not files:
                return None, "Please upload image files.", None

            # 출력 경로 확정 (날짜 폴더 포함)
            dated_dir = resolve_output_dir(output_directory)

            # ai_ 접두사 파일 필터링
            valid_files = []
            skipped = 0
            for f in files:
                if is_already_processed(f.name):
                    skipped += 1
                else:
                    valid_files.append(f)

            if not valid_files:
                return None, "✅ All uploaded files are already processed (ai_ prefix). Nothing to do.", None

            # 기존 번호 이어붙이기
            start_index = get_next_index(dated_dir)

            # 처리 목록 생성
            tasks = []
            for i, file_obj in enumerate(valid_files):
                file_path = file_obj.name
                tasks.append((file_path, dated_dir, start_index + i))

            successful = 0
            failed = 0
            processed_images = []
            start_time = time.time()

            # ThreadPoolExecutor 사용 (multiprocessing 대신)
            if len(tasks) > 3:
                with ThreadPoolExecutor(max_workers=4) as executor:
                    futures = [executor.submit(remove_all_metadata, fp, od, idx) for fp, od, idx in tasks]
                    for future in futures:
                        result_path, success = future.result()
                        if success:
                            successful += 1
                            processed_images.append(result_path)
                        else:
                            failed += 1
            else:
                for file_path, out_dir, idx in tasks:
                    result_path, success = remove_all_metadata(file_path, out_dir, idx)
                    if success:
                        successful += 1
                        processed_images.append(result_path)
                    else:
                        failed += 1

            processing_time = time.time() - start_time
            msg = f"✅ Processed {successful} images in {processing_time:.1f}s\n📁 Saved to: `{dated_dir}`"
            if skipped > 0:
                msg += f"\n⏭️ Skipped {skipped} already-processed file(s)"
            if failed > 0:
                msg += f"\n❌ Failed: {failed}"

            return processed_images, msg, None

        def process_folder(folder_path, include_subfolders_flag, output_directory):
            if not folder_path or not os.path.exists(folder_path):
                return None, "❌ Please enter a valid folder path."

            # 출력 경로 확정 (날짜 폴더 포함)
            dated_dir = resolve_output_dir(output_directory)

            supported_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.webp')
            image_files = []
            folder_path = os.path.abspath(folder_path)

            if include_subfolders_flag:
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        if file.lower().endswith(supported_extensions):
                            image_files.append(os.path.join(root, file))
            else:
                for file in os.listdir(folder_path):
                    if file.lower().endswith(supported_extensions):
                        image_files.append(os.path.join(folder_path, file))

            # ai_ 접두사 파일 필터링
            files_to_process = [f for f in image_files if not is_already_processed(f)]
            skipped = len(image_files) - len(files_to_process)

            if not files_to_process:
                if skipped > 0:
                    return None, f"✅ All {skipped} images already processed (ai_ prefix). Nothing to do."
                return None, "❌ No image files found in the specified folder."

            # 기존 번호 이어붙이기
            start_index = get_next_index(dated_dir)

            successful = 0
            failed = 0
            processed_images = []
            start_time = time.time()

            for i, file_path in enumerate(files_to_process):
                result_path, success = remove_all_metadata(file_path, dated_dir, start_index + i)
                if success:
                    successful += 1
                    if len(processed_images) < 50:
                        processed_images.append(result_path)
                else:
                    failed += 1

            processing_time = time.time() - start_time
            msg = f"✅ Processed {successful}/{len(files_to_process)} images in {processing_time:.1f}s\n📁 Saved to: `{dated_dir}`"
            if skipped > 0:
                msg += f"\n⏭️ Skipped {skipped} already-processed file(s)"
            if failed > 0:
                msg += f"\n❌ Failed: {failed}"
            if len(processed_images) < successful and len(processed_images) > 0:
                msg += f"\n📌 Showing {len(processed_images)} of {successful} in gallery"

            return processed_images, msg

        remove_files_button.click(
            fn=process_images,
            inputs=[image_input, output_dir],
            outputs=[output_gallery, output_message, image_input]
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
