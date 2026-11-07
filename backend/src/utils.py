"""
Utility variables and functions
"""

ORIGINAL_DB_DE_MAPPING : dict[int, str] = {
     0: "mti",
     2: "pan_masked",
     3: "processing_code",
     4: "amount",
     7: "transmitted_at",
    11: "stan",
    12: "loc_txn_time",
    13: "loc_txn_date",
    18: "mcc",
    22: "pos_entry_mode",
    25: "pos_condition",
    32: "acquirer_id",
    33: "forwarder_id",
    37: "rrn",
    38: "auth_id_resp",
    39: "resp_code",
    41: "terminal_id",
    42: "merchant_id",
    49: "currency",
}


DB_DE_MAPPING = {v: k for k, v in ORIGINAL_DB_DE_MAPPING.items()}


def mask_pan(pan: str) -> str:
    """mask the pan, first 6 digits and last 4, for security"""
    pan_len = len(pan)
    pan_masked = pan[0:6] + ("*" * (pan_len - 10)) + pan[pan_len - 4:]
    return pan_masked

def get_raw_json(message_dict: dict) -> dict:
    """Dict without the pan, expiration date and track 2 data"""
    return {k: v for k, v in message_dict.items() if (k != 2 or k != 14 or k != 35)}
