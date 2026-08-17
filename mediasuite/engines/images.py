"""Procesamiento por lotes de imágenes, marcas de agua e histogramas."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

from mediasuite.errors import MediaSuiteError
from mediasuite.jobs import JobContext

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
POSITIONS = {
    "Superior izquierda": "tl",
    "Superior derecha": "tr",
    "Centro": "center",
    "Inferior izquierda": "bl",
    "Inferior derecha": "br",
}


def list_images(folder: str) -> list[Path]:
    root = Path(folder)
    if not root.is_dir():
        raise MediaSuiteError("La carpeta de entrada no existe.")
    files = [p for p in sorted(root.iterdir()) if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    if not files:
        raise MediaSuiteError("No hay imágenes PNG/JPG/WEBP/BMP/TIFF en esa carpeta.")
    return files


def compute_histogram(path: str | Path) -> dict:
    raw = Image.open(path)
    fmt = raw.format or Path(path).suffix.lstrip(".").upper()
    mode = raw.mode
    image = ImageOps.exif_transpose(raw).convert("RGB")
    preview = image.copy()
    preview.thumbnail((640, 360))
    sample = image.copy()
    sample.thumbnail((900, 900))
    red, green, blue = sample.split()
    return {
        "size": image.size,
        "mode": mode,
        "format": fmt,
        "bytes": Path(path).stat().st_size,
        "preview": preview,
        "r": red.histogram(),
        "g": green.histogram(),
        "b": blue.histogram(),
    }


def process_batch(
    input_dir: str,
    output_dir: str,
    *,
    max_width: int,
    max_height: int,
    out_format: str,
    quality: int,
    watermark_text: str,
    watermark_image: str,
    position: str,
    opacity: float,
    scale_pct: float,
    ctx: JobContext,
) -> int:
    files = list_images(input_dir)
    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    stamp = None
    if watermark_image:
        stamp_path = Path(watermark_image)
        if not stamp_path.is_file():
            raise MediaSuiteError("No se encontró la imagen de marca de agua.")
        stamp = Image.open(stamp_path).convert("RGBA")

    total = len(files)
    ctx.log(f"Procesando {total} imagen(es)…")
    done = 0
    for index, src in enumerate(files, start=1):
        ctx.check_cancel()
        ctx.progress(100.0 * (index - 1) / total, f"[{index}/{total}] {src.name}")
        try:
            _process_one(
                src,
                out_root,
                max_width=max_width,
                max_height=max_height,
                out_format=out_format,
                quality=quality,
                watermark_text=watermark_text,
                stamp=stamp,
                position=position,
                opacity=opacity,
                scale_pct=scale_pct,
            )
            done += 1
        except Exception as exc:
            ctx.log(f"  Falló {src.name}: {exc}")
    ctx.progress(100, f"Listo: {done}/{total} imágenes exportadas")
    return done


def _process_one(
    src: Path,
    out_root: Path,
    *,
    max_width: int,
    max_height: int,
    out_format: str,
    quality: int,
    watermark_text: str,
    stamp: Image.Image | None,
    position: str,
    opacity: float,
    scale_pct: float,
) -> None:
    image = ImageOps.exif_transpose(Image.open(src))
    image = image.convert("RGBA")
    if max_width > 0 or max_height > 0:
        box = (
            max_width if max_width > 0 else image.width,
            max_height if max_height > 0 else image.height,
        )
        image.thumbnail(box, Image.Resampling.LANCZOS)

    if stamp is not None:
        image = _paste_stamp(image, stamp, position, opacity, scale_pct)
    if watermark_text.strip():
        image = _draw_text(image, watermark_text.strip(), position, opacity, scale_pct)

    fmt = out_format.lower()
    if fmt in ("keep", "original", ""):
        fmt = src.suffix.lstrip(".").lower()
        if fmt == "jpeg":
            fmt = "jpg"
    if fmt == "jpeg":
        fmt = "jpg"

    dest = out_root / f"{src.stem}.{fmt}"
    _save(image, dest, fmt, quality)


def _anchor(base: tuple[int, int], size: tuple[int, int], position: str, margin: int) -> tuple[int, int]:
    bw, bh = base
    w, h = size
    key = POSITIONS.get(position, "br")
    if key == "tl":
        return margin, margin
    if key == "tr":
        return bw - w - margin, margin
    if key == "center":
        return (bw - w) // 2, (bh - h) // 2
    if key == "bl":
        return margin, bh - h - margin
    return bw - w - margin, bh - h - margin


def _paste_stamp(
    image: Image.Image,
    stamp: Image.Image,
    position: str,
    opacity: float,
    scale_pct: float,
) -> Image.Image:
    overlay = stamp.copy()
    target_w = max(8, int(image.width * (scale_pct / 100.0)))
    ratio = target_w / overlay.width
    overlay = overlay.resize((target_w, max(8, int(overlay.height * ratio))), Image.Resampling.LANCZOS)
    if opacity < 0.999:
        alpha = overlay.split()[-1]
        alpha = ImageEnhance.Brightness(alpha).enhance(max(0.0, min(1.0, opacity)))
        overlay.putalpha(alpha)
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    xy = _anchor(image.size, overlay.size, position, max(8, image.width // 80))
    layer.paste(overlay, xy, overlay)
    return Image.alpha_composite(image, layer)


def _draw_text(
    image: Image.Image,
    text: str,
    position: str,
    opacity: float,
    scale_pct: float,
) -> Image.Image:
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    font_size = max(14, int(image.width * (scale_pct / 220.0)))
    font = _font(font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    xy = _anchor(image.size, (tw, th), position, max(8, image.width // 80))
    alpha = int(255 * max(0.0, min(1.0, opacity)))
    # Sombra ligera para que la firma se lea sobre fondos claros u oscuros.
    draw.text((xy[0] + 2, xy[1] + 2), text, font=font, fill=(0, 0, 0, alpha))
    draw.text(xy, text, font=font, fill=(255, 255, 255, alpha))
    return Image.alpha_composite(image, layer)


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _save(image: Image.Image, dest: Path, fmt: str, quality: int) -> None:
    quality = max(1, min(100, int(quality)))
    if fmt in {"jpg", "jpeg"}:
        rgb = Image.new("RGB", image.size, (255, 255, 255))
        rgb.paste(image, mask=image.split()[-1])
        rgb.save(dest, format="JPEG", quality=quality, optimize=True, progressive=True)
        return
    if fmt == "webp":
        image.save(dest, format="WEBP", quality=quality, method=6)
        return
    if fmt == "png":
        image.save(dest, format="PNG", optimize=True)
        return
    image.convert("RGB").save(dest)
