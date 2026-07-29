"""Debug: check HTML for JS issues"""
import re

with open('C:/Users/rfuser/WorkBuddy/2026-07-24-15-41-07/exchange_rate_system/dist/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Check encrypted variables
for var in ['encRmb', 'encOrtax', 'encConverter', 'encCurrencies', 'encExcelFiles', 'authPassword']:
    m = re.search(r"var " + var + r" = '([^']*)'", html)
    if m:
        val = m.group(1)
        print(f"{var}: len={len(val)}")
        print(f"  start: {val[:60]}")
        print(f"  end: {val[-60:]}")
        # Check for problematic chars
        bad = [c for c in val if c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=']
        if bad:
            print(f"  WARNING: non-base64 chars: {set(bad)}")
        else:
            print(f"  OK: pure base64")
    else:
        print(f"{var}: NOT FOUND!")

# Extract the full <script> block and check for syntax issues
script_match = re.search(r'<script>(.*?)</script>', html, re.DOTALL)
if script_match:
    js = script_match.group(1)
    print(f"\n=== JS block length: {len(js)} ===")
    
    # Check basic JS syntax patterns
    # Check for unescaped quotes in strings
    print(f"checkAuth defined: {'function checkAuth' in js}")
    print(f"decryptAndInit defined: {'function decryptAndInit' in js}")
    print(f"xorDecrypt defined: {'function xorDecrypt' in js}")
    print(f"showLoading defined: {'function showLoading' in js}")
    print(f"TextDecoder used: {'TextDecoder' in js}")
    print(f"Uint8Array used: {'Uint8Array' in js}")
    
    # Check if the auto-init IIFE is present
    print(f"auto-init IIFE: {'sessionStorage.getItem' in js}")
    
    # Check for common JS errors
    # Count opening and closing braces
    open_braces = js.count('{')
    close_braces = js.count('}')
    print(f"\nbraces: open={open_braces}, close={close_braces}, balanced={open_braces == close_braces}")
    
    open_parens = js.count('(')
    close_parens = js.count(')')
    print(f"parens: open={open_parens}, close={close_parens}, balanced={open_parens == close_parens}")
    
    # Print the checkAuth function
    auth_start = js.find('function checkAuth')
    if auth_start >= 0:
        print(f"\n=== checkAuth function ===")
        print(js[auth_start:auth_start+500])
    
    # Print the decryptAndInit function
    dec_start = js.find('function decryptAndInit')
    if dec_start >= 0:
        print(f"\n=== decryptAndInit function ===")
        print(js[dec_start:dec_start+600])

    # Print the auto-init code
    init_start = js.find('// ===================== 初始化')
    if init_start >= 0:
        print(f"\n=== auto-init code ===")
        print(js[init_start:init_start+400])
else:
    print("No <script> block found!")
