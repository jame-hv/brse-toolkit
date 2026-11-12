"""Read the JSON object a reviewer model was asked to answer with."""
import json


def json_object(reply: str) -> dict:
    """The JSON object starting at the first "{" of the reply; text after it is ignored. No fallback to a
    later "{": inside a broken answer that would be one issue, read as a clean review.
    ValueError with a message for the user when there is none or it is broken."""
    i = reply.find("{")
    if i < 0:
        raise ValueError("reviewer reply contains no JSON")
    try:
        obj, _ = json.JSONDecoder().raw_decode(reply, i)
    except ValueError as e:
        raise ValueError(f"reviewer JSON unreadable: {e}")
    if not isinstance(obj, dict):
        raise ValueError("reviewer JSON unreadable: not an object")
    return obj
