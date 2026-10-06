import os
import sys
import json
import subprocess
from pathlib import Path
import requests

# روابط التحميل الرسمية والمباشرة للمترجم
DOWNLOAD_URLS = [
    "https://github.com/ethereum/solidity/releases/download/v0.8.20/solc-windows.exe",
    "https://binaries.soliditylang.org/windows-amd64/solc-windows-amd64-v0.8.20+commit.a1b79de6.exe"
]
SOLC_EXE = Path("solc.exe")

def ensure_compiler():
    """تحميل المترجم تلقائياً في مجلد المشروع في حال عدم وجوده"""
    if SOLC_EXE.exists():
        print("[+] solc.exe is already present.")
        return

    print("[*] Downloading official solc compiler v0.8.20...")
    for url in DOWNLOAD_URLS:
        try:
            print(f"[*] Trying: {url}")
            resp = requests.get(url, stream=True, allow_redirects=True, timeout=60)
            if resp.status_code == 200:
                with open(SOLC_EXE, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                print("[+] Successfully downloaded solc.exe!")
                return
        except Exception as e:
            print(f"[-] Failed with {url}: {e}")
            continue

    raise RuntimeError("Could not download solc compiler from any official source.")

def compile_and_build():
    ensure_compiler()

    contract_path = Path("contracts/AgentEscrow.sol")
    build_dir = Path("build")
    build_dir.mkdir(exist_ok=True)

    print(f"[*] Compiling {contract_path}...")
    
    # تشغيل أمر التجميع مباشرة لاستخراج الـ Bytecode والـ ABI
    cmd = [
        str(SOLC_EXE.resolve()),
        str(contract_path),
        "--bin",
        "--abi",
        "--optimize",
        "-o",
        str(build_dir),
        "--overwrite"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[-] Compilation error:\n{result.stderr}")
        sys.exit(1)

    bin_path = build_dir / "AgentEscrow.bin"
    abi_path = build_dir / "AgentEscrow.abi"

    if not bin_path.exists() or not abi_path.exists():
        print("[-] Could not find compiled output files.")
        sys.exit(1)

    with open(abi_path, "r", encoding="utf-8") as f:
        abi = json.load(f)
        
    with open(bin_path, "r", encoding="utf-8") as f:
        bytecode = f.read().strip()

    if not bytecode.startswith("0x"):
        bytecode = "0x" + bytecode

    # حفظ الملف النهائي المكتمل
    artifact = {
        "contractName": "AgentEscrow",
        "abi": abi,
        "bytecode": bytecode
    }

    final_artifact_path = build_dir / "AgentEscrow.json"
    with open(final_artifact_path, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2)

    print("\n=========================================================")
    print(f"[+] COMPILATION COMPLETE!")
    print(f"    - Target File   : {final_artifact_path}")
    print(f"    - Bytecode Size : {len(bytecode)} characters")
    print(f"    - ABI Functions : {len(abi)}")
    print("=========================================================")

if __name__ == "__main__":
    compile_and_build()