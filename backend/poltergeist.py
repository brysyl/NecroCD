"""Latin-esque stack trace translator."""
import re

_LEXICON = [
    (r"Traceback \(most recent call last\)", "Vestigium recentissimum revelatur"),
    (r"ModuleNotFoundError|ImportError", "Modulus perditus est"),
    (r"SyntaxError", "Error syntaxis, verba maledicta"),
    (r"AssertionError|FAILED|failed", "Probatio defecit"),
    (r"TimeoutError|timed out", "Tempus exhaustum est"),
    (r"PermissionError", "Licentia negata"),
    (r"FileNotFoundError", "Tabula non inventa"),
    (r"KeyError", "Clavis ignota"),
    (r"TypeError", "Typus perversus"),
    (r"NameError", "Nomen ignotum"),
    (r"Error", "Error"),
]


def translate_trace(trace: str) -> str:
    """Return a Latin-esque rendering of the headline problems in a trace."""
    lines = []
    for pattern, latin in _LEXICON:
        if re.search(pattern, trace):
            if latin not in lines:
                lines.append(latin)
    if not lines:
        lines.append("Umbra ignota in codice habitat")
    return "; ".join(lines) + ". Exorcizamus te, codex immunde!"
