
# parses a raw LSNP message (key-value format) into a Python dictionary
# each message is separated by `\n`, terminated with `\n\n`

def parse_message(raw: str) -> dict:
    message = {}
    lines = raw.strip().split('\n')
    for line in lines:
        if ':' not in line:
            continue  # Skip malformed or empty lines
        key, value = line.split(':', 1)
        message[key.strip()] = value.strip()
    return message


# creates a LSNP message from a dictionary of fields into a raw string
# appends the terminating blank line (\n\n) as per MP spec
 
def craft_message(fields: dict) -> str:
    lines = [f"{key}: {value}" for key, value in fields.items()]
    return '\n'.join(lines) + '\n\n'