import os
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from loguru import logger

# ── Cores ─────────────────────────────────────────────────────────────────────
COL_WHITE        = (255, 255, 255, 255)
COL_DARK_EDGE    = (0,   0,   0)       # #000000 — bordas da área escura
COL_DARK_CENTER  = (8,   8,   8)       # #080808 — centro (preto quase puro)

# ── Dimensões da polaroid (800×1000px) ────────────────────────────────────────
PW, PH        = 800, 1000
MARGIN_SIDE   = 60
MARGIN_TOP    = 30
MARGIN_BOTTOM = 260
CIRCLE_D      = 520
CIRCLE_BLUR   = 5    # raio do gaussian blur nas bordas do círculo

# ── Layout derivado ───────────────────────────────────────────────────────────
INNER_W = PW - MARGIN_SIDE * 2          # 680px
INNER_X = MARGIN_SIDE                    # x=60

DARK_H  = PH - MARGIN_TOP - MARGIN_BOTTOM  # 710px
DARK_Y1 = MARGIN_TOP                     # y=30
DARK_Y2 = DARK_Y1 + DARK_H              # y=740

TEXT_Y1 = DARK_Y2                        # y=740
TEXT_H  = MARGIN_BOTTOM                  # 260px

CIRCLE_CX = PW // 2                     # x=400
CIRCLE_CY = DARK_Y1 + DARK_H // 2      # y=385

CANVAS_W = PW
CANVAS_H = PH
PX, PY   = 0, 0

ASSETS_DIR = Path(__file__).parent / "assets"


def _make_radial_gradient(width: int, height: int, cx: int, cy: int) -> Image.Image:
    """Gradiente radial: COL_DARK_CENTER no centro → COL_DARK_EDGE nas bordas."""
    y_idx, x_idx = np.mgrid[0:height, 0:width].astype(np.float32)

    # Distância de cada pixel ao centro
    dx = x_idx - cx
    dy = y_idx - cy
    dist = np.sqrt(dx * dx + dy * dy)

    # Normaliza pela distância ao canto mais distante
    max_dist = np.sqrt(max(cx, width - cx) ** 2 + max(cy, height - cy) ** 2)
    t = np.clip(dist / max_dist, 0.0, 1.0)

    # Curva de potência para vignette mais dramática nas bordas
    t = t ** 1.4

    c0 = np.array(COL_DARK_CENTER, dtype=np.float32)
    c1 = np.array(COL_DARK_EDGE,   dtype=np.float32)

    # Interpola e empilha canais + alpha
    rgb = (c0[np.newaxis, np.newaxis, :] * (1 - t[..., np.newaxis])
         + c1[np.newaxis, np.newaxis, :] *  t[..., np.newaxis])
    rgb = rgb.astype(np.uint8)
    alpha = np.full((height, width, 1), 255, dtype=np.uint8)
    arr = np.concatenate([rgb, alpha], axis=-1)
    return Image.fromarray(arr, "RGBA")


def _circle_crop(photo: Image.Image) -> Image.Image:
    """Corta a foto em círculo com bordas suavizadas via gaussian blur."""
    photo = photo.convert("RGBA")
    w, h = photo.size
    s = min(w, h)
    photo = photo.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2))
    photo = photo.resize((CIRCLE_D, CIRCLE_D), Image.LANCZOS)

    mask = Image.new("L", (CIRCLE_D, CIRCLE_D), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, CIRCLE_D - 1, CIRCLE_D - 1), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=CIRCLE_BLUR))

    out = Image.new("RGBA", (CIRCLE_D, CIRCLE_D), (0, 0, 0, 0))
    out.paste(photo, (0, 0), mask)
    return out


def _fit_image(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    img_w, img_h = img.size
    scale = min(max_w / img_w, max_h / img_h)
    return img.resize((round(img_w * scale), round(img_h * scale)), Image.LANCZOS)


def _paste_rgba(base: Image.Image, overlay: Image.Image, x: int, y: int) -> None:
    overlay = overlay.convert("RGBA")
    base.paste(overlay, (x, y), overlay)


def apply_polaroid_frame(
    image_path: str,
    output_path: str,
    event_name: str | None = None,
    event_date: str | None = None,
) -> str:
    # ── Canvas transparente ───────────────────────────────────────────────────
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))

    # ── Frame branco da polaroid ──────────────────────────────────────────────
    polaroid = Image.new("RGBA", (PW, PH), COL_WHITE)

    # ── Gradiente radial na área escura interna ───────────────────────────────
    cx_rel = CIRCLE_CX - INNER_X          # 340
    cy_rel = CIRCLE_CY - DARK_Y1          # 355
    gradient = _make_radial_gradient(INNER_W, DARK_H, cx_rel, cy_rel)
    polaroid.paste(gradient, (INNER_X, DARK_Y1))

    # ── Foto recortada em círculo com bordas suaves ───────────────────────────
    circular = _circle_crop(Image.open(image_path))
    cx_off = CIRCLE_CX - CIRCLE_D // 2
    cy_off = CIRCLE_CY - CIRCLE_D // 2
    polaroid.paste(circular, (cx_off, cy_off), circular)

    # ── Logos na área escura (cantos superiores) ──────────────────────────────
    LOGO_H = 90
    LOGO_M = 20

    logo_left_path  = ASSETS_DIR / "logo_nespresso.png"
    logo_right_path = ASSETS_DIR / "logo_nespresso2.png"

    if logo_left_path.exists():
        logo_l = Image.open(logo_left_path).convert("RGBA")
        logo_l = _fit_image(logo_l, INNER_W, LOGO_H)
        _paste_rgba(polaroid, logo_l, INNER_X + LOGO_M, DARK_Y1 + LOGO_M)
    else:
        logger.warning(f"Logo não encontrado: {logo_left_path}")

    if logo_right_path.exists():
        logo_r = Image.open(logo_right_path).convert("RGBA")
        logo_r = _fit_image(logo_r, INNER_W, LOGO_H)
        rx = INNER_X + INNER_W - LOGO_M - logo_r.width
        _paste_rgba(polaroid, logo_r, rx, DARK_Y1 + LOGO_M)
    else:
        logger.warning(f"Logo não encontrado: {logo_right_path}")

    # ── Imagem de texto na área branca inferior ───────────────────────────────
    TEXT_MARGIN = 20
    textos_path = ASSETS_DIR / "textos.png"

    if textos_path.exists():
        textos = Image.open(textos_path).convert("RGBA")
        max_w = round(PW * 0.80)
        max_h = TEXT_H - TEXT_MARGIN * 2
        textos = _fit_image(textos, max_w, max_h)
        tx = (PW - textos.width) // 2
        ty = TEXT_Y1 + (TEXT_H - textos.height) // 2
        _paste_rgba(polaroid, textos, tx, ty)
    else:
        logger.warning(f"Textos não encontrado: {textos_path}")

    # ── Composição final e salvar ─────────────────────────────────────────────
    canvas.paste(polaroid, (PX, PY), polaroid)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, "PNG")
    logger.info(f"Polaroid saved → {output_path}")
    return output_path
