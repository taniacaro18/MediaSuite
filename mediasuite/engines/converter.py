"""Conversión de contenedor y compresión CRF con FFmpeg."""

from __future__ import annotations

from pathlib import Path

from mediasuite.engines.ffmpeg_runner import FFmpegRunner, probe_media
from mediasuite.errors import FFmpegError, MediaSuiteError
from mediasuite.jobs import JobContext

FORMATS = ("mp4", "mkv", "avi", "mov", "webm")

_CODEC = {
    "mp4": ("libx264", "aac", []),
    "mkv": ("libx264", "aac", []),
    "mov": ("libx264", "aac", []),
    "avi": ("libx264", "aac", []),
    "webm": ("libvpx-vp9", "libopus", ["-b:v", "0", "-deadline", "good", "-cpu-used", "4"]),
}


def convert_video(
    runner: FFmpegRunner,
    input_path: str,
    output_path: str,
    fmt: str,
    crf: int,
    scale: str,
    ctx: JobContext,
) -> None:
    fmt = fmt.lower().lstrip(".")
    if fmt not in _CODEC:
        raise MediaSuiteError(f"Formato no soportado: {fmt}")

    info = probe_media(runner.ffmpeg, input_path)
    if not info["has_video"]:
        raise MediaSuiteError("El archivo de entrada no contiene video.")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    vcodec, acodec, extra = _CODEC[fmt]
    args: list[str] = ["-i", input_path]

    vf_parts: list[str] = []
    if scale == "1080p":
        vf_parts.append("scale=-2:1080")
    elif scale == "720p":
        vf_parts.append("scale=-2:720")
    elif scale == "480p":
        vf_parts.append("scale=-2:480")
    vf_parts.append("format=yuv420p")
    args += ["-vf", ",".join(vf_parts)]

    args += ["-c:v", vcodec, "-crf", str(int(crf)), *extra]
    if vcodec == "libx264":
        args += ["-preset", "veryfast"]

    if info.get("has_audio"):
        args += ["-c:a", acodec]
        if acodec == "aac":
            args += ["-b:a", "128k"]
        elif acodec == "libopus":
            args += ["-b:a", "96k"]
    else:
        args += ["-an"]

    if fmt == "mp4":
        args += ["-movflags", "+faststart"]
    args.append(output_path)

    ctx.log(f"Convirtiendo a {fmt.upper()}  CRF {crf}  escala {scale}…")
    try:
        runner.run(args, duration=info.get("duration") or None, ctx=ctx, label=f"Convirtiendo a {fmt.upper()}")
    except FFmpegError:
        if fmt != "webm":
            raise
        ctx.log("VP9/Opus no disponible en este FFmpeg. Reintentando con VP8 + Vorbis…")
        args = ["-i", input_path, "-vf", ",".join(vf_parts),
                "-c:v", "libvpx", "-crf", str(int(crf)), "-b:v", "0"]
        if info.get("has_audio"):
            args += ["-c:a", "libvorbis", "-q:a", "5"]
        else:
            args += ["-an"]
        args.append(output_path)
        runner.run(args, duration=info.get("duration") or None, ctx=ctx, label="Convirtiendo a WebM")

    ctx.log(f"Listo. Guardado en: {output_path}")
