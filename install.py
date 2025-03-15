import launch

if not launch.is_installed("piexif"):
    launch.run_pip("install piexif", "piexif")