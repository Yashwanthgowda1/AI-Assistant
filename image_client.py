"""
image_client.py — Screenshot capture + AI vision analysis.
Uses Mistral vision (pixtral-12b) to read the screen and extract the
interview question — no Tesseract/OCR required.
"""
from __future__ import annotations
import base64, io, logging, os
from typing import Optional
from PIL import Image

logger = logging.getLogger(__name__)


def capture_screen(region=None) -> Optional[Image.Image]:
    """Grab the full screen (or a region) using PyAutoGUI."""
    try:
        import pyautogui
        return pyautogui.screenshot(region=region)
    except Exception as exc:
        logger.exception("Screenshot failed: %s", exc)
        return None


def image_to_base64(image: Image.Image) -> str:
    """Encode PIL image as base64 PNG string."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def extract_question_from_screen(image: Image.Image, api_key: str) -> str:
    """
    Send screenshot to Mistral vision model.
    Returns the interview question text found on screen,
    or falls back to a description of what is visible.
    """
    if not api_key:
        logger.warning("No Mistral API key for vision analysis")
        return ""

    b64 = image_to_base64(image)

    try:
        from mistralai.client import Mistral
    except ImportError:
        try:
            from mistralai import Mistral
        except ImportError:
            logger.error("mistralai not installed")
            return ""

    try:
        client = Mistral(api_key=api_key)
        resp = client.chat.complete(
            model="pixtral-12b-2409",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": f"data:image/png;base64,{b64}",
                        },
                        {
                            "type": "text",
                            "text": (
                                "Look at this screenshot carefully. "
                                "Extract ONLY the interview question or coding problem "
                                "that is visible on the screen. "
                                "Return just the question text, nothing else. "
                                "If there are multiple questions, return all of them. "
                                "If no clear question is visible, describe what is on the screen."
                            ),
                        },
                    ],
                }
            ],
            max_tokens=512,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.exception("Vision API failed: %s", exc)
        return f"Vision error: {exc}"


def pil_to_qpixmap(image: Image.Image):
    """Convert PIL Image → QPixmap for display in PyQt5."""
    from PyQt5.QtGui import QPixmap, QImage
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    qimg = QImage()
    qimg.loadFromData(buf.read())
    return QPixmap.fromImage(qimg)
