import os
import sys
import json
from qwed_ucp.core import UCPVerifier

def main():
    # 1. Capture Inputs
    # GitHub Actions passes inputs as arguments or env vars. 
    # Composite uses env vars usually. Docker args usage:
    # args: ${{ inputs.transaction-file }} -> sys.argv[1]
    
    if len(sys.argv) < 2:
        print("❌ Error: Missing transaction-file argument")
        sys.exit(1)
        
    file_path = sys.argv[1]
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
