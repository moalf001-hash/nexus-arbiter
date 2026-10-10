# NexusArbiter (v2.1.0-stable)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Network: Base Sepolia](https://img.shields.io/badge/Network-Base%20Sepolia%20%2884532%29-blue.svg)](https://sepolia.basescan.org)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-brightgreen.svg)](https://www.python.org/)
[![Security Audit: Bandit Clean](https://img.shields.io/badge/Security%20Audit-Bandit%20Clean-success.svg)](#security-audit--compliance)
[![CI Pipeline](https://github.com/moalf001-hash/nexus-arbiter/actions/workflows/ci.yml/badge.svg)](https://github.com/moalf001-hash/nexus-arbiter/actions/workflows/ci.yml)

**NexusArbiter** is an autonomous B2B clearinghouse and cryptographic escrow protocol designed for Agent-to-Agent (A2A) economic interactions on Ethereum Layer 2 networks, natively targeting **Base Sepolia**.

It connects off-chain negotiations between autonomous agents with on-chain settlement workflows, focusing on cryptographic identity, verifiable Proof of Delivery (PoD), buyer price commitment integrity, deterministic state transitions, and a secure agent capability marketplace.

> **Release:** `v2.1.0-stable`
>
> **Reported Security Status:** Static analysis completed (0 Bandit issues), CWE-89 mitigations implemented via strict SQL whitelisting, and a reported 100% test pass rate. These claims should be verified against current CI and audit reports before production use.

---

## 🌐 Live Gateway & Interactive Demos

Experience the protocol through the public deployment tunnel:

- 📊 **Live Telemetry Dashboard:** [Open Dashboard](https://converted-intersection-cove-basically.trycloudflare.com/dashboard)
- 📑 **Interactive Swagger UI:** [Open API Documentation](https://converted-intersection-cove-basically.trycloudflare.com/docs)

> **Availability Notice:** These endpoints use a Cloudflare temporary tunnel. Availability depends on the tunnel and backend server remaining active. The links have not been independently verified.

---

## Table of Contents

- [Live Gateway & Interactive Demos](#-live-gateway--interactive-demos)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Configuration](#environment-configuration)
- [Running the Platform](#running-the-platform)
- [Security Audit & Compliance](#security-audit--compliance)
- [Security Considerations](#security-considerations)
- [License](#license)

## Key Features

- **Cryptographic Identity:** Ed25519 digital signatures for message authentication and state transition verification.
- **Encrypted Negotiations:** X25519 key agreement for establishing shared secrets between agents in End-to-End Encrypted (E2EE) sessions.
- **Secure Marketplace Registry:** Cryptographically verified agent discovery (`/registry/register` and `/registry/search`) with SSRF defenses against private, loopback, and cloud-metadata endpoints.
- **Anti-Price Spoofing Guard:** Signed buyer price commitments designed to prevent unauthorized settlement amount modifications.
- **Deterministic Finite State Machine (FSM):** Enforces negotiation states, participant turn order, and permitted transitions.
- **Multi-Tenant B2B SaaS Authentication:** SHA-256 hashed API keys with monthly quota enforcement and sliding-window rate limiting.
- **Persistent Storage:** SQLite with Write-Ahead Logging (WAL) and strict SQL query whitelisting.
- **Settlement Preparation:** Generates unsigned Solidity-compatible calldata for `AgentEscrow.sol` on Base Sepolia.
- **Automated Invoicing:** Generates structured cryptographic invoices with an integrated 1.5% platform fee mechanism.

## System Architecture

```text id="cs14qy"
┌─────────────────────┐       ┌─────────────────────┐
│     Buyer Agent     │       │    Seller Agent     │
│   Ed25519 / X25519  │       │   Ed25519 / X25519  │
└──────────┬──────────┘       └──────────┬──────────┘
           │                             │
           └─────────────┬───────────────┘
                         │
                Signed Negotiations
                         │
                         ▼
          ┌────────────────────────────────┐
          │      NexusArbiter Gateway      │
          │            FastAPI             │
          ├────────────────────────────────┤
          │ Marketplace Discovery & SSRF   │
          │ Tenant Authentication          │
          │ Signature Verification         │
          │ FSM Transition Validation      │
          │ Price Commitment Checks        │
          │ Proof of Delivery (PoD)        │
          │ DoS & Rate Limit Enforcement   │
          └───────────────┬────────────────┘
                          │
                          ▼
          ┌────────────────────────────────┐
          │       Settlement Engine        │
          │   Invoice + Unsigned Calldata  │
          └───────────────┬────────────────┘
                          │
                          ▼
          ┌────────────────────────────────┐
          │        AgentEscrow.sol         │
          │      Base Sepolia (84532)      │
          ├────────────────────────────────┤
          │ Seller Payout                  │
          │ Platform Fee (1.5%)            │
          └────────────────────────────────┘
```

### Negotiation Lifecycle

1. **Propose:** Buyer initiates a signed negotiation.
2. **Counter:** Seller submits a signed counteroffer.
3. **Accept:** Buyer accepts the terms and establishes a price commitment.
4. **Deliver:** Seller submits the agreed deliverable and Proof of Delivery.
5. **Verify:** Gateway validates signatures, commitments, negotiation state, and delivery conditions.
6. **Settle:** Settlement engine prepares unsigned calldata for the escrow contract.

> Generating unsigned calldata does not itself execute or confirm an on-chain transaction.

## Project Structure

```text id="xw1cqg"
nexus-arbiter/
├── build/
│   └── AgentEscrow.json
├── scripts/
│   ├── comprehensive_security_audit.py
│   ├── demo_negotiation_e2e.py
│   ├── test_live_settlement.py
│   └── test_registry_security.py
├── src/
│   ├── api/
│   │   └── server.py
│   ├── arbiter/
│   │   └── verification.py
│   ├── auth/
│   │   ├── keys.py
│   │   └── middleware.py
│   ├── blockchain/
│   │   └── escrow_client.py
│   ├── core/
│   │   └── fsm.py
│   ├── invoicing/
│   │   └── invoice_generator.py
│   ├── registry/
│   │   └── discovery.py
│   ├── sdk/
│   │   └── agent_client.py
│   └── storage/
│       └── database.py
├── templates/
│   └── dashboard.html
├── tests/
│   └── test_protocol_suite.py
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11 or later
- Git
- A terminal or command-line environment
- Access to a Base Sepolia RPC endpoint for blockchain interactions

### 1. Clone the Repository

```bash id="5nwpv7"
git clone https://github.com/moalf001-hash/nexus-arbiter.git
cd nexus-arbiter
```

### 2. Create a Virtual Environment

**Windows (PowerShell):**

```powershell id="cph4md"
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux / macOS:**

```bash id="a6y7la"
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash id="d9wmw8"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Environment Configuration

Create a `.env` file from `.env.example`:

**Windows (PowerShell):**

```powershell id="8b5n1j"
Copy-Item .env.example .env
```

**Linux / macOS:**

```bash id="v02qlu"
cp .env.example .env
```

Configure the following environment variables:

```dotenv id="suxh5b"
ESCROW_CONTRACT_ADDRESS=0xF2D0F7cb12dF286ABba3683810E4228A4e72C61C
ARBITER_WALLET_ADDRESS=0x082b38aeA5D1bB7FEF3C16818f2E76809f2bA685
USDC_TOKEN_ADDRESS=0x036CbD53842c5426634e7929541eC2318f3dCF7e
RPC_URL=https://sepolia.base.org
CHAIN_ID=84532
```

### Environment Variables

| Variable | Description |
|---|---|
| `ESCROW_CONTRACT_ADDRESS` | Deployed escrow contract address |
| `ARBITER_WALLET_ADDRESS` | Arbiter wallet address |
| `USDC_TOKEN_ADDRESS` | USDC token contract address |
| `RPC_URL` | Base Sepolia JSON-RPC endpoint |
| `CHAIN_ID` | Network chain ID (`84532`) |

### Security Notes

- Never commit `.env` or private keys to GitHub.
- Keep sensitive credentials out of source code and logs.
- Verify contract addresses before interacting with the blockchain.
- Ensure `.gitignore` excludes database files (`*.db`), secret files, and virtual environments.
- Use secure secret management for production deployments.

## Running the Platform

### Start the API Gateway

```powershell id="hgz2ei"
uvicorn src.api.server:app --reload --port 8000
```

The `--reload` option is intended for local development.

### API Endpoints

| Service | Endpoint |
|---|---|
| Live Dashboard | [Public Dashboard](https://converted-intersection-cove-basically.trycloudflare.com/dashboard) |
| Live Swagger UI | [Public API Docs](https://converted-intersection-cove-basically.trycloudflare.com/docs) |
| Local Dashboard | http://127.0.0.1:8000/dashboard |
| Local Swagger UI | http://127.0.0.1:8000/docs |
| Local Health Check | http://127.0.0.1:8000/health |

### Run Verification & Test Suites

**1. Run the core protocol test suite:**

```powershell id="5xobzo"
pytest -v
```

**2. Run marketplace security and SSRF tests:**

```powershell id="szz9ud"
python scripts/test_registry_security.py
```

**3. Run static code security analysis (Bandit):**

```powershell id="1dxf2v"
bandit -r src/ -ll
```

**4. Run the comprehensive security audit:**

```powershell id="dv4mfo"
python scripts/comprehensive_security_audit.py
```

### Run the End-to-End Negotiation Demo

```powershell id="6c5kbu"
python scripts/demo_negotiation_e2e.py
```

Expected lifecycle:

```text id="v1v4dm"
Propose -> Counter -> Accept -> Deliver -> Settle
```

## Security Audit & Compliance

NexusArbiter documents a multi-layered security matrix.

| # | Security Domain | Implementation & Verification Details | Reported Status |
|---|---|---|---|
| 1 | **Payload Size Limits** | Enforces 128 KB maximum body size; returns HTTP 413 | PASSED |
| 2 | **SQL Injection (CWE-89)** | Strict table and column whitelisting on dynamic queries | VERIFIED |
| 3 | **SSRF Protection** | Rejects loopback, private IP, and link-local endpoints | PASSED |
| 4 | **Rate Limiting** | 60 requests/minute per IP; returns HTTP 429 | ACTIVE |
| 5 | **Signature Verification** | Ed25519 cryptographic authentication for protocol transitions | PASSED |
| 6 | **Price Spoofing Guard** | Buyer-signed price commitments for negotiation sessions | PASSED |
| 7 | **FSM State Integrity** | Deterministic sequence numbers and strict turn validation | PASSED |

> **Audit Notice:** The statuses above are project-reported. They should be verified through current test results and CI logs. Passing automated tests or static analysis does not establish that the protocol is free of vulnerabilities.

### Static Security Analysis

Run Bandit against the Python source directory:

```powershell id="2rm69e"
bandit -r src/ -ll
```

A clean Bandit result does not prove the absence of SQL injection, SSRF, cryptographic flaws, or other vulnerabilities.

### Continuous Integration

View the GitHub Actions workflow:

[GitHub Actions — CI Pipeline](https://github.com/moalf001-hash/nexus-arbiter/actions/workflows/ci.yml)

The CI badge requires an existing and correctly configured `.github/workflows/ci.yml` workflow.

## Security Considerations

- **Replay Protection:** Bind messages to unique session IDs, participants, and deterministic sequence counters.
- **Canonical Serialization:** Ensure signatures and price commitments use identical, stable JSON serialization.
- **Key Management:** Protect signing keys using hardware-backed storage or secure secrets managers where appropriate.
- **Database Concurrency:** Verify transactional integrity and quota enforcement under concurrent requests.
- **SSRF Protection:** Validate destination addresses, DNS resolution, and redirects, and restrict outbound network access.
- **Rate Limiting:** Configure trusted proxies and distributed limits for multi-instance deployments.
- **Smart Contract Security:** Review access controls, token handling, reentrancy risks, fee calculations, and failure recovery.
- **Settlement Verification:** Confirm transaction receipts and on-chain state before reporting successful settlement.
- **Production Operations:** Configure monitoring, logging, dependency scanning, and secure deployment practices.

## License

Distributed under the MIT License.

See the [LICENSE](LICENSE) file for the complete license terms.
