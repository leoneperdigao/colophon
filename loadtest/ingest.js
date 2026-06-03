// k6 ingestion-plane load test — POST /documents under concurrent load.
//
// Verifies the *accept path* stays fast under burst (it only writes raw, creates
// the job, and enqueues — processing is decoupled). See ADR-0010 for the full
// strategy (processing-plane throughput, chaos, SLOs).
//
// Run (with the stack up and a sample present):
//   uv run python samples/download_samples.py
//   k6 run -e BASE_URL=http://localhost:8000 -e TOKEN=tokenA loadtest/ingest.js

import http from 'k6/http';
import { check } from 'k6';

export const options = {
  scenarios: {
    ramp_uploads: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 50 },
        { duration: '1m', target: 50 },
        { duration: '30s', target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_duration: ['p(99)<500'], // SLO: p99 accept latency < 500ms
    http_req_failed: ['rate<0.01'], // SLO: < 1% accept errors
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const TOKEN = __ENV.TOKEN || 'tokenA';
const PDF = open('../samples/downloaded/pdf-text-simple.pdf', 'b');

export default function () {
  const res = http.post(
    `${BASE_URL}/documents`,
    { file: http.file(PDF, 'doc.pdf', 'application/pdf') },
    { headers: { Authorization: `Bearer ${TOKEN}` } },
  );
  check(res, { 'accepted (202)': (r) => r.status === 202 });
}
