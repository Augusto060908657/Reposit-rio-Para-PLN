# Compatibilidade entre faster-whisper e versões recentes do PyAV (Python 3.13+)
try:
    import av

    _orig_av_open = av.open

    def _av_open_compat(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _orig_av_open(*args, **kwargs)

    av.open = _av_open_compat
except ImportError:
    pass
