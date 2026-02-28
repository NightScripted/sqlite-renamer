import config


def logPrint(q: str) -> None:
    """Print *q* to stdout, suppressing ``[DEBUG]`` messages when ``DEBUG_MODE`` is ``False``.

    Reads ``config.DEBUG_MODE`` at call time so runtime changes to the flag
    are respected immediately.

    Args:
        q (str): Message to print.
    """
    if "[DEBUG]" in q and not config.DEBUG_MODE:
        return
    print(q)
