def generate_text_board(rows: int, cols: int) -> str:
    """
    Vygeneruje textovou reprezentaci mapy ve stylu mřížky.
    Např.
    ┌────┬────┬────┐
    │ A1 │ B1 │ C1 │
    └────┴────┴────┘
    """
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    
    # Pro velké mapy použijeme kompaktní formát, aby nedocházelo k zalamování
    if cols >= 6:
        lines = []
        for r in range(1, rows + 1):
            row_str = " ".join(f"[{alphabet[c]}{r:<1}]" for c in range(cols))
            lines.append(row_str)
        return "\n".join(lines)
    
    # Fancy UI pro menší mapy
    top = "┌" + "┬".join(["────"] * cols) + "┐\n"
    mid = "├" + "┼".join(["────"] * cols) + "┤\n"
    bot = "└" + "┴".join(["────"] * cols) + "┘"
    
    lines = [top]
    for r in range(1, rows + 1):
        row_str = "│"
        for c in range(cols):
            letter = alphabet[c]
            room_name = f"{letter}{r}"
            row_str += f" {room_name:<2} │"
        lines.append(row_str + "\n")
        if r < rows:
            lines.append(mid)
    
    lines.append(bot)
    return "".join(lines)
