from watchpost.history import recent_checks


def detect_transition(conn, result):
    """
    Compares a just-saved result to whatever came right before it in
    history, so callers only alert on an actual change instead of pinging
    a webhook on every single check while something stays down.

    Returns "down", "up", or None (nothing changed). result must already
    be saved - this looks itself up by endpoint name rather than taking
    the previous result directly, so callers don't have to track state.
    """
    checks = recent_checks(conn, result.endpoint_name, limit=2)
    if len(checks) < 2:
        # first check ever for this endpoint - worth flagging if it's
        # already broken, nobody needs a ping just for "first check was fine"
        return "down" if not result.success else None

    current, previous = checks[0], checks[1]
    if previous.success == current.success:
        return None
    return "up" if current.success else "down"
