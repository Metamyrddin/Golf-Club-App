"""Fitter exports: JSON (caller), CSV, and a small text PDF with no extra library."""

from __future__ import annotations

import csv
import io


def recommendation_csv(result: dict) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "set",
            "brand",
            "slot",
            "label",
            "head",
            "head_category",
            "shaft",
            "flex",
            "shaft_weight_g",
            "loft",
            "length_delta_in",
            "recommended_length_in",
            "lie_label",
            "lie_delta_deg",
            "grip",
        ]
    )
    for bag in result["sets"]:
        for club in bag["clubs"]:
            writer.writerow(
                [
                    bag["name"],
                    bag["brand"],
                    club["slot"],
                    club["label"],
                    club["head"]["model"],
                    club["head"]["category"],
                    club["shaft"]["model"],
                    club["flex"],
                    club["shaft"]["weight_g"],
                    club["loft"],
                    club["length_delta_in"],
                    club["recommended_length_in"],
                    club["lie_label"],
                    club["lie_delta_deg"] if club["lie_delta_deg"] is not None else "",
                    club["grip"],
                ]
            )
    return buffer.getvalue()


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def recommendation_pdf(result: dict) -> bytes:
    """A single-page-or-more fitting sheet. Helvetica only, so no font files."""
    target = result["target"]
    lines = [
        "FAIRWAY LEDGER  -  fitting sheet",
        result.get("disclaimer", ""),
        "",
        (
            f"Speed {target['swing_speed_mph']:.0f} mph ({target['swing_speed_source']})   "
            f"Flex {target['flex']}   Length {target['length_delta_in']:+.2f} in   "
            f"Lie {target['lie_delta_deg']:+.1f} deg ({target['lie_label']})   "
            f"Grip {target['grip']}"
        ),
        f"Head category {target['head_category'].replace('_', ' ')}",
        f"Wrist-to-floor {target['wrist_to_floor_in']:.1f} in"
        + (" estimated" if target["wrist_to_floor_estimated"] else " measured"),
    ]
    if target.get("medical_flags"):
        lines.append("Medical flags: " + ", ".join(target["medical_flags"]))
    for note in result.get("assumptions") or []:
        lines.append("Note: " + note)
    lines.append("")
    for bag in result["sets"]:
        lines.append(f"== {bag['name']}  ({bag['brand']})  flex family {bag['flex_family']} ==")
        for club in bag["clubs"]:
            loft = f"{club['loft']:.1f} deg" if isinstance(club["loft"], (int, float)) else ""
            lines.append(
                f"  {club['label']}: {club['head']['model']} + {club['shaft']['model']} "
                f"{club['flex']} {club['shaft']['weight_g']:.0f}g {loft} "
                f"len {club['recommended_length_in']:.2f}in grip {club['grip']}"
            )
        wrapped = _wrap(bag["rationale"], 96)
        lines.extend(wrapped)
        lines.append("")
    lines.append("Share medical notes only with the fitter. Not a medical clearance.")

    # Wrap long lines and paginate at 46 lines.
    pages: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        for piece in _wrap(line, 96) or [""]:
            current.append(piece)
            if len(current) >= 46:
                pages.append(current)
                current = []
    if current:
        pages.append(current)

    objects: list[bytes] = []

    def add(data: bytes) -> int:
        objects.append(data)
        return len(objects)

    font_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids = []
    content_ids = []
    for page_lines in pages:
        commands = ["BT", "/F1 9 Tf", "14 TL", "40 760 Td"]
        for index, line in enumerate(page_lines):
            if index:
                commands.append("T*")
            commands.append(f"({_pdf_escape(line)}) Tj")
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1", errors="replace")
        content_ids.append(
            add(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
        )
    # Pages parent is created after page objects so we know the kids. Two-pass:
    # reserve the pages object id first.
    pages_id = add(b"<< /Type /Pages /Count 0 /Kids [] >>")
    for content_id in content_ids:
        page_ids.append(
            add(
                f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 612 792] "
                f"/Contents {content_id} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>".encode()
            )
        )
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[pages_id - 1] = (
        f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>".encode()
    )
    catalog_id = add(f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode())

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{index} 0 obj\n".encode())
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(objects)+1}\n".encode())
    out.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode())
    out.extend(
        f"trailer << /Size {len(objects)+1} /Root {catalog_id} 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    )
    return bytes(out)


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= width:
            current += " " + word
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines
