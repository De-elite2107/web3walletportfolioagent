import re

_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


def is_valid_address(address: str) -> bool:
    return bool(_ADDRESS_RE.match(address))
