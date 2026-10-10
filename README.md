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
> **Reported Security Status:** Static analysis completed with 0 Bandit issues, CWE-89 mitigations implemented through SQL whitelisting, and a reported 100% test pass rate. These results should be confirmed against the latest CI logs and test reports before production deployment.

## Table of Contents

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
- **Secure Marketplace Registry:** Cryptographically verified agent discovery through `/registry/register` and `/registry/search`, with SSRF defenses against private, loopback, and cloud-metadata endpoints.
- **Anti-Price Spoofing Guard:** Cryptographically signed buyer price commitments designed to prevent unauthorized settlement amount modifications.
- **Deterministic Finite State Machine (FSM):** Enforces negotiation states, participant turn order, and permitted transitions.
- **Multi-Tenant B2B SaaS Authentication:** SHA-256 hashed API keys, monthly quota enforcement, and sliding-window rate limiting.
- **Persistent Storage:** SQLite database using Write-Ahead Logging (WAL) and strict SQL query whitelisting.
- **Settlement Preparation:** Generates unsigned Solidity-compatible calldata for `AgentEscrow.sol` on Base Sepolia.
- **Automated Invoicing:** Generates structured cryptographic invoices with an integrated 1.5% platform fee mechanism.

## System Architecture

```text
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

1. **Propose:** The buyer initiates a signed negotiation.
2. **Counter:** The seller submits a signed counteroffer.
3. **Accept:** The buyer accepts the terms and establishes a signed price commitment.
4. **Deliver:** The seller submits the agreed deliverable and its Proof of Delivery.
5. **Verify:** The gateway validates signatures, FSM transitions, commitments, and applicable delivery conditions.
6. **Settle:** The settlement engine prepares unsigned calldata for the escrow contract.

> **Note:** Generating unsigned calldata does not itself execute or confirm an on-chain transaction.

## Project Structure

```text
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

```bash
git clone https://github.com/moalf001-hash/nexus-arbiter.git
cd nexus-arbiter
```

### 2. Create a Virtual Environment

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**

```bat
python -m venv venv
venv\Scripts\activate.bat
```

**Linux / macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Environment Configuration

Create a `.env` file from `.env.example`.

**Windows (PowerShell):**

```powershell
Copy-Item .env.example .env
```

**Linux / macOS:**

```bash
cp .env.example .env
```

Configure the following environment variables:

```dotenv
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
- Keep sensitive credentials out of source code and application logs.
- Verify contract addresses before blockchain interactions.
- Ensure `.gitignore` excludes database files (`*.db`), secret files, and virtual environments.
- Use secure secret management for production environments.

## Running the Platform

### Start the API Gateway

```powershell
uvicorn src.api.server:app --reload --port 8000
```

The `--reload` flag is intended for development environments.

### API Endpoints

| Endpoint | URL |
|---|---|
| Swagger UI | http://127.0.0.1:8000/docs |
| ReDoc | http://127.0.0.1:8000/redoc |
| Dashboard | http://127.0.0.1:8000/dashboard |
| Health Check | http://127.0.0.1:8000/health |

These endpoints require the application to expose the corresponding routes.

### Run Verification & Test Suites

**1. Run the core protocol test suite:**

```powershell
pytest -v
```

**2. Run marketplace security and SSRF tests:**

```powershell
python scripts/test_registry_security.py
```

**3. Run static code security analysis with Bandit:**

```powershell
bandit -r src/ -ll
```

**4. Run the comprehensive security audit:**

```powershell
python scripts/comprehensive_security_audit.py
```

### Run the End-to-End Negotiation Demo

```powershell
python scripts/demo_negotiation_e2e.py
```

Expected negotiation lifecycle:

```text
Propose -> Counter -> Accept -> Deliver -> Settle
```

### Run Settlement Tests

```powershell
python scripts/test_live_settlement.py
```

> **Warning:** Review the settlement test implementation and configured network before running it. Depending on the implementation, this script may interact with a blockchain and incur transaction fees.

## Security Audit & Compliance

NexusArbiter documents a multi-layered security testing matrix covering the following areas.

| # | Security Domain | Implementation & Verification Details | Reported Status |
|---|---|---|---|
| 1 | Payload Size Limits | Enforces a 128 KB maximum request body size; returns HTTP 413 | PASSED |
| 2 | SQL Injection (CWE-89) | Strict table and column whitelisting on dynamic queries | VERIFIED |
| 3 | SSRF Protection | Rejects loopback, private IP, and link-local endpoints | PASSED |
| 4 | Rate Limiting | 60 requests/minute per IP; returns HTTP 429 | ACTIVE |
| 5 | Signature Verification | Ed25519 cryptographic authentication for protocol transitions | PASSED |
| 6 | Price Spoofing Guard | Buyer-signed price commitments for negotiation sessions | PASSED |
| 7 | FSM State Integrity | Deterministic sequence numbers and strict turn validation | PASSED |

> **Verification Notice:** The statuses above are project-reported. Re-run the relevant tests and inspect CI artifacts before relying on these results. Static analysis and automated tests are not substitutes for an independent security assessment.

### Static Analysis

Bandit can be used to inspect the Python source tree for selected security-related patterns:

```powershell
bandit -r src/ -ll
```

A clean Bandit result does not prove the absence of SQL injection, SSRF, cryptographic flaws, or other vulnerabilities.

### Continuous Integration

The repository references a GitHub Actions workflow:

[View CI Pipeline](https://github.com/moalf001-hash/nexus-arbiter/actions/workflows/ci.yml)

The CI badge reflects the workflow status only when `.github/workflows/ci.yml` exists and GitHub Actions is configured correctly.

## Security Considerations

- **Replay Protection:** Bind messages to unique session IDs, participants, and deterministic sequence counters.
- **Canonical Serialization:** Ensure signatures and price commitments use identical, stable JSON serialization rules.
- **Key Management:** Protect signing keys using secure secret managers or hardware-backed key storage where appropriate.
- **Database Concurrency:** Verify transaction isolation, quota enforcement, and integrity under concurrent requests.
- **SSRF Protection:** Validate resolved destination IP addresses and redirects, and restrict outbound network access where possible.
- **Rate Limiting:** Consider trusted proxy configuration and distributed rate limiting for multi-instance deployments.
- **Smart Contract Security:** Review access controls, reentrancy, token handling, fee calculations, and transaction failure scenarios.
- **Settlement Verification:** Confirm transaction receipts and the required on-chain state before reporting settlement as successful.
- **Operational Security:** Use dependency scanning, audit logging, monitoring, and secure deployment configuration.

## License

Distributed under the MIT License.

See the [LICENSE](LICENSE) file for the complete license terms.
