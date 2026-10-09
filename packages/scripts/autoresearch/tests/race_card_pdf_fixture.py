"""Small generated PDF fixtures; no KRA download is required by tests."""

from __future__ import annotations

from shared.kra_race_card_pdf import MEETINGS

HORSE_NAME = "\ud14c\uc2a4\ud2b8\ub9c8"
TRAINING_TEXT = "16\ud68c242\ubd84(\uad00)/\uad6c18\uc2b51"
GATE_TEXT = "\ucd9c\ubc1c\uc870\uad50:260501(\uad00,\uc591\ud638)"
TREATMENT_TEXT = "260617\uadfc\uc721\ud1b51\ud68c"
SWIMMING_TEXT = "\uc218\uc601 : 0\ud68c 0\ubc14\ud034"
TRAINER_TEXT = "(28\uc870)\ud568\uc644\uc2dd 52\uc2b9(8.3%)"
PANEL_TEXT = "\n".join(
    (TRAINER_TEXT, TRAINING_TEXT, SWIMMING_TEXT, GATE_TEXT, TREATMENT_TEXT)
)


def make_card_pdf(
    *,
    meet: int = 1,
    race_date: str = "20260627",
    race_no: int = 1,
    horse_numbers: tuple[int, ...] = (1, 2),
    extra_history: bool = True,
    joined_headers: bool = False,
) -> bytes:
    """Generate just the PDF text and rectangles our layout contract requires."""
    commands = []

    def text(value: str, x: float, y: float, size: int, scale: int = 100) -> None:
        encoded = value.encode("utf-16-be").hex()
        commands.append(
            f"BT /F1 {size} Tf {scale} Tz 1 0 0 1 {x} {y} Tm <{encoded}> Tj ET"
        )

    text("10\uc2dc35\ubd84", 120, 770, 12)
    left, name_right, panel_right = (11, 113, 199) if meet == 2 else (10, 110, 196)
    for index, number in enumerate(horse_numbers):
        top = 105 + index * 100
        commands.extend(
            (
                f"{left} {842 - top - 0.5} 100 .5 re f",
                f"{left} {842 - top - 100} 100 .5 re f",
                f"{name_right} {842 - top - 100} .1 100 re f",
                f"{panel_right} {842 - top - 100} .1 100 re f",
            )
        )
        text(str(number), 10.2 if number >= 10 else 14, 842 - top - 13, 13, 54)
        text(HORSE_NAME, 26 if joined_headers else 32, 842 - top - 13, 13)
        for offset, line in enumerate(PANEL_TEXT.splitlines()):
            if meet == 2 and line == TRAINING_TEXT:
                line = "2\uc8fc\uc870\uad50: 7\ud68c108\ubd84(\uad00)"
            text(line, name_right + 2, 842 - top - 30 - offset * 12, 4)
        if extra_history:
            text("260610\uc0b0\ud1b199\ud68c", panel_right + 5, 842 - top - 70, 4)
            text(
                "260617-2R \uc8fc\ud589\uc2ec\uc0ac", panel_right + 5, 842 - top - 30, 4
            )
    footer = f"{MEETINGS[meet][2]} {race_no}\uacbd\uc8fc[{race_date[:4]}.{race_date[4:6]}.{race_date[6:]}]"
    text(footer, 12, 20, 7)
    stream = "\n".join(commands).encode("ascii")
    cmap = b"""/CIDInit /ProcSet findresource begin
12 dict begin begincmap
/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def
/CMapName /IdentityUnicode def /CMapType 2 def
1 begincodespacerange <0000> <FFFF> endcodespacerange
1 beginbfrange <0000> <FFFF> <0000> endbfrange
endcmap CMapName currentdict /CMap defineresource pop end end"""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type0 /BaseFont /Fixture /Encoding /Identity-H /DescendantFonts [6 0 R] /ToUnicode 8 0 R >>",
        b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /Fixture /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> /DW 1000 /FontDescriptor 7 0 R >>",
        b"<< /Type /FontDescriptor /FontName /Fixture /Flags 4 /FontBBox [0 -200 1000 800] /ItalicAngle 0 /Ascent 800 /Descent -200 /CapHeight 800 /StemV 80 >>",
        f"<< /Length {len(cmap)} >>\nstream\n".encode() + cmap + b"\nendstream",
    ]
    result = bytearray(b"%PDF-1.7\n")
    offsets = [0]
    for number, value in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(f"{number} 0 obj\n".encode() + value + b"\nendobj\n")
    xref = len(result)
    result.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        result.extend(f"{offset:010d} 00000 n \n".encode())
    result.extend(
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(result)
