"""
Utility variables and functions
"""
from enum import Enum

ORIGINAL_DB_DE_MAPPING : dict[int, str] = {
     0: "mti",
     2: "pan",
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

DB_DE_MAPPING : dict[str, int] = {v: k for k, v in ORIGINAL_DB_DE_MAPPING.items()}


def mask_pan(pan: str) -> str:
    """mask the pan, first 6 digits and last 4, for security"""
    pan_len = len(pan)
    pan_masked = pan[0:6] + ("*" * (pan_len - 10)) + pan[pan_len - 4:]
    return pan_masked

def get_raw_json(message_dict: dict) -> dict:
    """Dict without the pan, expiration date and track 2 data"""
    return {k: v for k, v in message_dict.items() if (k != 2 or k != 14 or k != 35)}



class MessageBaseType(Enum):
    """Message Base Types enum for consistency"""
    ODE_BASE      = 1
    FIN_REQ_BASE  = 2
    FIN_RESP_BASE = 3
    REV_REQ_BASE  = 4
    REV_RESP_BASE = 5

def get_message_base(message_dict: dict, message_type: MessageBaseType) -> dict:
    """Get message base as dict from the processed iso_message
      for populating the relevant model"""
    message_base = {
        "pan"             : message_dict    [DB_DE_MAPPING["pan"]],
        "processing_code" : message_dict    [DB_DE_MAPPING["processing_code"]],
        "amount"          : message_dict    [DB_DE_MAPPING["amount"]],
        "transmitted_at"  : message_dict    [DB_DE_MAPPING["transmitted_at"]],
        "stan"            : message_dict    [DB_DE_MAPPING["stan"]],
        "loc_txn_time"    : message_dict    [DB_DE_MAPPING["loc_txn_time"]],
        "loc_txn_date"    : message_dict    [DB_DE_MAPPING["loc_txn_date"]],
        "rrn"             : message_dict.get(DB_DE_MAPPING["rrn"]),
        "terminal_id"     : message_dict    [DB_DE_MAPPING["terminal_id"]],
        "merchant_id"     : message_dict    [DB_DE_MAPPING["merchant_id"]],
        "currency"        : message_dict    [DB_DE_MAPPING["currency"]],
    }

    if message_type == MessageBaseType.FIN_REQ_BASE:
        message_base["mcc"]             = message_dict.get(DB_DE_MAPPING["mcc"])
        message_base["pos_entry_mode"]  = message_dict.get(DB_DE_MAPPING["pos_entry_mode"])
        message_base["pos_condition"]   = message_dict.get(DB_DE_MAPPING["pos_condition"])
        message_base["acquirer_id"]     = message_dict.get(DB_DE_MAPPING["acquirer_id"])

    if message_type == MessageBaseType.FIN_RESP_BASE:
        message_base["auth_id_resp"]    = message_dict.get(DB_DE_MAPPING["auth_id_resp"])
        message_base["resp_code"]       = message_dict    [DB_DE_MAPPING["resp_code"]]

    if message_type == MessageBaseType.REV_REQ_BASE:
        message_base["mcc"]             = message_dict.get(DB_DE_MAPPING["mcc"])
        message_base["acquirer_id"]     = message_dict.get(DB_DE_MAPPING["acquirer_id"])

    if message_type == MessageBaseType.REV_RESP_BASE:
        message_base["mcc"]             = message_dict.get(DB_DE_MAPPING["mcc"])
        message_base["acquirer_id"]     = message_dict.get(DB_DE_MAPPING["acquirer_id"])
        message_base["resp_code"]       = message_dict    [DB_DE_MAPPING["resp_code"]]

    return message_base
