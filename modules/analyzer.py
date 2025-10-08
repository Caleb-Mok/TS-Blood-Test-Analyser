
def get_status_color(value, min_val, max_val, tolerance=0.10):
    
    """Return color based on how far value is from healthy range."""

    try:
        value = float(value)
    except (ValueError, TypeError):
        return None # skip empty
    
    lower_warn = min_val * (1 + tolerance)
    upper_warn = max_val * (1 - tolerance)
    if value < min_val or value > max_val:
        return "red"
    elif value < lower_warn or value > upper_warn:
        return "yellow"
    else:
        return "green"