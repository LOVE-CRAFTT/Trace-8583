import { useEffect, useState } from "react";
import "./index.css";

type Status = "approved" | "declined" | "reversed" | "pending";

// One row of GET /transactions (the transaction_status view)
type Transaction = {
  id: number;
  pan: string;
  processing_code: string;
  amount: number | string; // minor units
  currency: string;
  stan: string;
  rrn: string | null;
  terminal_id: string;
  merchant_id: string;
  transmitted_at: string;
  created_at: string;
  resp_code: string | null;
  auth_id_resp: string | null;
  status: Status;
};

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
const REFRESH_MS = 3000;
const RECENT_COUNT = 10;
const TOP_REASONS = 5;

const DECLINE_REASONS: Record<string, string> = {
  "05": "Do not honor",
  "14": "Invalid card number",
  "51": "Insufficient funds",
  "54": "Expired card",
  "55": "Incorrect PIN",
  "57": "Transaction not permitted",
  "61": "Exceeds withdrawal limit",
  "91": "Issuer unavailable",
  "96": "System malfunction",
};

const CURRENCIES: Record<string, string> = {
  "566": "NGN",
  "356": "INR",
  "840": "USD",
  "978": "EUR",
  "826": "GBP",
};

function formatAmount(amount: number | string, currency: string): string {
  const value = Number(amount) / 100; // minor units to major
  const code = CURRENCIES[currency] ?? currency;
  const text = value.toLocaleString("en", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${code} ${text}`;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-GB"); // 24 hour HH:MM:SS
}

function computeStats(rows: Transaction[]) {
  // Approval rate counts every transaction the issuer answered with 00,
  // including ones reversed later, over all transactions that got an answer.
  // Pending rows (no response yet) stay out of the denominator.
  const answered = rows.filter((r) => r.resp_code !== null);
  const approved = answered.filter((r) => r.resp_code === "00").length;
  return {
    total: rows.length,
    declined: rows.filter((r) => r.status === "declined").length,
    approvalRate: answered.length ? (approved / answered.length) * 100 : null,
  };
}

function topDeclineReasons(rows: Transaction[]): [string, number][] {
  const counts = new Map<string, number>();
  for (const row of rows) {
    if (row.status === "declined" && row.resp_code) {
      counts.set(row.resp_code, (counts.get(row.resp_code) ?? 0) + 1);
    }
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, TOP_REASONS);
}

export default function App() {
  const [rows, setRows] = useState<Transaction[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      try {
        const response = await fetch(`${API_URL}/transactions?limit=10000`, {
          signal: controller.signal,
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        setRows(await response.json());
        setError(null);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : "Request failed");
      }
    }

    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, []);

  const stats = computeStats(rows);
  const reasons = topDeclineReasons(rows);

  // The API returns rows newest first, so the head of the list is the most recent
  const recent = rows.slice(0, RECENT_COUNT);

  return (
    <div className="head">
      <h2 className="title">Trace_8583</h2>

      {error && (
        <div className="error-banner">
          Cannot reach the backend ({error}). Showing the last data received.
        </div>
      )}

      <div className="section-1">
        <OverviewCard title="Transactions" value={stats.total.toLocaleString()} />
        <OverviewCard
          title="Approval rate"
          value={
            stats.approvalRate === null ? "—" : `${stats.approvalRate.toFixed(1)}%`
          }
        />
        <OverviewCard title="Declined" value={stats.declined.toLocaleString()} />
      </div>

      <div className="section-2">
        <Declines reasons={reasons} />
      </div>

      <div className="section-3">
        <RecentTransactions rows={recent} />
      </div>
    </div>
  );
}

function OverviewCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="overview-card">
      <div className="special-text">{title}</div>
      <div className="card-value">{value}</div>
    </div>
  );
}

function Declines({ reasons }: { reasons: [string, number][] }) {
  const max = reasons[0]?.[1] ?? 1;

  return (
    <>
      <h4>Top decline reasons</h4>
      {reasons.length === 0 ? (
        <p className="muted">No declines yet</p>
      ) : (
        reasons.map(([code, count]) => (
          <div className="reason-row" key={code}>
            <span>
              {code} {DECLINE_REASONS[code] ?? "Declined"}
            </span>
            <div className="bar-track">
              <div
                className="bar-fill"
                style={{ width: `${(count / max) * 100}%` }}
              />
            </div>
            <span className="reason-count">{count}</span>
          </div>
        ))
      )}
    </>
  );
}

function StatusBadge({ row }: { row: Transaction }) {
  const labels: Record<Status, string> = {
    approved: `${row.resp_code} Approved`,
    declined: `${row.resp_code} Declined`,
    reversed: "Reversed",
    pending: "Pending",
  };
  return <span className={`badge badge-${row.status}`}>{labels[row.status]}</span>;
}

function RecentTransactions({ rows }: { rows: Transaction[] }) {
  return (
    <>
      <h4>Recent transactions</h4>
      {rows.length === 0 ? (
        <p className="muted">No transactions yet</p>
      ) : (
        <div className="table-wrap">
          <table className="transactions-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>STAN</th>
                <th>Terminal</th>
                <th>Amount</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>{formatTime(row.created_at)}</td>
                  <td>{row.stan}</td>
                  <td>{row.terminal_id}</td>
                  <td>{formatAmount(row.amount, row.currency)}</td>
                  <td>
                    <StatusBadge row={row} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
