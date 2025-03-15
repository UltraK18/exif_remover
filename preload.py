def preload(parser):
    parser.add_argument("--exif-remover-enable", action='store_true', help="EXIF Remover: Enable the extension", default=True)
    parser.add_argument("--exif-remover-output-dir", type=str, help="EXIF Remover: Output directory for processed images", default="")