"""
Generates the eval images under eval_data/images/ from documents.py's
section descriptions — not run automatically (images are committed as
static fixtures), but kept so the eval set is reproducible/auditable
rather than being unexplained binary files. Re-run after editing
DOCUMENTS in documents.py:

    ml/.venv/bin/python -m ml.rag.ingest.experiments.eval_data.generate_images

Uses Pillow (already a project dependency, ml/rag/ingest/patient_documents.py
will need it for image preprocessing anyway) and numpy (already pinned).
"""

import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .documents import DOCUMENTS, IMAGES_DIR

random.seed(42)
np.random.seed(42)

PAGE_WIDTH, PAGE_HEIGHT = 900, 1200
MARGIN = 60

_FONT_FILES = {
    "sans": "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Regular.ttf",
    "sans_bold": "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf",
    "serif": "/usr/share/fonts/liberation-serif-fonts/LiberationSerif-Regular.ttf",
    "mono": "/usr/share/fonts/liberation-mono-fonts/LiberationMono-Regular.ttf",
}


def _font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(_FONT_FILES[kind], size)
    except OSError:
        return ImageFont.load_default()


def _draw_text_lines(draw: ImageDraw.ImageDraw, lines: list[str], x: int, y: int, font: ImageFont.FreeTypeFont,
                      line_height: int) -> int:
    """Draw each line at x, return the y position after the last line."""
    for line in lines:
        draw.text((x, y), line, fill="black", font=font)
        y += line_height
    return y


def _draw_table(draw: ImageDraw.ImageDraw, headers: list[str], rows: list[list[str]], x: int, y: int,
                 col_widths: list[int], font: ImageFont.FreeTypeFont, header_font: ImageFont.FreeTypeFont,
                 row_height: int = 34) -> int:
    """Draw a grid table (header row + data rows, ruled lines) — real table structure, not just aligned text."""
    total_width = sum(col_widths)
    table_height = row_height * (len(rows) + 1)

    for row_idx in range(len(rows) + 2):
        line_y = y + row_idx * row_height
        draw.line([(x, line_y), (x + total_width, line_y)], fill="black", width=1)
    col_x = x
    for width in [0, *col_widths]:
        col_x += width
        draw.line([(col_x, y), (col_x, y + table_height)], fill="black", width=1)

    col_x = x
    for header, width in zip(headers, col_widths):
        draw.text((col_x + 8, y + 8), header, fill="black", font=header_font)
        col_x += width
    for row_idx, row in enumerate(rows, start=1):
        col_x = x
        for cell, width in zip(row, col_widths):
            draw.text((col_x + 8, y + row_idx * row_height + 8), cell, fill="black", font=font)
            col_x += width
    return y + table_height + 20


def _draw_columns(draw: ImageDraw.ImageDraw, left: list[str], right: list[str], x: int, y: int,
                   font: ImageFont.FreeTypeFont, line_height: int, right_x_offset: int = 420) -> int:
    """Draw two parallel columns of lines (e.g. demographics), interleaved row by row."""
    for left_line, right_line in zip(left, right):
        draw.text((x, y), left_line, fill="black", font=font)
        draw.text((x + right_x_offset, y), right_line, fill="black", font=font)
        y += line_height
    return y + 16


def render_clean(doc: dict) -> Image.Image:
    """Render one document's sections onto a plain white page — simulates a direct PDF/scan."""
    img = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), "white")
    draw = ImageDraw.Draw(img)
    body_font = _font(doc["font"], 20)
    header_font = _font(f"{doc['font']}_bold" if doc["font"] == "sans" else doc["font"], 20)
    line_height = 30
    x, y = MARGIN, MARGIN

    for section in doc["sections"]:
        if section["type"] == "text":
            y = _draw_text_lines(draw, section["lines"], x, y, body_font, line_height)
        elif section["type"] == "table":
            col_count = len(section["headers"])
            col_widths = [max(140, (PAGE_WIDTH - 2 * MARGIN) // col_count)] * col_count
            y = _draw_table(draw, section["headers"], section["rows"], x, y + 10, col_widths, body_font, header_font)
        elif section["type"] == "columns":
            y = _draw_columns(draw, section["left"], section["right"], x, y + 10, body_font, line_height)
        y += 10

    return img


def degrade_to_photo(clean: Image.Image) -> Image.Image:
    """Simulate an actual phone-camera photo: perspective skew, rotation, blur, noise, vignette, JPEG.

    More aggressive than a simple rotate+blur+noise pass — a real photo
    of a printed page is rarely shot dead-on or evenly lit, so this adds a
    mild perspective warp (camera not perfectly parallel to the page) and
    a vignette (uneven lighting/shadow toward one edge) on top of the
    rotation/blur/noise/contrast degradation already in place.
    """
    width, height = clean.size

    # Perspective warp: displace each corner independently within a small
    # margin, simulating the page not being perfectly flat/parallel to
    # the camera.
    margin = int(min(width, height) * 0.035)
    src = [(0, 0), (width, 0), (width, height), (0, height)]
    dst = [(random.randint(0, margin), random.randint(0, margin)),
           (width - random.randint(0, margin), random.randint(0, margin)),
           (width - random.randint(0, margin), height - random.randint(0, margin)),
           (random.randint(0, margin), height - random.randint(0, margin))]
    coeffs = _perspective_coefficients(dst, src)
    img = clean.transform((width, height), Image.PERSPECTIVE, coeffs, fillcolor="white", resample=Image.BICUBIC)

    img = img.rotate(random.uniform(-3.5, 3.5), expand=True, fillcolor="white")
    img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.8, 1.4)))

    arr = np.array(img).astype("float32")
    arr += np.random.normal(0, 16, arr.shape)

    # Vignette: darken toward a randomly chosen corner, like uneven phone
    # camera/room lighting rather than a studio scan.
    yy, xx = np.mgrid[0:arr.shape[0], 0:arr.shape[1]]
    corner_y, corner_x = random.choice([(0, 0), (0, arr.shape[1]), (arr.shape[0], 0), (arr.shape[0], arr.shape[1])])
    dist = np.sqrt((xx - corner_x) ** 2 + (yy - corner_y) ** 2)
    vignette = 1.0 - 0.25 * (dist / dist.max())
    arr *= vignette[..., None]

    arr = arr * 0.88 + 12
    return Image.fromarray(arr.clip(0, 255).astype("uint8")).convert("RGB")


def _perspective_coefficients(src_pts, dst_pts):
    """Solve for PIL's 8 perspective transform coefficients mapping src_pts -> dst_pts."""
    matrix = []
    for (x, y), (dx, dy) in zip(src_pts, dst_pts):
        matrix.append([x, y, 1, 0, 0, 0, -dx * x, -dx * y])
        matrix.append([0, 0, 0, x, y, 1, -dy * x, -dy * y])
    a = np.array(matrix, dtype="float64")
    b = np.array([coord for point in dst_pts for coord in point], dtype="float64")
    result = np.linalg.solve(a, b)
    return result.tolist()


def main() -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    for doc in DOCUMENTS:
        clean = render_clean(doc)
        clean.save(IMAGES_DIR / f"{doc['id']}_clean.png")
        # JPEG, not PNG: real phone photos are JPEG, and JPEG's own
        # compression artifacts are part of a faithful "photo" simulation.
        degrade_to_photo(clean).save(IMAGES_DIR / f"{doc['id']}_photo.jpg", "JPEG", quality=80)
        print(f"{doc['id']}: clean + photo written")


if __name__ == "__main__":
    main()
