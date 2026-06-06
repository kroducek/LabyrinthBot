ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def _room_marker(col_idx: int, row: int, rows: int, cols: int) -> str:
    """◆ roh, ◇ okraj, · vnitřní"""
    is_corner = (row in (1, rows)) and (col_idx in (0, cols - 1))
    is_edge   = (row in (1, rows)) or  (col_idx in (0, cols - 1))
    if is_corner: return "◆"
    if is_edge:   return "◇"
    return "·"

def generate_text_board(rows: int, cols: int) -> str:
    """
    Vygeneruje textovou reprezentaci mapy ve stylu mřížky.
    Malé mapy (< 6 sloupců) — fancy UI s kompasem a markery.
    Velké mapy (6+) — kompaktní formát.

    Markery: ◆ roh (2 průchody)  ◇ okraj (3)  · střed (4)

    Příklad 4x4:
          W ←——→ E
      ┌────┬────┬────┬────┐
    N │◆A1 │◇B1 │◇C1 │◆D1 │
      ├────┼────┼────┼────┤
      │◇A2 │·B2 │·C2 │◇D2 │
      ├────┼────┼────┼────┤
      │◇A3 │·B3 │·C3 │◇D3 │
      ├────┼────┼────┼────┤
    S │◆A4 │◇B4 │◇C4 │◆D4 │
      └────┴────┴────┴────┘
      ◆ roh (2 průchody)  ◇ okraj (3)  · střed (4)
    """
    if cols >= 6:
        # Kompaktní formát pro velké mapy
        lines = []
        for r in range(1, rows + 1):
            row_str = " ".join(
                f"[{_room_marker(c, r, rows, cols)}{ALPHABET[c]}{r}]"
                for c in range(cols)
            )
            lines.append(row_str)
        lines.append("◆ roh (2)  ◇ okraj (3)  · střed (4)")
        return "\n".join(lines)

    # Fancy UI pro menší mapy
    top = "┌" + "┬".join(["────"] * cols) + "┐\n"
    mid = "├" + "┼".join(["────"] * cols) + "┤\n"
    bot = "└" + "┴".join(["────"] * cols) + "┘\n"

    # Kompas nahoře
    indent = "      "
    compass_top = indent + "W ←——→ E\n"

    lines = [compass_top, indent + top]
    for r in range(1, rows + 1):
        # Levý kompas
        if r == 1:        left = "  N "
        elif r == rows:   left = "  S "
        else:             left = "    "

        row_str = left + "│"
        for c in range(cols):
            marker = _room_marker(c, r, rows, cols)
            name = f"{ALPHABET[c]}{r}"
            row_str += f"{marker}{name} │"
        lines.append(row_str + "\n")
        if r < rows:
            lines.append(indent + mid)

    lines.append(indent + bot)
    lines.append("      ◆ roh (2 průchody)  ◇ okraj (3)  · střed (4)")
    return "".join(lines)