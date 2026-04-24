from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from loguru import logger

# ── Dimensões (1200×1600px, proporção 3:4) ────────────────────────────────────
PW, PH         = 1200, 1600
MARGIN_TOP     = 30    # espaço branco acima do quadrado preto
MARGIN_SIDE    = 70    # espaço branco nas laterais
MARGIN_BOTTOM  = 60    # espaço branco abaixo da área de texto
BOTTOM_WHITE   = 300   # altura da área branca com textos
CIRCLE_D       = 820
CIRCLE_BLUR    = 6

# ── Layout derivado ───────────────────────────────────────────────────────────
INNER_X1 = MARGIN_SIDE                          # 30
INNER_X2 = PW - MARGIN_SIDE                     # 1170
INNER_W  = INNER_X2 - INNER_X1                 # 1140

BLACK_Y1 = MARGIN_TOP                           # 30
BLACK_Y2 = PH - MARGIN_BOTTOM - BOTTOM_WHITE   # 1240
BLACK_H  = BLACK_Y2 - BLACK_Y1                 # 1210

WHITE_Y1 = BLACK_Y2                             # 1240
WHITE_Y2 = PH - MARGIN_BOTTOM                   # 1540

CIRCLE_CX = PW // 2                            # 600
CIRCLE_CY = BLACK_Y1 + BLACK_H // 2           # 635

ASSETS_DIR = Path(__file__).parent / "assets"


def _circle_crop(photo: Image.Image) -> Image.Image:
    """Recorta a foto em círculo com bordas suavizadas e vignette interno."""
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

    # Vignette interno: centro transparente → bordas preto alpha 220
    size = CIRCLE_D
    center = size / 2
    y_idx, x_idx = np.ogrid[:size, :size]
    dist_norm = np.sqrt((x_idx - center) ** 2 + (y_idx - center) ** 2) / center
    vignette_start = 0.65
    vignette = np.clip((dist_norm - vignette_start) / (1.0 - vignette_start), 0.0, 1.0)
    vignette_alpha = (vignette * 220).astype(np.uint8)

    vignette_arr = np.zeros((size, size, 4), dtype=np.uint8)
    vignette_arr[:, :, 3] = vignette_alpha
    vignette_img = Image.fromarray(vignette_arr, "RGBA")

    out = Image.alpha_composite(out, vignette_img)
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
    # ── Canvas branco ─────────────────────────────────────────────────────────
    canvas = Image.new("RGBA", (PW, PH), (255, 255, 255, 255))

    # ── Retângulo preto sólido ─────────────────────────────────────────────────
    ImageDraw.Draw(canvas).rectangle(
        [INNER_X1, BLACK_Y1, INNER_X2, BLACK_Y2],
        fill=(0, 0, 0, 255),
    )

    # ── Logos nos cantos superiores do retângulo preto ────────────────────────
    LOGO_H = 130
    LOGO_M = 20

    logo_left_path  = ASSETS_DIR / "logo_nespresso.png"
    logo_right_path = ASSETS_DIR / "logo_nespresso2.png"

    if logo_left_path.exists():
        logo_l = Image.open(logo_left_path).convert("RGBA")
        logo_l = _fit_image(logo_l, INNER_W // 2, LOGO_H)
        _paste_rgba(canvas, logo_l, INNER_X1 + LOGO_M, BLACK_Y1 + LOGO_M)
    else:
        logger.warning(f"Logo não encontrado: {logo_left_path}")

    if logo_right_path.exists():
        logo_r = Image.open(logo_right_path).convert("RGBA")
        logo_r = _fit_image(logo_r, INNER_W // 2, LOGO_H)
        rx = INNER_X2 - LOGO_M - logo_r.width
        _paste_rgba(canvas, logo_r, rx, BLACK_Y1 + LOGO_M)
    else:
        logger.warning(f"Logo não encontrado: {logo_right_path}")

    # ── Foto em círculo centralizada no retângulo preto ───────────────────────
    circular = _circle_crop(Image.open(image_path))
    cx_off = CIRCLE_CX - CIRCLE_D // 2   # 190
    cy_off = CIRCLE_CY - CIRCLE_D // 2   # 280
    _paste_rgba(canvas, circular, cx_off, cy_off)

    # ── Imagem de textos na área branca inferior ──────────────────────────────
    TEXT_PAD_TOP = 30
    TEXT_MARGIN  = 16
    textos_path  = ASSETS_DIR / "textos.png"

    if textos_path.exists():
        textos = Image.open(textos_path).convert("RGBA")
        max_w  = round(PW * 0.88)
        area_h = (WHITE_Y2 - WHITE_Y1) - TEXT_PAD_TOP - TEXT_MARGIN
        textos = _fit_image(textos, max_w, area_h)
        tx = (PW - textos.width) // 2
        ty = WHITE_Y1 + TEXT_PAD_TOP + (area_h - textos.height) // 2
        _paste_rgba(canvas, textos, tx, ty)
    else:
        logger.warning(f"Textos não encontrado: {textos_path}")

    # ── Salvar ────────────────────────────────────────────────────────────────
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, "PNG")
    logger.info(f"Polaroid saved → {output_path}")
    return output_path
