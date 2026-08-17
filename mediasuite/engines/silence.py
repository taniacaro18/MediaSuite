"""Recorte de silencios por streaming de audio (sin cargar el video en RAM)."""

from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path

from mediasuite.engines.ffmpeg_runner import FFmpegRunner, format_seconds, probe_media
from mediasuite.errors import MediaSuiteError
from mediasuite.jobs import JobContext

SILENCE_START_RE = re.compile(r"silence_start:\s*([0-9.]+)")
SILENCE_END_RE = re.compile(r"silence_end:\s*([0-9.]+)")


def detect_silences(
    runner: FFmpegRunner,
    input_path: str,
    noise_db: float,
    min_duration: float,
    ctx: JobContext,
    progress_start: float = 0.0,
    progress_end: float = 100.0,
) -> tuple[list[tuple[float, float]], dict]:
    info = probe_media(runner.ffmpeg, input_path)
    if not info["has_audio"]:
        raise MediaSuiteError("El archivo no tiene pista de audio para analizar silencios.")
    duration = info["duration"] or 0.0
    if duration <= 0:
        raise MediaSuiteError("No se pudo leer la duración del video.")

    starts: list[float] = []
    silences: list[tuple[float, float]] = []

    def on_line(line: str) -> None:
        start = SILENCE_START_RE.search(line)
        if start:
            starts.append(float(start.group(1)))
            return
        end = SILENCE_END_RE.search(line)
        if end and starts:
            silences.append((starts.pop(0), float(end.group(1))))

    ctx.log(
        f"Analizando audio ({format_seconds(duration)}) a {noise_db:.0f} dB, "
        f"mínimo {min_duration:.2f}s…"
    )
    af = (
        f"aformat=sample_rates=16000:channel_layouts=mono,"
        f"silencedetect=noise={noise_db}dB:d={min_duration}"
    )
    runner.run(
        ["-i", input_path, "-vn", "-sn", "-dn", "-af", af, "-f", "null", "-"],
        duration=duration,
        ctx=ctx,
        on_stderr_line=on_line,
        progress_start=progress_start,
        progress_end=progress_end,
        collect_stderr=True,
        label="Analizando silencios",
    )

    if starts:
        silences.append((starts[0], duration))
    silences.sort()
    return silences, info


def keep_intervals(
    duration: float,
    silences: list[tuple[float, float]],
    margin: float,
) -> list[tuple[float, float]]:
    """Invierte silencios a segmentos a conservar, dejando ``margin`` s de cola."""
    keeps: list[list[float]] = []
    cursor = 0.0
    for start, end in silences:
        if start > cursor + 0.01:
            keeps.append([cursor, start])
        cursor = max(cursor, end)
    if cursor < duration - 0.01:
        keeps.append([cursor, duration])

    expanded: list[list[float]] = []
    for start, end in keeps:
        expanded.append([max(0.0, start - margin), min(duration, end + margin)])

    if not expanded:
        return []

    merged: list[list[float]] = [expanded[0]]
    for start, end in expanded[1:]:
        if start <= merged[-1][1] + 0.01:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    return [(a, b) for a, b in merged if b - a >= 0.05]


def summarize_cut(duration: float, keeps: list[tuple[float, float]], silences: list[tuple[float, float]]) -> dict:
    keep_time = sum(b - a for a, b in keeps)
    silence_time = sum(b - a for a, b in silences)
    return {
        "duration": duration,
        "silence_count": len(silences),
        "keep_count": len(keeps),
        "keep_time": keep_time,
        "removed_time": max(0.0, duration - keep_time),
        "raw_silence_time": silence_time,
    }


def export_without_silences(
    runner: FFmpegRunner,
    input_path: str,
    output_path: str,
    keeps: list[tuple[float, float]],
    info: dict,
    crf: int,
    ctx: JobContext,
    progress_start: float = 0.0,
    progress_end: float = 100.0,
) -> None:
    if not keeps:
        raise MediaSuiteError("No quedaron segmentos con voz. Baja el umbral o el margen.")

    duration = info.get("duration") or 0.0
    keep_time = sum(b - a for a, b in keeps)
    if keep_time >= duration - 0.05:
        ctx.log("No hay silencios recortables; se reexporta el archivo completo sin marcas de agua.")
        _reencode(runner, input_path, output_path, info, crf, duration, ctx, progress_start, progress_end)
        return

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    expr = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in keeps)

    if len(expr) < 5500:
        ctx.log(f"Exportando {len(keeps)} segmentos en un solo paso ({format_seconds(keep_time)})…")
        args = ["-i", input_path, "-vf", f"select='{expr}',setpts=N/FRAME_RATE/TB"]
        if info.get("has_audio"):
            args += ["-af", f"aselect='{expr}',asetpts=N/SR/TB", "-c:a", "aac", "-b:a", "128k"]
        else:
            args += ["-an"]
        args += [
            "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", output_path,
        ]
        runner.run(
            args, duration=keep_time, ctx=ctx,
            progress_start=progress_start, progress_end=progress_end, label="Exportando recorte",
        )
        ctx.log(f"Exportación lista: {output_path}")
        return

    ctx.log(
        f"Muchos cortes ({len(keeps)}). Se procesan segmentos en disco temporal "
        "para no saturar RAM ni la línea de comandos."
    )
    _export_by_segments(runner, input_path, output_path, keeps, info, crf, ctx, progress_start, progress_end)


def _reencode(
    runner: FFmpegRunner,
    input_path: str,
    output_path: str,
    info: dict,
    crf: int,
    duration: float,
    ctx: JobContext,
    progress_start: float = 0.0,
    progress_end: float = 100.0,
) -> None:
    args = [
        "-i", input_path,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    ]
    if info.get("has_audio"):
        args += ["-c:a", "aac", "-b:a", "128k"]
    else:
        args += ["-an"]
    args.append(output_path)
    runner.run(
        args, duration=duration or None, ctx=ctx,
        progress_start=progress_start, progress_end=progress_end, label="Reexportando video",
    )


def _export_by_segments(
    runner: FFmpegRunner,
    input_path: str,
    output_path: str,
    keeps: list[tuple[float, float]],
    info: dict,
    crf: int,
    ctx: JobContext,
    progress_start: float = 0.0,
    progress_end: float = 100.0,
) -> None:
    tmp = Path(tempfile.mkdtemp(prefix="mediasuite_silence_"))
    try:
        total = sum(b - a for a, b in keeps) or 1.0
        done = 0.0
        list_lines: list[str] = []
        n = len(keeps)
        span = progress_end - progress_start
        for i, (start, end) in enumerate(keeps, start=1):
            ctx.check_cancel()
            dur = max(0.05, end - start)
            seg = tmp / f"seg_{i:04d}.mp4"
            ctx.log(f"Segmento {i}/{n}  {format_seconds(start)} → {format_seconds(end)}")
            args = [
                "-ss", f"{start:.3f}", "-i", input_path, "-t", f"{dur:.3f}",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", str(crf),
                "-pix_fmt", "yuv420p", "-avoid_negative_ts", "make_zero",
            ]
            if info.get("has_audio"):
                args += ["-c:a", "aac", "-b:a", "128k"]
            else:
                args += ["-an"]
            args.append(str(seg))
            seg_start = progress_start + span * 0.05 + span * 0.85 * (done / total)
            seg_end = progress_start + span * 0.05 + span * 0.85 * ((done + dur) / total)
            runner.run(
                args,
                duration=dur,
                ctx=ctx,
                progress_start=seg_start,
                progress_end=seg_end,
                label=f"Segmento {i}/{n}",
            )
            list_lines.append(f"file '{seg.as_posix()}'")
            done += dur

        list_file = tmp / "concat.txt"
        list_file.write_text("\n".join(list_lines) + "\n", encoding="utf-8")
        ctx.log("Uniendo segmentos (copia de flujos, sin reanalizar)…")
        runner.run(
            ["-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", output_path],
            ctx=ctx,
            progress_start=progress_start + span * 0.92,
            progress_end=progress_end,
            label="Uniendo segmentos",
        )
        ctx.log(f"Exportación lista: {output_path}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
