"""
Generate linked ISO 8583 messages as field dictionaries.

Keys are data element numbers as strings, matching the parser's JSON output
("0" is the MTI). A response echoes the request's identifying fields, and a
reversal carries the original message's identity in field 90.
"""
# pylint: disable=redefined-outer-name
import random
import pprint
import threading
from datetime import UTC, datetime, timedelta, timezone
from itertools import count

from .ingest import process

LAGOS = timezone(timedelta(hours=1))  # Nigeria has no daylight saving

TEST_PANS = ["4111111111111111", "5500000000000004", "4012888888881881"]
TERMINALS = ["TERM0001", "TERM0002", "TERM0003"]
MERCHANTS = ["MERCHANT123", "MERCHANT456", "MERCHANT789"]
MCCS = ["5411", "5812", "5541", "5999"]
ACQUIRER_ID = "111111"

# About 90% approved, the rest spread over common decline codes
RESPONSE_CODES = ["00", "05", "51", "55", "91"]
RESPONSE_WEIGHTS = [80, 5, 5, 5, 5]


# Field layouts: (kind, size). "fixed" is exactly size characters; "llvar" and
# "lllvar" carry a 2 or 3 digit length prefix and hold up to size characters.
# Everything is ASCII; only the bitmap is raw binary.
FORMATS = {
    "2": ("llvar", 19), "3": ("fixed", 6), "4": ("fixed", 12), "7": ("fixed", 10),
    "11": ("fixed", 6), "12": ("fixed", 6), "13": ("fixed", 4), "14": ("fixed", 4),
    "15": ("fixed", 4), "17": ("fixed", 4), "18": ("fixed", 4), "22": ("fixed", 3),
    "25": ("fixed", 2), "28": ("fixed", 9), "32": ("llvar", 11), "35": ("llvar", 37),
    "37": ("fixed", 12), "38": ("fixed", 6), "39": ("fixed", 2), "41": ("fixed", 8),
    "42": ("fixed", 15), "43": ("fixed", 40), "48": ("lllvar", 999),
    "49": ("fixed", 3), "50": ("fixed", 3), "60": ("lllvar", 999), "90": ("fixed", 42),
}
PREFIX_DIGITS = {"llvar": 2, "lllvar": 3}

_stans = count(1)


def _next_stan() -> str:
    """Next system trace audit number, 6 digits, wrapping after 999999"""
    return f"{next(_stans) % 1_000_000:06d}"


def _times() -> dict[str, str]:
    """Fields 7 (UTC), 12 and 13 (local time and date) for right now"""
    now = datetime.now(UTC)
    local = now.astimezone(LAGOS)
    return {
        "7": now.strftime("%m%d%H%M%S"),
        "12": local.strftime("%H%M%S"),
        "13": local.strftime("%m%d"),
    }


def _encode(field: str, value: str) -> str:
    """One data element as it appears on the wire (length prefix included)."""
    kind, size = FORMATS[field]
    if kind == "fixed":
        if len(value) != size:
            raise ValueError(f"field {field} must be {size} characters, got {len(value)}")
        return value
    if len(value) > size:
        raise ValueError(f"field {field} is longer than {size} characters")
    return f"{len(value):0{PREFIX_DIGITS[kind]}d}{value}"


def pack(msg: dict[str, str]) -> str:
    """Field dictionary to a hex string: ASCII MTI, binary bitmap, ASCII elements."""
    elements = sorted((int(k), v) for k, v in msg.items() if k != "0")
    secondary = any(number > 64 for number, _ in elements)
    bitmap = bytearray(16 if secondary else 8)
    if secondary:
        bitmap[0] |= 0x80  # bit 1 says a secondary bitmap follows
    body = ""
    for number, value in elements:
        bitmap[(number - 1) // 8] |= 0x80 >> ((number - 1) % 8)
        body += _encode(str(number), value)
    return (msg["0"].encode() + bytes(bitmap) + body.encode()).hex().upper()


class FinancialRequest:
    """A purchase request (MTI 0200) that derives its response and reversal."""

    def __init__(self):
        pan = random.choice(TEST_PANS)
        self.fields = {
            "0": "0200",
            "2": pan,
            "3": "000000",
            "4": f"{random.randint(100, 500_000):012d}",
            "11": _next_stan(),
            "14": "2512",
            "18": random.choice(MCCS),
            "22": "021",
            "25": "00",
            "32": ACQUIRER_ID,
            "35": f"{pan}=25121011234500000",
            "37": f"{random.randrange(10**12):012d}",
            "41": random.choice(TERMINALS),
            "42": random.choice(MERCHANTS).ljust(15),
            "49": "566",
            **_times(),
        }

    def response(self, code: str | None = None) -> dict[str, str]:
        """The 0210 for this request. A random weighted code unless one is given."""
        code = code or random.choices(RESPONSE_CODES, RESPONSE_WEIGHTS)[0]
        echoed = ("2", "3", "4", "11", "12", "13", "37", "41", "42", "49")
        msg = {"0": "0210", **{k: self.fields[k] for k in echoed}}
        msg["7"] = _times()["7"]
        msg["39"] = code
        if code == "00":
            msg["38"] = f"{random.randrange(10**6):06d}"
        return msg

    def reversal(self) -> dict[str, str]:
        """The 0400 that undoes this request. Gets a new STAN; field 90 holds the original."""
        echoed = ("2", "3", "4", "18", "32", "37", "41", "42", "49")
        msg = {"0": "0400", "11": _next_stan(), **_times()}
        msg.update({k: self.fields[k] for k in echoed})
        msg["90"] = (
            self.fields["0"]
            + self.fields["11"]
            + self.fields["7"]
            + ACQUIRER_ID.zfill(11)
            + "0" * 11
        )
        return msg


def reversal_response(reversal: dict[str, str]) -> dict[str, str]:
    """The 0410 answering a reversal. Always approved."""
    echoed = ("2", "3", "4", "11", "12", "13", "18", "32", "37", "41", "42", "49", "90")
    msg = {"0": "0410", **{k: reversal[k] for k in echoed}}
    msg["7"] = _times()["7"]
    msg["39"] = "00"
    return msg


def generate_transaction(reversal_chance: float = 0.1) -> dict[str, dict[str, str] | None]:
    """One request and response, plus sometimes a reversal pair for an approved one."""
    request = FinancialRequest()
    response = request.response()
    reversal = None
    if response["39"] == "00" and random.random() < reversal_chance:
        reversal = request.reversal()
    return {
        "request": request.fields,
        "response": response,
        "reversal_request": reversal,
        "reversal_response": reversal_response(reversal) if reversal else None,
    }

def get_transaction_hex_strings() -> list[str]:
    """Pack generated transaction set to hex string"""
    generated_strings = []
    for _, msg in generate_transaction(reversal_chance=0.2).items():
        if msg:
            generated_strings.append(pack(msg))
    return generated_strings


# for threading in start/stop_generator function
stop_event = None # pylint: disable=invalid-name
thread = None     # pylint: disable=invalid-name

def run_generator(stop_event):
    """Continuously generate, pack, and process transactions until stopped."""
    while not stop_event.is_set():
        try:
            transactions = get_transaction_hex_strings()
            for value in transactions:
                if stop_event.is_set():
                    break
                process(value)
        except Exception as e: # pylint: disable=broad-exception-caught
            print(f"Generator error: {e}")
        stop_event.wait(3)

def start_generator():
    """Start the background transaction generator thread if not already running."""
    global stop_event, thread # pylint: disable=global-statement

    if thread is not None and thread.is_alive():
        return
    stop_event = threading.Event()
    thread = threading.Thread(
        target=run_generator,
        args=(stop_event,),
        daemon=True
    )
    thread.start()

def stop_generator():
    """Signal the transaction generator to stop and wait for its thread to finish."""
    if thread is not None and thread.is_alive():
        stop_event.set()
        thread.join(timeout=3)


if __name__ == "__main__":
    for _ in range(3):
        for name, msg in generate_transaction(reversal_chance=0.2).items():
            pprint.pp((name, pack(msg) if msg else None))
