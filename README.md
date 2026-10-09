
# NexusArbiter (v2.0.0)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Network: Base Sepolia](https://img.shields.io/badge/Network-Base%20Sepolia%20\(84532\)-blue.svg)](https://sepolia.basescan.org)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-brightgreen.svg)](https://www.python.org/)
[![CI Pipeline](https://github.com/moalf001-hash/nexus-arbiter/actions/workflows/ci.yml/badge.svg)](https://github.com/moalf001-hash/nexus-arbiter/actions/workflows/ci.yml)

**NexusArbiter** is an autonomous B2B clearinghouse and cryptographic escrow protocol designed for Agent-to-Agent (A2A) economic interactions on Ethereum Layer 2 networks, initially targeting **Base Sepolia**.

It connects off-chain negotiations between autonomous agents with on-chain settlement workflows, focusing on cryptographic identity, Proof of Delivery (PoD), price commitment integrity, and deterministic state transitions.

> **Status:** Development and testing project. Security and production readiness have not been independently verified.

## Table of Contents

* [Key Features](#key-features)
* [System Architecture](#system-architecture)
* [Project Structure](#project-structure)
* [Getting Started](#getting-started)
* [Environment Configuration](#environment-configuration)
* [Running the Platform](#running-the-platform)
* [Security Audit](#security-audit)
* [Security Considerations](#security-considerations)
* [License](#license)

## Key Features

* **Cryptographic Identity:** Ed25519 digital signatures for message authentication and state transition verification.
* **Encrypted Negotiations:** X25519 key agreement for establishing shared secrets between agents.
* **Anti-Price Spoofing:** Signed price commitments designed to prevent unauthorized settlement amount changes.
* **Deterministic Finite State Machine (FSM):** Enforces negotiation states, participant roles, and permitted transitions.
* **Multi-Tenant API:** Tenant-aware authentication and rate limiting.
* **Persistent Storage:** SQLite database with Write-Ahead Logging (WAL) mode.
* **Settlement Preparation:** Generates unsigned Solidity-compatible calldata for escrow transactions.
* **Invoice Generation:** Supports structured invoice generation and a platform fee intended to be 1.5%.

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
          ┌──────────────────────────────┐
          │     NexusArbiter Gateway     │
          │           FastAPI            │
          ├──────────────────────────────┤
          │ Tenant Authentication        │
          │ Signature Verification       │
          │ FSM Transition Validation    │
          │ Price Commitment Checks      │
          │ Proof of Delivery Verification│
          │ SLA and Quota Enforcement     │
          └──────────────┬───────────────┘
                         │
                         ▼
          ┌──────────────────────────────┐
          │     Settlement Preparation   │
          │  Invoice + Unsigned Calldata │
          └──────────────┬───────────────┘
                         │
                         ▼
          ┌──────────────────────────────┐
          │      AgentEscrow.sol         │
          │   Base Sepolia (84532)       │
          ├──────────────────────────────┤
          │ Seller Payout                │
          │ Platform Fee                 │
          └──────────────────────────────┘
```

## Project Structure

```text
nexus-arbiter/
├── build/
│   └── AgentEscrow.json
├── scripts/
│   ├── comprehensive_security_audit.py
│   └── demo_negotiation_e2e.py
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
│   ├── sdk/
│   │   └── agent_client.py
│   └── storage/
│       └── database.py
├── templates/
│   └── dashboard.html
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Getting Started

### Prerequisites

* Python 3.11 or later
* Git
* A terminal or command-line environment
* Access to a Base Sepolia RPC endpoint for blockchain interactions

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

**Linux / macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Environment Configuration

Create a `.env` file from `.env.example`:

```powershell
Copy-Item .env.example .env
```

Configure the following environment variables in `.env`:

```dotenv
ESCROW_CONTRACT_ADDRESS=0xF2D0F7cb12dF286ABba3683810E4228A4e72C61C
ARBITER_WALLET_ADDRESS=0x082b38aeA5D1bB7FEF3C16818f2E76809f2bA685
USDC_TOKEN_ADDRESS=0x036CbD53842c5426634e7929541eC2318f3dCF7e
RPC_URL=https://sepolia.base.org
CHAIN_ID=84532
```

| Variable                  | Description                      |
| ------------------------- | -------------------------------- |
| `ESCROW_CONTRACT_ADDRESS` | Deployed escrow contract address |
| `ARBITER_WALLET_ADDRESS`  | Arbiter wallet address           |
| `USDC_TOKEN_ADDRESS`      | USDC token contract address      |
| `RPC_URL`                 | Base Sepolia JSON-RPC endpoint   |
| `CHAIN_ID`                | Network chain ID (`84532`)       |

**Security notes:**

* Never commit `.env` or private keys to GitHub.
* Keep sensitive credentials out of source code.
* Verify all contract addresses before interacting with the blockchain.
* Ensure `.gitignore` excludes secret files and virtual environments.

## Running the Platform

### Start the API Gateway

```powershell
uvicorn src.api.server:app --reload --port 8000
```

### API Endpoints

* **Swagger UI:** http://127.0.0.1:8000/docs
* **ReDoc:** http://127.0.0.1:8000/redoc
* **Dashboard:** http://127.0.0.1:8000/dashboard

These endpoints require the application to expose the corresponding routes.

### Run the End-to-End Negotiation Demo

```powershell
python scripts/demo_negotiation_e2e.py
```

Expected lifecycle:

```text
Propose -> Counter -> Accept -> Deliver -> Settle
```

### Run the Security Audit

```powershell
python scripts/comprehensive_security_audit.py
```

## Security Audit

The project includes a test suite intended to cover seven security-related areas.

| # | Security Check             | Expected Behavior                                        |
| - | -------------------------- | -------------------------------------------------------- |
| 1 | Payload Size Limits        | Reject oversized requests with HTTP 413 where configured |
| 2 | SQL Injection Resistance   | Use parameterized queries                                |
| 3 | Atomic Quota Enforcement   | Prevent quota bypasses under concurrent requests         |
| 4 | Signature Verification     | Reject invalid Ed25519 signatures                        |
| 5 | Price Commitment Integrity | Detect unauthorized settlement amount changes            |
| 6 | FSM Role Integrity         | Enforce valid state transitions and participant roles    |
| 7 | SLA Deadline Enforcement   | Reject deliveries that violate configured deadlines      |

> **Note:** These are intended test cases, not independently verified results. Report successful checks only after running and reviewing the test suite.

## Security Considerations

* **Replay Protection:** Bind messages to sessions, participants, and unique nonces or sequence numbers.
* **Canonical Serialization:** Ensure signatures and commitments use identical data representations.
* **Key Management:** Protect signing keys and use secure key derivation and authenticated encryption.
* **Database Concurrency:** Test quota enforcement under concurrent requests.
* **Smart Contract Security:** Review access controls, token transfers, fee calculations, and failure handling.
* **Settlement Verification:** Confirm transaction receipts and on-chain state before reporting settlement as complete.
* **Invoice Compliance:** Verify tax and invoicing requirements for the applicable jurisdiction.
* **Production Deployment:** Configure monitoring, secret management, dependency updates, and API rate limits.

Cryptographic algorithms alone do not guarantee protocol security. Correct implementation and secure key management are also required.

## License

This project is intended to be distributed under the MIT License.

See the [MIT License](https://opensource.org/licenses/MIT) for details. Ensure the repository contains a `LICENSE` file with the appropriate license text.
