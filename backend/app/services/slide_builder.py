"""
Slide Builder service for creating PPTX files from slide outlines.

This module handles the generation of PowerPoint files using python-pptx
based on the structured SlideOutline data.
"""
import logging
import os
from pathlib import Path
from typing import Optional

from pptx import Presentation
from pptx.util import Inches, Pt

from app.schemas.slide import SlideOutline, SlideData
from app.core.config import settings

logger = logging.getLogger(__name__)

# Directory for generated images
IMAGE_BASE_DIR = Path(settings.GENERATED_FILES_DIR) / "images"


def build_pptx(outline: SlideOutline, output_path: str) -> str:
    """
    Build a PPTX file from a slide outline.

    Args:
        outline: SlideOutline containing slide structure
        output_path: Full path where the PPTX file should be saved

    Returns:
        The output path of the created file

    Raises:
        Exception: If file creation fails
    """
    logger.info(f"Building PPTX with {len(outline.slides)} slides")

    # Ensure output directory exists
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create presentation
    prs = Presentation()

    # Set slide dimensions (16:9 widescreen)
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    for slide_data in outline.slides:
        if slide_data.layout == "title":
            _add_title_slide(prs, slide_data, outline.title)
        elif slide_data.layout == "section":
            _add_section_slide(prs, slide_data)
        else:
            _add_content_slide(prs, slide_data)

    # Save the presentation
    prs.save(output_path)
    logger.info(f"PPTX saved to {output_path}")

    return output_path


def _add_title_slide(prs: Presentation, slide_data: SlideData, deck_title: str) -> None:
    """Add a title slide to the presentation."""
    # Use title slide layout (index 0)
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)

    # Set title
    title_shape = slide.shapes.title
    if title_shape:
        title_shape.text = slide_data.title or deck_title

    # Set subtitle if available
    if len(slide.placeholders) > 1:
        subtitle_placeholder = slide.placeholders[1]
        if slide_data.subtitle:
            subtitle_placeholder.text = slide_data.subtitle

    # Add speaker notes if available
    if slide_data.speaker_notes:
        notes_slide = slide.notes_slide
        notes_slide.notes_text_frame.text = slide_data.speaker_notes


def _add_section_slide(prs: Presentation, slide_data: SlideData) -> None:
    """Add a section header slide to the presentation."""
    # Use section header layout (index 2) or title slide if not available
    try:
        slide_layout = prs.slide_layouts[2]
    except IndexError:
        slide_layout = prs.slide_layouts[0]

    slide = prs.slides.add_slide(slide_layout)

    # Set title
    title_shape = slide.shapes.title
    if title_shape:
        title_shape.text = slide_data.title

    # Add speaker notes if available
    if slide_data.speaker_notes:
        notes_slide = slide.notes_slide
        notes_slide.notes_text_frame.text = slide_data.speaker_notes


def _add_content_slide(prs: Presentation, slide_data: SlideData) -> None:
    """Add a content slide with bullets to the presentation."""
    # Use title and content layout (index 1)
    slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(slide_layout)

    # Set title
    title_shape = slide.shapes.title
    if title_shape:
        title_shape.text = slide_data.title

    # Check if we have an image to display
    has_image = slide_data.image_url and _get_image_path(slide_data.image_url)

    # Add bullet points
    if slide_data.bullets:
        # Find the content placeholder
        content_placeholder = None
        for shape in slide.placeholders:
            if shape.placeholder_format.idx == 1:  # Content placeholder
                content_placeholder = shape
                break

        if content_placeholder:
            text_frame = content_placeholder.text_frame
            text_frame.clear()

            for i, bullet in enumerate(slide_data.bullets):
                if i == 0:
                    p = text_frame.paragraphs[0]
                else:
                    p = text_frame.add_paragraph()

                p.text = bullet
                p.level = 0
                p.font.size = Pt(18)

            # If we have an image, resize the text placeholder to make room
            if has_image and content_placeholder:
                # Move content to the left half of the slide
                content_placeholder.left = Inches(0.5)
                content_placeholder.width = Inches(6.0)

    # Add image if available
    if has_image:
        _insert_image(slide, slide_data.image_url)

    # Add visual hint as a note if present
    notes_content = []
    if slide_data.speaker_notes:
        notes_content.append(slide_data.speaker_notes)
    if slide_data.visual_hint:
        notes_content.append(f"\n[ビジュアル指示] {slide_data.visual_hint}")

    if notes_content:
        notes_slide = slide.notes_slide
        notes_slide.notes_text_frame.text = "\n".join(notes_content)


def _get_image_path(image_url: str) -> Optional[Path]:
    """
    Get the local file path from an image URL.

    Args:
        image_url: URL in format /api/v1/assets/images/{filename}

    Returns:
        Path to the image file, or None if it doesn't exist
    """
    if not image_url:
        return None

    # Extract filename from URL
    filename = image_url.split("/")[-1]
    file_path = IMAGE_BASE_DIR / filename

    if file_path.exists():
        return file_path
    return None


def _insert_image(slide, image_url: str) -> None:
    """
    Insert an image into the slide (right side).

    Args:
        slide: The slide object to insert the image into
        image_url: URL to the image file
    """
    file_path = _get_image_path(image_url)
    if not file_path:
        logger.warning(f"Image not found: {image_url}")
        return

    try:
        # Position image on the right side of the slide
        left = Inches(6.8)
        top = Inches(1.5)
        width = Inches(6.0)

        slide.shapes.add_picture(str(file_path), left, top, width=width)
        logger.info(f"Inserted image into slide: {file_path}")
    except Exception as e:
        logger.error(f"Failed to insert image {file_path}: {e}")


def get_pptx_output_path(notebook_id: str, deck_id: str) -> str:
    """
    Generate the output path for a PPTX file.

    Args:
        notebook_id: UUID of the notebook
        deck_id: UUID of the slide deck

    Returns:
        Full path for the PPTX file
    """
    output_dir = Path(settings.GENERATED_FILES_DIR) / "slides" / str(notebook_id)
    return str(output_dir / f"{deck_id}.pptx")


def delete_pptx_file(pptx_path: str) -> bool:
    """
    Delete a PPTX file.

    Args:
        pptx_path: Path to the PPTX file

    Returns:
        True if file was deleted, False if it didn't exist
    """
    try:
        if os.path.exists(pptx_path):
            os.remove(pptx_path)
            logger.info(f"Deleted PPTX file: {pptx_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to delete PPTX file {pptx_path}: {e}")
        return False
