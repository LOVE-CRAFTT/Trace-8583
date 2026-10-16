-- TODO: Give overview of current database design


CREATE TABLE IF NOT EXISTS original_data_elements (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mti             CHAR(4)     NOT NULL,
    transmitted_at  CHAR(10)    NOT NULL,
    stan            CHAR(6)     NOT NULL,
    acquirer_id     VARCHAR(11),
    forwarder_id    VARCHAR(11),
    UNIQUE (mti, transmitted_at, stan)
);

CREATE TABLE IF NOT EXISTS financial_request (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pan_masked      VARCHAR(19) NOT NULL,
    processing_code CHAR(6)     NOT NULL,
    amount          BIGINT      NOT NULL,
    transmitted_at  CHAR(10)    NOT NULL,
    stan            CHAR(6)     NOT NULL,
    loc_txn_time    CHAR(6)     NOT NULL,
    loc_txn_date    CHAR(4)     NOT NULL,
    mcc             CHAR(4),
    pos_entry_mode  CHAR(3),
    pos_condition   CHAR(2),
    acquirer_id     VARCHAR(11),
    rrn             CHAR(12),
    terminal_id     CHAR(8)     NOT NULL,
    merchant_id     CHAR(15)    NOT NULL,
    currency        CHAR(3)     NOT NULL,

    -- remove (don't keep)s before inserting
    raw_json        JSONB       NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (stan, terminal_id, loc_txn_date)
);


CREATE TABLE IF NOT EXISTS financial_response (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pan_masked      VARCHAR(19) NOT NULL,
    processing_code CHAR(6)     NOT NULL,
    amount          BIGINT      NOT NULL,
    transmitted_at  CHAR(10)    NOT NULL,
    stan            CHAR(6)     NOT NULL,
    loc_txn_time    CHAR(6)     NOT NULL,
    loc_txn_date    CHAR(4)     NOT NULL,
    rrn             CHAR(12),
    auth_id_resp    CHAR(6),
    resp_code       CHAR(2)     NOT NULL,
    terminal_id     CHAR(8)     NOT NULL,
    merchant_id     CHAR(15)    NOT NULL,
    currency        CHAR(3)     NOT NULL,

    -- populate by referencing unique combo
    request_id      BIGINT REFERENCES financial_request(id),

    -- remove (don't keep)s before inserting
    raw_json        JSONB       NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (stan, terminal_id, loc_txn_date)
);


CREATE TABLE IF NOT EXISTS reversal_request (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pan_masked      VARCHAR(19) NOT NULL,
    processing_code CHAR(6)     NOT NULL,
    amount          BIGINT      NOT NULL,
    transmitted_at  CHAR(10)    NOT NULL,
    stan            CHAR(6)     NOT NULL,
    loc_txn_time    CHAR(6)     NOT NULL,
    loc_txn_date    CHAR(4)     NOT NULL,
    mcc             CHAR(4),
    acquirer_id     VARCHAR(11),
    rrn             CHAR(12),
    terminal_id     CHAR(8)     NOT NULL,
    merchant_id     CHAR(15)    NOT NULL,
    currency        CHAR(3)     NOT NULL,
    ode_id          BIGINT REFERENCES original_data_elements(id)    NOT NULL,

    -- original financial request from (DE 90 STAN + terminal_id + transmitted_at)
    -- meaning DE 90 should be filled first
    original_fin_req_id BIGINT REFERENCES financial_request(id),

    -- remove (don't keep)s before inserting
    raw_json        JSONB       NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (stan, terminal_id, loc_txn_date)
);


CREATE TABLE IF NOT EXISTS reversal_response (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pan_masked      VARCHAR(19) NOT NULL,
    processing_code CHAR(6)     NOT NULL,
    amount          BIGINT      NOT NULL,
    transmitted_at  CHAR(10)    NOT NULL,
    stan            CHAR(6)     NOT NULL,
    loc_txn_time    CHAR(6)     NOT NULL,
    loc_txn_date    CHAR(4)     NOT NULL,
    mcc             CHAR(4),
    acquirer_id     VARCHAR(11),
    rrn             CHAR(12),
    resp_code       CHAR(2)     NOT NULL,
    terminal_id     CHAR(8)     NOT NULL,
    merchant_id     CHAR(15)    NOT NULL,
    currency        CHAR(3)     NOT NULL,
    ode_id          BIGINT REFERENCES original_data_elements(id)      NOT NULL,

    -- reversal request
    reversal_req_id BIGINT REFERENCES reversal_request(id),

    -- remove (don't keep)s before inserting
    raw_json        JSONB       NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (stan, terminal_id, loc_txn_date)
);
