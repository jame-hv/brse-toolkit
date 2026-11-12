"""Read the JSON object a reviewer model was asked to answer with."""
import json
import re


def json_object(reply: str) -> dict:
    """The first {...} in the reply. ValueError with a message for the user when there is none or it is broken."""
    m = re.search(r"\{.*\}", reply, re.S)
    if not m:
        raise ValueError("reviewer reply contains no JSON")
    try:
        return json.loads(m.group(0))
    except ValueError as e:
        raise ValueError(f"reviewer JSON unreadable: {e}")
