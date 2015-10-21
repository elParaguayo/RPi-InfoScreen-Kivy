

def clean_command(value):
    """ Strips whitespace, underscores dashes and lowercases value """
    return value.strip().lower().replace("_", "").replace("-", "")\
        .replace(" ", "")
