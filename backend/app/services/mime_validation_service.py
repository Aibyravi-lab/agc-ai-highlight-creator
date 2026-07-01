ALLOWED_MIME_TYPES: frozenset = frozenset({
    "video/mp4",
    "video/x-msvideo",
    "video/quicktime",
    "video/webm",
    "video/x-matroska",
})


class MimeValidationService:

    HEADER_SIZE = 12

    ALLOWED_MIME_TYPES = ALLOWED_MIME_TYPES

    @staticmethod
    def detect(header: bytes) -> str | None:

        if len(header) < 4:
            return None

        # EBML magic — WebM and MKV share this header
        if header[:4] == b'\x1a\x45\xdf\xa3':
            return "video/webm"

        # RIFF container — AVI
        if (
            header[:4] == b'RIFF'
            and len(header) >= 12
            and header[8:12] == b'AVI '
        ):
            return "video/x-msvideo"

        # ISO Base Media (MP4 / MOV / M4V)
        if len(header) >= 8 and header[4:8] == b'ftyp':
            brand = header[8:12] if len(header) >= 12 else b''
            if brand == b'qt  ':
                return "video/quicktime"
            return "video/mp4"

        # Old QuickTime atom-based container (pre-ftyp .mov files)
        if len(header) >= 8 and header[4:8] in (
            b'moov', b'mdat', b'free', b'skip', b'wide'
        ):
            return "video/quicktime"

        return None

    @classmethod
    def is_allowed(
        cls,
        header: bytes
    ) -> tuple[bool, str | None]:

        mime = cls.detect(header)
        return mime in cls.ALLOWED_MIME_TYPES, mime
