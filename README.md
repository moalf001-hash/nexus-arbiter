# 🛡️ NexusArbiter: Autonomous Escrow & Deterministic Arbitration Protocol

[![Base Sepolia](https://img.shields.io/badge/Network-Base%20Sepolia%20(L2)-blue)](https://sepolia.basescan.org/address/0xF2D0F7cb12dF286ABba3683810E4228A4e72C61C)
[![Contract Verified](https://img.shields.io/badge/BaseScan-Verified%20Contract-brightgreen)](https://sepolia.basescan.org/address/0xF2D0F7cb12dF286ABba3683810E4228A4e72C61C#code)
[![Solidity](https://img.shields.io/badge/Solidity-^0.8.20-lightgrey)](https://soliditylang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-v1.5.1-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An institutional-grade, non-custodial escrow and deterministic dispute resolution protocol engineered for autonomous AI agents engaging in machine-to-machine (M2M) service exchanges and micropayments.

---

## 🏛️ System Architecture

NexusArbiter decouples off-chain cryptographic negotiation from on-chain monetary settlement to achieve zero counterparty risk, sub-second execution, and low-cost Layer 2 finality.

+-----------------------------------------------------------------------------------+
|                              Off-Chain Agent Layer                                |
|                                                                                   |
|  [Buyer Agent] <--- Ed25519 Commitment Exchange ---> [Seller Agent]                |
|         \                                                    /                    |
|          \--- Signed Terms + SLA ---> [Arbiter API] <-------/                     |
+---------------------------------------------|-------------------------------------+
                                              | Deterministic PoD Verification
                                              v
+-----------------------------------------------------------------------------------+
|                          Base Sepolia L2 Smart Contract                           |
|                                                                                   |
|                      +-----------------------------+                              |
|                      |      AgentEscrow.sol        |                              |
|                      +-----------------------------+                              |
|                         /            |            \                               |
|          lockFunds() --/             |             \-- settleAndSplit()           |
|                                 refundBuyer()                                     |
|                                      |                                            |
|       [Buyer Refund] <---------------+---------------> [Seller Pay + 1.5% Cut]    |
+-----------------------------------------------------------------------------------+

---

## 🔒 Security Invariants & Verification Results

The protocol has undergone comprehensive threat modeling and negative invariant verification:

1. Reentrancy Immunity (CEI Pattern): The settleAndSplit routine implements strict Checks-Effects-Interactions, updating state storage to EscrowStatus.SETTLED prior to external ERC-20 token transfers.
2. Anti-Price Spoofing (Ed25519 Signatures): Off-chain commitments mandate raw cryptographic binding between session parameters, timestamps, and negotiated amounts, completely neutralizing replay and price-spoofing attacks.
3. Role & Modifier Boundaries: Core settlement and administrative paths are guarded on-chain via EVM modifiers (onlyArbiterOrBuyer and onlyPlatformOwner), deterministically reverting unauthorized fund drain attempts (EVM Revert: Unauthorized).
4. Deterministic SLA Enforcement: Guarantees programmatic buyer recovery via refundBuyer upon breach of delivery SLAs without centralized manual intervention.

---

## 🚀 Live On-Chain Deployment

| Parameter | Value |
| :--- | :--- |
| Network | Base Sepolia (Ethereum L2) |
| Chain ID | 84532 |
| Contract Address | 0xF2D0F7cb12dF286ABba3683810E4228A4e72C61C |
| Deployment Tx | 0x579498566fa868f66f3b5dc103b76a8e34a6d5b9e379697530a9fc19b699f9ab |
| Contract Status | Verified Public Source Code (Exact Bytecode Match) |
| Settlement Token | Testnet USDC (0x036CbD53842c5426634e7929541eC2318f3dCF7e) |
| Protocol Take Rate | 1.5% platform cut dynamically routed upon proof of delivery |

---

## ⚡ Quickstart & Local Reproduction

### 1. Installation
git clone https://github.com/moalf001-hash/nexus-arbiter.git
cd nexus-arbiter

python -m venv venv
# On Windows:
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt

### 2. Launch Arbiter Gateway & Dashboard
uvicorn src.api.server:app --reload --port 8000
- Interactive Operations Dashboard: http://127.0.0.1:8000/dashboard
- Swagger API Specifications: http://127.0.0.1:8000/docs

### 3. Run Autonomous Simulation & Security Audits
# Execute end-to-end M2M agent negotiation and escrow settlement
python run_full_simulation.py

# Execute negative security edge cases and static verification suite
python scripts/verify_edge_cases.py
python scripts/static_analysis_audit.py

---

## 📄 License
Distributed under the MIT License. See LICENSE for details.