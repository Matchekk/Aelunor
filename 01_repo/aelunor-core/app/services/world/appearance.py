def format_appearance_message(display_name: str, kind: str, source: str, new_value: str) -> str:
    if kind == "aging_stage":
        return f"{display_name} wirkt nun deutlich {new_value}."
    if kind == "corruption_threshold":
        return f"An {display_name} wird die Verderbnis sichtbar: {new_value}."
    if kind == "class_visual":
        return f"{display_name}s neue Klasse hinterlässt sichtbare Spuren: {new_value}."
    if kind == "faction_visual":
        return f"{display_name} trägt nun sichtbare Zeichen einer Fraktion: {new_value}."
    if kind == "scar_added":
        return f"{display_name} trägt nun eine neue Narbe: {new_value}."
    return f"{display_name}s Erscheinung verändert sich: {new_value}."
