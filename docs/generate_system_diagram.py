from __future__ import annotations

from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "system-design-diagram.png"

WIDTH = 1800
HEIGHT = 1120
BG = "#F7F9FC"
INK = "#17212B"
MUTED = "#5B6875"
LINE = "#81909D"

FONT_REGULAR = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)


def text_block(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    details: str,
    accent: str,
) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=8, fill="#FFFFFF", outline="#DCE3E9", width=2)
    draw.rounded_rectangle((x1, y1, x1 + 10, y2), radius=5, fill=accent)

    title_font = font(25, bold=True)
    detail_font = font(19)
    draw.text((x1 + 28, y1 + 24), title, fill=INK, font=title_font)

    lines: list[str] = []
    for paragraph in details.split("\n"):
        lines.extend(wrap(paragraph, width=27) or [""])
    draw.multiline_text(
        (x1 + 28, y1 + 67),
        "\n".join(lines),
        fill=MUTED,
        font=detail_font,
        spacing=7,
    )


def arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: str = LINE,
    dashed: bool = False,
    width: int = 4,
) -> None:
    x1, y1 = start
    x2, y2 = end
    if dashed:
        steps = 12
        for i in range(0, steps, 2):
            a = i / steps
            b = min((i + 1) / steps, 1)
            draw.line(
                (x1 + (x2 - x1) * a, y1 + (y2 - y1) * a,
                 x1 + (x2 - x1) * b, y1 + (y2 - y1) * b),
                fill=color,
                width=width,
            )
    else:
        draw.line((x1, y1, x2, y2), fill=color, width=width)

    if abs(x2 - x1) >= abs(y2 - y1):
        direction = 1 if x2 > x1 else -1
        points = [(x2, y2), (x2 - 14 * direction, y2 - 9), (x2 - 14 * direction, y2 + 9)]
    else:
        direction = 1 if y2 > y1 else -1
        points = [(x2, y2), (x2 - 9, y2 - 14 * direction), (x2 + 9, y2 - 14 * direction)]
    draw.polygon(points, fill=color)


def label(draw: ImageDraw.ImageDraw, x: int, y: int, title: str, subtitle: str) -> None:
    draw.text((x, y), title.upper(), fill="#2D5B73", font=font(18, bold=True))
    draw.text((x, y + 29), subtitle, fill=MUTED, font=font(18))


def main() -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)

    draw.text((70, 50), "NCCI Policy Explorer", fill=INK, font=font(45, bold=True))
    draw.text(
        (70, 110),
        "System architecture for citation-grounded exploration of the CMS 2026 Medicare NCCI manual",
        fill=MUTED,
        font=font(23),
    )

    deploy_box = (1330, 45, 1730, 135)
    draw.rounded_rectangle(deploy_box, radius=8, fill="#EAF3F6", outline="#B7D0D9", width=2)
    draw.text((1353, 65), "DEPLOYMENT", fill="#2D5B73", font=font(16, bold=True))
    draw.text((1353, 91), "Private GitHub repo  ->  Render HTTPS", fill=INK, font=font(19, bold=True))

    draw.rounded_rectangle((55, 180, 1745, 505), radius=8, fill="#EEF3F7", outline="#D5DFE7", width=2)
    label(draw, 80, 205, "1. Index build", "Runs at startup when the generated index is missing")

    build_boxes = [
        ((80, 285, 365, 445), "CMS manual", "287-page source PDF\nPhysical pages retained", "#D59A24"),
        ((430, 285, 715, 445), "Extract + clean", "pypdf extraction\nHeader normalization", "#2F78A8"),
        ((780, 285, 1065, 445), "Page-aware chunks", "Sentence boundaries\nChapter + page metadata", "#4B8B72"),
        ((1130, 285, 1430, 445), "SQLite FTS5", "884 indexed passages\nBM25 search", "#6E66A8"),
        ((1495, 285, 1720, 445), "Insights", "Topics, chapters,\nand code counts", "#C8624A"),
    ]
    for box, title, details, accent in build_boxes:
        text_block(draw, box, title, details, accent)
    for left, right in zip(build_boxes, build_boxes[1:]):
        arrow(draw, (left[0][2] + 8, 365), (right[0][0] - 8, 365))

    draw.rounded_rectangle((55, 550, 1745, 935), radius=8, fill="#F1F5F2", outline="#D7E2DA", width=2)
    label(draw, 80, 575, "2. Question answering", "Runs for every user question")

    runtime_boxes = [
        ((80, 670, 325, 830), "Web interface", "Question input\nInsights + source links", "#168A8A"),
        ((380, 670, 625, 830), "Python API", "POST /api/chat\nGET insights/search", "#52616D"),
        ((680, 670, 945, 830), "Retrieve", "FTS5 + BM25\nTop 6 diverse pages", "#2F78A8"),
        ((1000, 670, 1265, 830), "GPT-5.6 Sol", "Evidence-only prompt\nLow reasoning", "#C8624A"),
        ((1320, 670, 1570, 830), "Validate", "Check citation IDs\nDetect missing sources", "#4B8B72"),
        ((1625, 670, 1720, 830), "Answer", "Text +\npage links", "#D59A24"),
    ]
    for box, title, details, accent in runtime_boxes:
        text_block(draw, box, title, details, accent)
    for left, right in zip(runtime_boxes, runtime_boxes[1:]):
        arrow(draw, (left[0][2] + 8, 750), (right[0][0] - 8, 750))

    # The stored index feeds retrieval without sitting in the request path visually.
    arrow(draw, (1280, 453), (815, 658), color="#6E66A8", dashed=True, width=3)
    draw.rounded_rectangle((680, 870, 1265, 910), radius=8, fill="#FFFFFF", outline="#B8C4CC", width=2)
    draw.text(
        (707, 880),
        "Model unavailable  ->  return ranked evidence excerpts",
        fill=MUTED,
        font=font(18, bold=True),
    )
    arrow(draw, (812, 830), (812, 868), dashed=True, width=3)
    arrow(draw, (1265, 890), (1665, 840), dashed=True, width=3)

    trust_box = (55, 975, 1745, 1075)
    draw.rounded_rectangle(trust_box, radius=8, fill="#FFF8E8", outline="#E5C77C", width=2)
    draw.text((80, 994), "TRUST BOUNDARIES", fill="#8B5E13", font=font(17, bold=True))
    draw.text(
        (80, 1026),
        "API key stays in Render secrets   |   Retrieved PDF text is treated as data   |   Every citation opens the source page",
        fill=INK,
        font=font(21, bold=True),
    )

    image.save(OUTPUT, format="PNG", optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()

