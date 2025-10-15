# API Endpoints

## Wolfram Scorer (stub)
- `POST /score`
  - Body: `{ "license_status": "active|expired|revoked", "type": "..." }`
  - Response: `{ "risk_score": float, "explanations": [str, ...] }`
