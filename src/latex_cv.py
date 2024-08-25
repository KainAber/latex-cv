import logging
import re
import shutil
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


def create_CV() -> None:

    ########################################################
    #                   CONSTRUCT PATHS                    #
    ########################################################

    # Construct the project root directory
    project_src_folder_path = Path(__file__).resolve().parents[0]
    project_root_folder_path = Path(__file__).resolve().parents[1]

    # Construct the path to the CV config
    config_file_path = project_root_folder_path / "CV_config.yaml"

    # Construct the path to the CV config
    tex_template_path = project_src_folder_path / "CV_template.tex"

    ########################################################
    #               READ INPUT AND TEMPLATE                #
    ########################################################

    # Read CV config
    with open(config_file_path, "r") as file:
        CV_config_dict = yaml.safe_load(file)

    # Get the input and output folders
    input_folder = CV_config_dict.get("input_folder")
    output_folder = CV_config_dict.get("output_folder")

    # Construct the paths
    input_folder_path = (project_root_folder_path / input_folder).resolve()
    output_folder_path = (project_root_folder_path / output_folder).resolve()

    # Get the list of files in the input folder
    input_yaml_file_paths = [
        f for f in input_folder_path.iterdir() if f.is_file() and f.suffix == ".yaml"
    ]

    # Get the input yaml file with the latest changes
    latest_input_file_path = max(input_yaml_file_paths, key=lambda f: f.stat().st_mtime)

    # Logging the selected config
    logger.info(f"Selected config: {latest_input_file_path}")

    # Read user yaml file
    with open(latest_input_file_path, "r") as file:
        CV_dict = yaml.safe_load(file)

    # Read tex template
    with open(tex_template_path, "r") as file:
        CV_template = file.read()

    ########################################################
    #                 CREATE AN IMG FOLDER                 #
    ########################################################

    # Define a folder path for LaTeX resources
    img_output_folder_path = output_folder_path / "img"

    # Create icons folder if it does not exist already
    if not img_output_folder_path.exists():
        logger.info(f"Creating resource folder at {img_output_folder_path}")
        img_output_folder_path.mkdir()

    ########################################################
    #                  COPY PROFILE IMAGE                  #
    ########################################################

    # Construct path to profile picture
    photo_path_relative = Path(CV_dict.get("personal info").get("photo path"))
    photo_path_absolute = (input_folder / photo_path_relative).resolve()

    shutil.copy(photo_path_absolute, img_output_folder_path / photo_path_absolute.name)

    ########################################################
    #                 CREATE COLORED ICONS                 #
    ########################################################

    # Read color dict
    color_dict = CV_dict.get("colors")

    # Get left side accent color
    left_side_accent_color = color_dict.get("left side accent")

    # icon folder path
    icon_folder_path = project_src_folder_path / "icons"

    # Get the list of files in the input folder not containing an underscore
    icon_file_paths = [f for f in icon_folder_path.iterdir() if f.is_file()]

    # Iterate through each icon file path
    for icon_file_path in icon_file_paths:

        # Define new icon name
        new_icon_name = f"_{left_side_accent_color}_" + icon_file_path.name

        # Create output path
        colored_icon_folder_path = img_output_folder_path / new_icon_name

        # Generate new icon
        create_colored_icon(
            icon_file_path, colored_icon_folder_path, left_side_accent_color
        )

        # Define pattern and replacement
        pattern = str(Path("icons") / icon_file_path.name)
        replacement = str(Path("img") / new_icon_name)

        # Replace icon path in CV template
        CV_template = sub(pattern, replacement, CV_template)

    ########################################################
    #                 ADJUST COLOR PALETTE                 #
    ########################################################

    # Prepare dictionary and replace values
    for key, value in color_dict.items():

        # Prepare keys and values

        # Prepare keys by removing whitespaces
        key = key.replace(" ", "")

        # Place values inside the template

        # Define pattern and replacement
        pattern = r"\\definecolor{" + str(key) + r"}{HTML}{.*?}"
        replacement = r"\\definecolor{" + str(key) + r"}{HTML}{" + str(value) + r"}"

        # Execute replacement
        CV_template = sub(pattern, replacement, CV_template)

    ########################################################
    #          REPLACE PERSONAL INFO AND GEOMETRY          #
    ########################################################

    # Read personal info and geometry
    personal_info_geometry_dict = CV_dict.get("personal info") | CV_dict.get("geometry")

    # Prepare dictionary and replace values
    for key, value in personal_info_geometry_dict.items():

        # Prepare keys and values

        # Prepare keys
        if isinstance(key, str):
            # Remove whitespaces
            key = key.replace(" ", "")

        # Prepare string values
        if isinstance(value, str):
            # Remove trailing newlines
            value = value.strip("\n")

            # Replace newlines with LaTeX syntax
            value = value.replace("\n", "\\\\\\\\")

        # Catch None objects
        if value is None:
            value = ""

        # Adjust photo path if it exists
        if key == "photopath" and value:
            value = str(Path("img") / Path(value).name)

        # Place values inside the template

        # Define pattern and replacement
        pattern = r"\\newcommand{\\" + str(key) + r"}{.*?}"
        replacement = r"\\newcommand{\\" + str(key) + r"}{" + str(value) + r"}"

        # Execute replacement
        CV_template = sub(pattern, replacement, CV_template)

    ########################################################
    #                     ADD QUALITIES                    #
    ########################################################

    # Read list of quality sections
    quality_sections_list = CV_dict.get("qualities")

    # Resulting LaTeX string
    qualities_latex = ""

    # Loop through all quality sections
    for quality_section_idx, quality_section_dict in enumerate(quality_sections_list):

        # Read quality section name (the only key)
        quality_section_name = next(iter(quality_section_dict))

        # Add comment block
        qualities_latex += (
            "\t\t" + "%" * (1 + 5 + len(quality_section_name) + 5 + 1) + "\n"
            "\t\t" + "%" + " " * 5 + quality_section_name.upper() + " " * 5 + "%" + "\n"
            "\t\t" + "%" * (1 + 5 + len(quality_section_name) + 5 + 1) + "\n\n"
        )

        # Add section header
        qualities_latex += (
            "\t\t{\\\\large \\\\fontfamily {qbk}\\\\selectfont \\\\textbf{"
            + quality_section_name
            + "}}\n\n"
        )

        # Add quality table preamble
        qualities_latex += (
            "\t\t\\\\begin{flushleft}\n"
            "\t\t\t\\\\renewcommand{\\\\arraystretch}{1.1}\n"
            "\t\t\t\\\\begin{tabular}{ll}\n"
        )

        # Iterate through all qualities
        for quality_item in quality_section_dict.get(quality_section_name):

            # Get quality and level
            if isinstance(quality_item, dict):
                quality = next(iter(quality_item.keys()))
                level = quality_item.get(quality)
            elif isinstance(quality_item, str):
                quality = quality_item.strip("\n")
                level = None

            # Add row to table
            if level == 0 or level is None:
                qualities_latex += "\t\t\t\t\\\\ & " + quality + "\\\\\\\\\n"
            else:
                qualities_latex += (
                    "\t\t\t\t\\\\progressbar{4em}{"
                    + str(level)
                    + "} & "
                    + quality
                    + "\\\\\\\\\n"
                )

        # Close quality table
        qualities_latex += "\t\t\t\\\\end{tabular}\n" "\t\t\\\\end{flushleft}\n\n"

        # Add bigskip between sections
        if quality_section_idx != len(quality_sections_list) - 1:
            qualities_latex += "\t\t\\\\bigskip\n\n"

    # Place qualities inside the template

    # Define pattern and replacement
    pattern = r"[^\n]*%<qualities>.*?%</qualities>"
    replacement = qualities_latex

    # Execute replacement
    CV_template = sub(pattern, replacement, CV_template, flags=re.DOTALL)

    ########################################################
    #                       ADD VITA                       #
    ########################################################

    # Read list of vita sections
    vita_sections_list = CV_dict.get("vita")

    # Resulting LaTeX string
    vita_latex = ""

    # Loop through all vita sections
    for vita_section_idx, vita_section_dict in enumerate(vita_sections_list):

        # Read vita section name (the only key)
        vita_section_name = next(iter(vita_section_dict))

        # Add comment block
        vita_latex += (
            "\t\t" + "%" * (1 + 5 + len(vita_section_name) + 5 + 1) + "\n"
            "\t\t" + "%" + " " * 5 + vita_section_name.upper() + " " * 5 + "%" + "\n"
            "\t\t" + "%" * (1 + 5 + len(vita_section_name) + 5 + 1) + "\n\n"
        )

        # Add section header
        vita_latex += (
            "\t\t{\\\\LARGE \\\\color{rightsideaccent}"
            "\\\\fontfamily {qbk}\\\\selectfont \\\\textbf{"
            + vita_section_name
            + "}}\n\n"
        )
        vita_latex += "\t\t\\\\bigskip\n\n"

        # Get vita points
        vita_section_items = vita_section_dict.get(vita_section_name)

        # Iterate through all items
        for vita_item_idx, vita_item_dict in enumerate(vita_section_items):

            # Get vita item and properties
            vita_item_title = next(iter(vita_item_dict.keys()))
            vita_item_from = vita_item_dict.get(vita_item_title).get("from")
            vita_item_to = vita_item_dict.get(vita_item_title).get("to")
            vita_item_at = vita_item_dict.get(vita_item_title).get("at")
            vita_item_description = vita_item_dict.get(vita_item_title).get("doing")

            # Add vita item
            vita_latex += (
                "\t\t\\\\CVItem{"
                + str(vita_item_title)
                + "}{"
                + str(vita_item_from)
                + "}{"
                + str(vita_item_to)
                + "}{"
                + str(vita_item_at)
                + "}"
            )

            # Add description (if given) and appropriate whitespace
            if vita_item_description:

                # Go to newline without \\
                vita_latex += "\n\n"

                # Begin itemize
                vita_latex += "\t\t\\\\begin{itemize}\n"

                # Iterate through description
                for description_item in vita_item_description:
                    description_item = sub(
                        "\\n", "\\\\\\\\\\\\\\\\", description_item, log=False
                    )
                    vita_latex += "\t\t\t\\\\item{" + description_item + "}\n"

                # Close description and vita item
                vita_latex += "\t\t\\\\end{itemize}\n\n"

                # Add bigskip within section after item with description
                if vita_item_idx != len(vita_section_items) - 1:
                    vita_latex += "\t\t\\\\bigskip\n\n"

            else:

                # Add newline \\
                vita_latex += "\\\\\\\\\n\n"

        # Add padding between vita sections
        if vita_section_idx != len(vita_sections_list) - 1:
            vita_latex += "\t\t\\\\vspace{\\\\rightsidetextpadding}\n\n"

    # Place vita inside the template

    # Define pattern and replacement
    pattern = r"[^\n]*%<vita>.*?%</vita>"
    replacement = vita_latex

    # Execute replacement
    CV_template = sub(pattern, replacement, CV_template, flags=re.DOTALL)

    ########################################################
    #               UPDATE LANGUAGE SETTINGS               #
    ########################################################

    # Read latex language package
    language_arg = CV_dict.get("language", "english")

    # Define pattern and replacement
    pattern = r"\\usepackage\[english\]{babel}"
    replacement = r"\\usepackage[" + language_arg + r"]{babel}"

    # Execute replacement
    CV_template = sub(pattern, replacement, CV_template)

    ########################################################
    #                       EXPORT                         #
    ########################################################

    # Construct the tex output file path
    output_tex_file_name = "CV_" + latest_input_file_path.stem + ".tex"
    output_tex_file_path = output_folder_path / output_tex_file_name

    # Export tex
    with open(output_tex_file_path, "w") as f:
        f.write(CV_template)

    # Log the export
    logger.info(f"Exported .tex file to {output_tex_file_path}")

    ########################################################
    #                      COMPILE                         #
    ########################################################

    # Log the compilation
    logger.info(f"Compiling pdf to folder {output_folder_path}")

    # Compile the tex file
    subprocess.run(
        [
            "latexmk",
            "-quiet",
            "-pdf",
            f"-output-directory={str(output_folder_path)}",
            f"{str(output_tex_file_path)}",
        ]
    )  # nosec

    # Log the compilation
    logger.info(f"Compiled pdf to folder {output_folder_path}")

    # Log cleanup
    logger.info("Cleaning compilation directory")

    # Cleaning up auxilliary files
    subprocess.run(
        [
            "latexmk",
            "-quiet",
            "-c",
            f"-output-directory={str(output_folder_path)}",
            f"{str(output_tex_file_path)}",
        ]
    )  # nosec

    # Logging cleanup
    logger.info("Finsihed cleanup")
