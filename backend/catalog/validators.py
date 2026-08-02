import re
import warnings
import zlib
from io import BytesIO
from pathlib import Path
from xml.parsers import expat

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

MAX_CATEGORY_ICON_SIZE = 5 * 1024 * 1024
MAX_CATEGORY_ICON_DIMENSION = 4096
MAX_CATEGORY_ICON_PIXELS = 16_777_216
MAX_SVG_ELEMENTS = 2048
MAX_SVG_DEPTH = 64

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SVG_NAMESPACE = "http://www.w3.org/2000/svg"

SAFE_SVG_ELEMENTS = {
    "circle",
    "clipPath",
    "defs",
    "desc",
    "ellipse",
    "g",
    "line",
    "linearGradient",
    "mask",
    "path",
    "polygon",
    "polyline",
    "radialGradient",
    "rect",
    "stop",
    "svg",
    "title",
}

SAFE_SVG_ATTRIBUTES = {
    "clip-path",
    "clip-rule",
    "color",
    "color-interpolation",
    "color-rendering",
    "cx",
    "cy",
    "d",
    "display",
    "fill",
    "fill-opacity",
    "fill-rule",
    "fx",
    "fy",
    "gradientTransform",
    "gradientUnits",
    "height",
    "id",
    "mask",
    "mask-type",
    "offset",
    "opacity",
    "pathLength",
    "points",
    "preserveAspectRatio",
    "r",
    "rx",
    "ry",
    "shape-rendering",
    "spreadMethod",
    "stop-color",
    "stop-opacity",
    "stroke",
    "stroke-dasharray",
    "stroke-dashoffset",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-miterlimit",
    "stroke-opacity",
    "stroke-width",
    "transform",
    "vector-effect",
    "version",
    "viewBox",
    "visibility",
    "width",
    "x",
    "x1",
    "x2",
    "y",
    "y1",
    "y2",
}

LOCAL_URL_RE = re.compile(r"url\(\s*#[A-Za-z_][A-Za-z0-9_.:-]*\s*\)\Z", re.I)
URL_FUNCTION_RE = re.compile(r"url\s*\(", re.I)
SAFE_ID_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.:-]*\Z")
SAFE_COLOR_RE = re.compile(
    r"(?:"
    r"none|currentcolor|context-fill|context-stroke|transparent|"
    r"inherit|initial|unset|"
    r"#[0-9a-f]{3,8}|[a-z]+|"
    r"(?:rgb|rgba|hsl|hsla)\([0-9.,%+\-/\s]+\)"
    r")\Z",
    re.I,
)


class UnsafeSvgError(Exception):
    pass


def _validation_error(message: str) -> ValidationError:
    return ValidationError(message, code="invalid_category_icon")


def _read_icon(value) -> bytes:
    try:
        original_position = value.tell()
    except (AttributeError, OSError, ValueError):
        original_position = 0

    try:
        try:
            value.seek(0)
        except (AttributeError, OSError, ValueError):
            value.open("rb")
            value.seek(0)
        data = value.read(MAX_CATEGORY_ICON_SIZE + 1)
    finally:
        try:
            value.seek(original_position)
        except (AttributeError, OSError, ValueError):
            pass

    if not isinstance(data, bytes):
        raise _validation_error("فایل آیکن معتبر نیست.")
    if len(data) > MAX_CATEGORY_ICON_SIZE:
        raise _validation_error("حجم آیکن حداکثر ۵ مگابایت باشد.")
    return data


def _validate_png_chunks(data: bytes) -> None:
    if not data.startswith(PNG_SIGNATURE):
        raise _validation_error("محتوای فایل PNG معتبر نیست.")

    offset = len(PNG_SIGNATURE)
    chunk_index = 0
    saw_header = False
    saw_image_data = False
    saw_end = False

    while offset < len(data):
        if len(data) - offset < 12:
            raise _validation_error("ساختار فایل PNG معتبر نیست.")

        length = int.from_bytes(data[offset : offset + 4], "big")
        chunk_type = data[offset + 4 : offset + 8]
        chunk_end = offset + 12 + length
        if chunk_end > len(data) or not re.fullmatch(rb"[A-Za-z]{4}", chunk_type):
            raise _validation_error("ساختار فایل PNG معتبر نیست.")

        chunk_data = data[offset + 8 : offset + 8 + length]
        expected_crc = int.from_bytes(data[offset + 8 + length : chunk_end], "big")
        actual_crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise _validation_error("ساختار فایل PNG معتبر نیست.")

        if chunk_index == 0 and (chunk_type != b"IHDR" or length != 13):
            raise _validation_error("ساختار فایل PNG معتبر نیست.")
        if chunk_type == b"IHDR":
            if saw_header:
                raise _validation_error("ساختار فایل PNG معتبر نیست.")
            saw_header = True
        elif chunk_type == b"IDAT":
            saw_image_data = True
        elif chunk_type == b"IEND":
            if length != 0 or saw_end:
                raise _validation_error("ساختار فایل PNG معتبر نیست.")
            saw_end = True
            if chunk_end != len(data):
                raise _validation_error("فایل PNG دارای داده‌ی اضافی است.")

        offset = chunk_end
        chunk_index += 1

    if not (saw_header and saw_image_data and saw_end):
        raise _validation_error("ساختار فایل PNG معتبر نیست.")


def _validate_png(data: bytes) -> None:
    _validate_png_chunks(data)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format != "PNG":
                    raise _validation_error("محتوای فایل PNG معتبر نیست.")
                width, height = image.size
                if (
                    width > MAX_CATEGORY_ICON_DIMENSION
                    or height > MAX_CATEGORY_ICON_DIMENSION
                    or width * height > MAX_CATEGORY_ICON_PIXELS
                ):
                    raise _validation_error("ابعاد آیکن PNG بیش از حد مجاز است.")
                if getattr(image, "is_animated", False):
                    raise _validation_error("آیکن PNG باید یک تصویر ثابت باشد.")
                image.verify()
    except ValidationError:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as exc:
        raise _validation_error("محتوای فایل PNG معتبر نیست.") from exc


def _split_xml_name(name: str) -> tuple[str | None, str]:
    if "}" not in name:
        return None, name
    namespace, local_name = name.rsplit("}", 1)
    return namespace, local_name


def _validate_svg_attribute(name: str, value: str) -> None:
    namespace, local_name = _split_xml_name(name)
    if namespace is not None or local_name.lower().startswith("on"):
        raise UnsafeSvgError
    if local_name not in SAFE_SVG_ATTRIBUTES or len(value) > 4096:
        raise UnsafeSvgError
    if (
        "\\" in value
        or "'" in value
        or '"' in value
        or any(ord(character) < 32 for character in value)
    ):
        # CSS escapes and quoted CSS image values can disguise external resources.
        raise UnsafeSvgError

    normalized = value.strip()
    lowered = normalized.lower()
    if local_name == "id" and not SAFE_ID_RE.fullmatch(normalized):
        raise UnsafeSvgError
    if any(
        token in lowered
        for token in (
            "javascript:",
            "data:",
            "file:",
            "http:",
            "https:",
            "@import",
            "expression(",
            "-moz-binding",
        )
    ):
        raise UnsafeSvgError
    if "://" in lowered or lowered.startswith("//"):
        raise UnsafeSvgError

    local_url = LOCAL_URL_RE.fullmatch(normalized)
    if local_name in {"clip-path", "mask"}:
        if lowered != "none" and not local_url:
            raise UnsafeSvgError
    elif local_name in {"fill", "stroke"}:
        if not local_url and not SAFE_COLOR_RE.fullmatch(normalized):
            raise UnsafeSvgError
    elif local_name in {"color", "stop-color"}:
        if not SAFE_COLOR_RE.fullmatch(normalized):
            raise UnsafeSvgError
    elif URL_FUNCTION_RE.search(normalized):
        raise UnsafeSvgError


def _validate_svg(data: bytes) -> None:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise _validation_error("فایل SVG باید با UTF-8 ذخیره شده باشد.") from exc

    state = {
        "depth": 0,
        "elements": 0,
        "root_seen": False,
        "stack": [],
    }
    parser = expat.ParserCreate(namespace_separator="}")
    parser.buffer_text = True
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)

    def reject(*_args):
        raise UnsafeSvgError

    def on_xml_decl(_version, encoding, _standalone):
        if encoding and encoding.lower().replace("_", "-") not in {
            "utf-8",
            "utf8",
        }:
            raise UnsafeSvgError

    def on_namespace(_prefix, uri):
        if uri != SVG_NAMESPACE:
            raise UnsafeSvgError

    def on_start(name, attributes):
        namespace, local_name = _split_xml_name(name)
        if namespace != SVG_NAMESPACE or local_name not in SAFE_SVG_ELEMENTS:
            raise UnsafeSvgError
        if not state["root_seen"]:
            if local_name != "svg":
                raise UnsafeSvgError
            state["root_seen"] = True

        state["depth"] += 1
        state["elements"] += 1
        if state["depth"] > MAX_SVG_DEPTH or state["elements"] > MAX_SVG_ELEMENTS:
            raise UnsafeSvgError
        state["stack"].append(local_name)
        for attribute_name, value in attributes.items():
            _validate_svg_attribute(attribute_name, value)

    def on_end(_name):
        state["stack"].pop()
        state["depth"] -= 1

    def on_text(content):
        if content.strip() and (
            not state["stack"] or state["stack"][-1] not in {"title", "desc"}
        ):
            raise UnsafeSvgError

    parser.XmlDeclHandler = on_xml_decl
    parser.StartNamespaceDeclHandler = on_namespace
    parser.StartElementHandler = on_start
    parser.EndElementHandler = on_end
    parser.CharacterDataHandler = on_text
    parser.ProcessingInstructionHandler = reject
    parser.StartDoctypeDeclHandler = reject
    parser.EntityDeclHandler = reject
    parser.UnparsedEntityDeclHandler = reject
    parser.NotationDeclHandler = reject
    parser.ExternalEntityRefHandler = reject

    try:
        parser.Parse(text, True)
    except (UnsafeSvgError, expat.ExpatError, ValueError) as exc:
        raise _validation_error("ساختار یا محتوای فایل SVG ایمن نیست.") from exc
    if not state["root_seen"] or state["depth"] != 0:
        raise _validation_error("ساختار یا محتوای فایل SVG ایمن نیست.")


def validate_category_icon(value) -> None:
    if not value:
        return

    name = getattr(value, "name", "")
    extension = Path(name).suffix.lower()
    if extension not in {".png", ".svg"}:
        raise _validation_error("فرمت آیکن باید PNG یا SVG باشد.")

    size = getattr(value, "size", None)
    if size is not None and size > MAX_CATEGORY_ICON_SIZE:
        raise _validation_error("حجم آیکن حداکثر ۵ مگابایت باشد.")

    data = _read_icon(value)
    if extension == ".png":
        _validate_png(data)
    else:
        _validate_svg(data)
