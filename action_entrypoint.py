import os
import sys
import json
from qwed_ucp.core import UCPVerifier


def _safe_resolve(path: str) -> str:
    """Resolve and validate path against the sandbox base directory.

    In GitHub Actions, the canonical sandbox is $GITHUB_WORKSPACE. Locally,
    fall back to the current working directory. Reject any path that escapes
    the sandbox after resolving ../, symlinks, and relative components.

    Prevents partial path traversal by ensuring the base dir ends with the
    OS separator before the startswith check (e.g. so "/data/resources-evil"
    does not match "/data/resources").
    """
    base = os.path.realpath(os.environ.get("GITHUB_WORKSPACE") or os.getcwd())
    # Ensure trailing separator so "/foo" does not match "/foo-evil"
    if not base.endswith(os.sep):
        base = base + os.sep
    # Join relative inputs to the sandbox base before resolving so they
    # resolve against $GITHUB_WORKSPACE, not the process cwd (Docker
    # container uses WORKDIR /app which differs from the workspace).
    if os.path.isabs(path):
        resolved = os.path.realpath(path)
    else:
        resolved = os.path.realpath(os.path.join(base, path))
    if resolved != base[:-1] and not resolved.startswith(base):
        raise ValueError(
            f"path {path!r} resolves to {resolved!r} which is outside the "
            f"allowed sandbox {base!r}"
        )
    return resolved


def main():
    # 1. Capture Inputs
    # GitHub Actions passes inputs as arguments or env vars.
    # Composite uses env vars usually. Docker args usage:
    # args: ${{ inputs.transaction-file }} -> sys.argv[1]

    if len(sys.argv) < 2:
        print("❌ Error: Missing transaction-file argument")
        sys.exit(1)

    try:
        file_path = _safe_resolve(sys.argv[1])
    except ValueError as e:
        print(f"❌ Security: {e}")
        sys.exit(1)
    print(f"🚀 Starting UCP Audit on: {file_path}")

    if not os.path.exists(file_path):
        print(f"❌ Error: File not found: {file_path}")
        sys.exit(1)

    # 2. Load Transactions
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Support list of transactions or single object
        transactions = data if isinstance(data, list) else [data]
        if any(not isinstance(txn, dict) for txn in transactions):
            raise ValueError("All transactions must be JSON objects")

    except Exception as e:
        print(f"❌ JSON Load Error: {e}")
        sys.exit(1)

    # 3. Verify
    verifier = UCPVerifier(strict_mode=True)
    failures = 0

    print(f"{'ID':<20} | {'Status':<10} | {'Error'}")
    print("-" * 60)

    for i, txn in enumerate(transactions):
        txn_id = txn.get("id", f"TXN_{i}")
        
        # Determine what to verify (Checkout or arbitrary)
        # UCPVerifier expects a checkout object.
        result = verifier.verify_checkout(txn)
        
        if result.verified:
            print(f"{txn_id:<20} | ✅ PASS     | -")
        else:
            print(f"{txn_id:<20} | 🛑 FAIL     | {result.error}")
            failures += 1
            
            # Write failure detail to GitHub Output
            with open(os.environ.get('GITHUB_STEP_SUMMARY', 'summary.md'), 'a') as f:
                 f.write(f"### 🛑 Blocked Transaction: {txn_id}\n")
                 f.write(f"- **Reason:** {result.error}\n")
                 f.write(f"- **Guards:** {result}\n")

    # 4. Final Verdict
    if failures > 0:
        print(f"\n❌ Audit Failed: Blocked {failures} illegal transactions.")
        sys.exit(1)
    else:
        print("\n✅ Audit Passed: All transactions look clean.")
        sys.exit(0)

if __name__ == "__main__":
    main()
