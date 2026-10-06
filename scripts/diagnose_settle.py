import pathlib
import re

print("=========================================================")
print("        NexusArbiter Settle Endpoint Security Audit      ")
print("=========================================================")

# 1. البحث عن نقطة النهاية /settle في كود الـ API
routes_dir = pathlib.Path("src/api")
found = False

for py_file in routes_dir.rglob("*.py"):
    content = py_file.read_text(encoding="utf-8")
    if "/settle" in content or "arbiter/settle" in content:
        print(f"\n[+] Found settle endpoint logic in: {py_file}")
        lines = content.splitlines()
        for idx, line in enumerate(lines, 1):
            if any(k in line for k in ["403", "status_code", "FORBIDDEN", "def settle", "FSM", "state"]):
                print(f"  Line {idx:3d}: {line}")
        found = True

# 2. فحص استدعاء submit_and_settle في SDK
sdk_file = pathlib.Path("src/sdk/agent_client.py")
if sdk_file.exists():
    print(f"\n[+] Inspecting SDK: {sdk_file}")
    lines = sdk_file.read_text(encoding="utf-8").splitlines()
    for idx, line in enumerate(lines, 1):
        if 215 <= idx <= 235:
            print(f"  Line {idx:3d}: {line}")

# 3. فحص سيناريو المحاكاة حول السطر 173
sim_file = pathlib.Path("scripts/simulate_autonomous_agents.py")
if sim_file.exists():
    print(f"\n[+] Inspecting Simulation: {sim_file}")
    lines = sim_file.read_text(encoding="utf-8").splitlines()
    for idx, line in enumerate(lines, 1):
        if 165 <= idx <= 185:
            print(f"  Line {idx:3d}: {line}")

print("\n=========================================================")