import logging
import re
import subprocess  # nosec
from pathlib import Path
from typing import Any

import yaml
from PIL import Image

########################################################
#                   CONFIGURE LOGGER                   #
########################################################

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


########################################################
#                     PATHS CLASS                      #
########################################################


class Paths:

    # Construct the project root directory
    project_src_folder_path = Path(__file__).resolve().parents[0]
    project_root_folder_path = Path(__file__).resolve().parents[1]

    # Construct the path to the CV config
    config_file_path = project_root_folder_path / "CV_config.yaml"

    # icon folder path
    icon_folder_path = project_src_folder_path / "icons"

    # Read CV config
    with open(config_file_path, "r") as file:
        CV_config_dict = yaml.safe_load(file)

    # Get the input and output folders
    input_folder = CV_config_dict.get("input_folder")
    output_folder = CV_config_dict.get("output_folder")

    # Construct the paths
    input_folder_path = (project_root_folder_path / input_folder).resolve()
    output_folder_path = (project_root_folder_path / output_folder).resolve()

    # Define a folder path for LaTeX resources
    img_output_folder_path = output_folder_path / "img"

    # Create icons folder if it does not exist already
    if not img_output_folder_path.exists():
        logger.info(f"Creating resource folder at {img_output_folder_path}")
        img_output_folder_path.mkdir()


########################################################
#                  DEFINING FUNCTIONS                  #
########################################################


def sub(pattern: str, repl: str, string: str, flags: Any = 0, log: bool = True) -> str:

    # Generate the result string
    res_string, n_subs = re.subn(pattern, repl, string, flags=flags)

    # Log if no subs were performed
    if n_subs == 0 and log:
        logger.warning(
            f"No substitutions performed for pattern '{pattern}' "
            f"and replacement '{repl}'"
        )

    return res_string


def create_and_replace_colored_icons(CV_template: str, color: str) -> str:

    # Get the list of files in the input folder not containing an underscore
    icon_file_paths = [
        f for f in Paths.icon_folder_path.iterdir() if f.suffix == ".png"
    ]

    # Iterate through each icon file path
    for icon_file_path in icon_file_paths:
        # Define new icon name
        new_icon_name = f"_{color}_" + icon_file_path.name

        # Create output path
        colored_icon_folder_path = Paths.img_output_folder_path / new_icon_name

        # Generate new icon
        create_colored_icon(icon_file_path, colored_icon_folder_path, color)

        # Define pattern and replacement
        pattern = str(Path("icons") / icon_file_path.name)
        replacement = str(Path("img") / new_icon_name)

        # Replace icon path in CV template
        CV_template = sub(pattern, replacement, CV_template)

    return CV_template


def create_colored_icon(
    input_icon_path: Path, output_icon_path: Path, html_color: str
) -> None:
    # Convert HTML to RGB
    r_new, g_new, b_new = tuple(
        int(html_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)
    )

    # Load pixels
    img = Image.open(input_icon_path).convert("RGBA")

    # Load pixel data
    pixels = img.load()

    # Iterate through each pixel
    for y in range(img.height):
        for x in range(img.width):
            # Get RGBA values
            _, _, _, a = pixels[x, y]

            pixels[x, y] = (r_new, g_new, b_new, a)

    # Save the image
    img.save(output_icon_path)


def compile_tex(tex_file_path: Path) -> Path:

    tex_folder_path = Path(tex_file_path).parent

    # Log the compilation
    logger.info(f"Compiling pdf to folder {tex_folder_path}")

    # Compile the tex file
    subprocess.run(
        [
            "latexmk",
            "-quiet",
            "-pdf",
            f"-output-directory={str(tex_folder_path)}",
            f"{str(tex_file_path)}",
        ]
    )  # nosec

    # Log the compilation
    logger.info(f"Compiled pdf to folder {tex_folder_path}")

    # Log cleanup
    logger.info("Cleaning compilation directory")

    # Cleaning up auxilliary files
    subprocess.run(
        [
            "latexmk",
            "-quiet",
            "-c",
            f"-output-directory={str(tex_folder_path)}",
            f"{str(tex_file_path)}",
        ]
    )  # nosec

    # Logging cleanup
    logger.info("Finsihed cleanup")
