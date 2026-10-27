"""Nemotron model ids served by Nebius Token Factory.

Ids are the catalog values from tokenfactory.nebius.com (October 2026).
The Apps and Agents track asks for a fast model on ordinary calls and a
stronger model when the step needs planning or verification.
"""

NANO = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
SUPER = "nvidia/nemotron-3-super-120b-a12b"
ULTRA = "nvidia/Nemotron-3-Ultra-550b-a55b"

# Default smoke pair. Ultra is opt-in: it is several times the price of Super.
SMOKE_MODELS = (NANO, SUPER)

ROLE_MODEL = {
    "format": NANO,
    "plan": SUPER,
    "verify": SUPER,
}


def model_for(role: str) -> str:
    try:
        return ROLE_MODEL[role]
    except KeyError as exc:
        known = ", ".join(sorted(ROLE_MODEL))
        raise ValueError(f"unknown role {role!r}; expected one of {known}") from exc
