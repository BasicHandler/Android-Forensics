#!/usr/bin/env python3
import os
import sys
import hashlib
import time

def print_banner():
    GREEN = '\033[92m'
    ORANGE = '\033[38;5;208m'
    RESET = '\033[0m'
    print(f"{GREEN}+++ BINO MELBINO CONTACT CLEANSE v2.4 +++{RESET}")
    print(f"{ORANGE}Deep Property Audit - Universal Migration Protocol{RESET}")

def cleanse_vcf_lines(lines):
    cleansed_lines = []
    in_vcard = False
    stats = {
        "scanned": 0,
        "stripped_vendor": 0,
        "stripped_keys": 0,
        "orphans_killed": 0,
        "bit_rot_purged": 0,
        "audit_log": []
    }
    
    PROSCRIBED_PREFIXES = ('X-', 'GOOGLE-', 'X-MS-', 'X-SAMSUNG-', 'X-PHONETIC-')
    PROSCRIBED_KEYS = ('UID', 'REV', 'PRODID', 'PHOTO', 'VERSION')

    for line in lines:
        stats["scanned"] += 1
        # Normalize encoding and fix Samsung/Windows line endings
        line = line.replace('\ufeff', '').replace('\r\n', '\n')
        stripped = line.strip()
        
        if not stripped:
            continue

        # Case-Insensitive Structural Lock
        upper_stripped = stripped.upper()
        if upper_stripped.startswith('BEGIN:VCARD'):
            in_vcard = True
            cleansed_lines.append("BEGIN:VCARD\n")
            cleansed_lines.append("VERSION:3.0\n") 
            continue
        elif upper_stripped.startswith('END:VCARD'):
            in_vcard = False
            cleansed_lines.append("END:VCARD\n")
            continue

        # Bit-Rot Guard with Folding Support
        if ':' not in stripped:
            # Keep folded lines (start with space/tab) if we are inside a vCard
            if line.startswith((' ', '\t')) and in_vcard:
                cleansed_lines.append(line)
                continue
            stats["bit_rot_purged"] += 1
            continue

        # Kill orphan metadata sitting outside BEGIN/END blocks
        if not in_vcard:
            stats["orphans_killed"] += 1
            continue

        # Property Audit
        parts = stripped.split(':', 1)
        key_section = parts[0].upper()
        # Handle parameters (e.g. 'TEL;TYPE=CELL')
        base_key = key_section.split(';', 1)[0]
        
        if any(base_key.startswith(p) for p in PROSCRIBED_PREFIXES):
            stats["stripped_vendor"] += 1
            stats["audit_log"].append(f"REMOVED_VENDOR_EXT: {base_key}")
            continue
            
        if base_key in PROSCRIBED_KEYS:
            stats["stripped_keys"] += 1
            stats["audit_log"].append(f"REMOVED_ID: {base_key}")
            continue

        cleansed_lines.append(line if line.endswith('\n') else line + '\n')
    
    return cleansed_lines, stats

def main():
    print_banner()
    while True:
        target = input("Target VCF location: ").strip().strip('"\'')
        if os.path.isfile(target): break
        print(f"File not found: {target}")
    
    # Force UTF-8-sig to handle Samsung BOM markers
    try:
        with open(target, 'r', encoding='utf-8-sig', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Read Error: {e}"); return
    
    print(f"Audit started on {len(lines)} lines...")
    cleansed_lines, stats = cleanse_vcf_lines(lines)
    
    if not cleansed_lines:
        print("\n[!] Audit Failure: Zero lines matched the VCARD structure.")
        # Diagnostic: peek at the first line
        if lines:
            print(f"    Sample line 1: {repr(lines[0][:30])}")
        return

    ts = int(time.time())
    output_file = os.path.join(os.path.dirname(os.path.abspath(target)), f"sanitized_{ts}.vcf")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(cleansed_lines)
    
    print(f"\nAudit Success: {output_file}")
    print(f"Purged: {stats['bit_rot_purged']} rot, {stats['stripped_vendor']} vendor bloat.")

if __name__ == "__main__":
    main()
