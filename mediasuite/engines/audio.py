"""Extracción de pistas, normalización y reducción básica de ruido."""

from __future__ import annotations

from pathlib import Path

from mediasuite.engines.ffmpeg_runner import FFmpegRunner, probe_media
from mediasuite.errors import MediaSuiteError
from mediasuite.jobs import JobContext


def extract_audio(
    runner: FFmpegRunner,
    input_path: str,
    output_path: str,
    fmt: str,
    normalize: bool,
    denoise: bool,
    denoise_db: float,
    ctx: JobContext,
) -> None:
    info = probe_media(runner.ffmpeg, input_path)
    if not info["has_audio"]:
        raise MediaSuiteError("El archivo no tiene pista de audio.")

    fmt = fmt.lower().lstrip(".")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    filters: list[str] = []
    if denoise:
        nf = max(-80.0, min(-20.0, float(denoise_db)))
        filters.append(f"afftdn=nf={nf}")
        ctx.log(f"Reducción de ruido FFT (nf={nf:.0f} dB)")
    if normalize:
        filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
        ctx.log("Normalización loudnorm (I=-16 LUFS)")

    args: list[str] = ["-i", input_path, "-vn"]
    if filters:
        args += ["-af", ",".join(filters)]

    if fmt == "mp3":
        args += ["-c:a", "libmp3lame", "-q:a", "2"]
    elif fmt == "wav":
        args += ["-c:a", "pcm_s16le"]
    else:
        raise MediaSuiteError("Formato de audio no soportado. Usa MP3 o WAV.")
    args.append(output_path)

    ctx.log(f"Extrayendo audio {fmt.upper()}…")
    try:
        runner.run(args, duration=info.get("duration") or None, ctx=ctx, label="Extrayendo y procesando audio")
    except Exception:
        if fmt != "mp3":
            raise
        ctx.log("libmp3lame no disponible. Reintentando con AAC en contenedor M4A…")
        fallback = str(Path(output_path).with_suffix(".m4a"))
        args = ["-i", input_path, "-vn"]
        if filters:
            args += ["-af", ",".join(filters)]
        args += ["-c:a", "aac", "-b:a", "192k", fallback]
        runner.run(args, duration=info.get("duration") or None, ctx=ctx, label="Extrayendo audio M4A")
        ctx.log(f"Listo. Guardado en: {fallback}")
        return

    ctx.log(f"Listo. Guardado en: {output_path}")
