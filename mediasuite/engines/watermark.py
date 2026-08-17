"""Recorte de barras quemadas y desenfoque localizado de marcas de agua."""

from __future__ import annotations

import tempfile
from pathlib import Path

from mediasuite.engines.ffmpeg_runner import FFmpegRunner, probe_media
from mediasuite.errors import MediaSuiteError
from mediasuite.jobs import JobContext


def extract_preview_frame(runner: FFmpegRunner, input_path: str, ctx: JobContext | None = None) -> str:
    info = probe_media(runner.ffmpeg, input_path)
    if not info["has_video"]:
        raise MediaSuiteError("El archivo no contiene video.")
    stamp = min(3.0, max(0.0, (info["duration"] or 0) * 0.1))
    tmp = Path(tempfile.gettempdir()) / "mediasuite_preview.jpg"
    runner.run(
        ["-ss", f"{stamp:.2f}", "-i", input_path, "-frames:v", "1", "-q:v", "3", str(tmp)],
        ctx=ctx,
        progress_start=0,
        progress_end=100,
        label="Extrayendo fotograma",
    )
    return str(tmp)


def apply_crop(
    runner: FFmpegRunner,
    input_path: str,
    output_path: str,
    top_pct: float,
    bottom_pct: float,
    crf: int,
    ctx: JobContext,
) -> None:
    info = probe_media(runner.ffmpeg, input_path)
    if not info["has_video"]:
        raise MediaSuiteError("El archivo no contiene video.")
    if top_pct + bottom_pct >= 95:
        raise MediaSuiteError("El recorte dejaría un video casi vacío. Reduce los porcentajes.")

    top = top_pct / 100.0
    bottom = bottom_pct / 100.0
    vf = f"crop=iw:ih*(1-{top:.4f}-{bottom:.4f}):0:ih*{top:.4f}"
    ctx.log(f"Recorte superior {top_pct:.1f}% / inferior {bottom_pct:.1f}%")
    _encode(runner, input_path, output_path, info, crf, ctx, vf=vf)


def apply_blur_mask(
    runner: FFmpegRunner,
    input_path: str,
    output_path: str,
    x: int,
    y: int,
    width: int,
    height: int,
    strength: int,
    crf: int,
    ctx: JobContext,
) -> None:
    info = probe_media(runner.ffmpeg, input_path)
    if not info["has_video"]:
        raise MediaSuiteError("El archivo no contiene video.")

    vw, vh = info["width"], info["height"]
    if vw and vh:
        if x < 0 or y < 0 or width < 8 or height < 8:
            raise MediaSuiteError("La región de desenfoque es inválida.")
        if x + width > vw or y + height > vh:
            ctx.log(f"Aviso: la región excede {vw}x{vh}. FFmpeg recortará al borde.")

    luma = max(1, min(31, int(strength)))
    fc = (
        f"[0:v]crop={int(width)}:{int(height)}:{int(x)}:{int(y)},"
        f"boxblur={luma}:{luma}[blur];[0:v][blur]overlay={int(x)}:{int(y)}"
    )
    ctx.log(f"Desenfoque {width}x{height} en ({x},{y}), fuerza {luma}")
    _encode(runner, input_path, output_path, info, crf, ctx, filter_complex=fc)


def _encode(
    runner: FFmpegRunner,
    input_path: str,
    output_path: str,
    info: dict,
    crf: int,
    ctx: JobContext,
    vf: str | None = None,
    filter_complex: str | None = None,
) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    args: list[str] = ["-i", input_path]
    if filter_complex:
        args += ["-filter_complex", filter_complex]
    elif vf:
        args += ["-vf", vf]
    args += ["-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p"]
    if info.get("has_audio"):
        args += ["-c:a", "aac", "-b:a", "128k"]
    else:
        args += ["-an"]
    args += ["-movflags", "+faststart", output_path]
    runner.run(args, duration=info.get("duration") or None, ctx=ctx, label="Procesando video")
    ctx.log(f"Exportación lista: {output_path}")
