def convert_action_string_to_flags(action_string):
    """
    Converts string format of action (buy/sell) to flags for optionstools.pricing package
    """
    return (1,-1) if action_string == 'buy' else (-1,1)
