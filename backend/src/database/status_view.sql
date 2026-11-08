CREATE OR REPLACE VIEW transaction_status AS
SELECT
    fr.id,
    fr.pan,
    fr.processing_code,
    fr.amount,
    fr.currency,
    fr.stan,
    fr.rrn,
    fr.terminal_id,
    fr.merchant_id,
    fr.transmitted_at,
    fr.created_at,
    resp.resp_code,
    resp.auth_id_resp,
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM reversal_request rq
            JOIN reversal_response rs ON rs.reversal_req_id = rq.id
            WHERE rq.original_fin_req_id = fr.id AND rs.resp_code = '00'
        ) THEN 'reversed'
        WHEN resp.resp_code = '00' THEN 'approved'
        WHEN resp.resp_code IS NOT NULL THEN 'declined'
        ELSE 'pending'
    END AS status
FROM financial_request fr
LEFT JOIN LATERAL (
    SELECT r.resp_code, r.auth_id_resp
    FROM financial_response r
    WHERE r.request_id = fr.id
    ORDER BY r.id DESC
    LIMIT 1
) resp ON TRUE;
