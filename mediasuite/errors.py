class MediaSuiteError(Exception):
    """Error controlado de la aplicación."""


class CancelledError(MediaSuiteError):
    """El usuario canceló el trabajo en curso."""


class FFmpegError(MediaSuiteError):
    """FFmpeg terminó con error o no pudo ejecutarse."""
