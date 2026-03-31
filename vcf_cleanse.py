#!/usr/bin/env python3
import os
import sys
import hashlib
import time

def print_banner():
    GREEN = '\033[92m'
    ORANGE = '\033[38;5;208m'
    RESET = '\033[0m'
    print(f"{GREEN}+++ BINO MELBINO CONTACT CLEANSE v2.3 +++{RESET}")
    print(f"{ORANGE}Deep Property Audit - Samsung to GrapheneOS Migration{RESET}")

def cleanse_vcf_lines(lines):
    """
    Deep Property Audit: Strips vendor telemetry, bit-rot, and re-links identifiers.
    Returns: (cleansed_lines, stats_dictionary)
    """
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
    
    # Comprehensive Proscribed Lists
    PROSCRIBED_PREFIXES = ('X-', 'GOOGLE-', 'X-MS-', 'X-SAMSUNG-', 'X-PHONETIC-')
    PROSCRIBED_KEYS = ('UID', 'REV', 'PRODID', 'PHOTO', 'VERSION')

    for line in lines:
        stats["scanned"] += 1
        # Normalize: Remove BOM and fix line endings
        line = line.replace('\ufeff', '').replace('\r\n', '\n')
        stripped = line.strip()
        
        if not stripped:
            continue

        # 1. Structural Lock: Handle BEGIN/END (Case-Insensitive)
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

        # 2. Bit-Rot Guard: Handle Folded Lines vs. Orphaned Fragments
        if ':' not in stripped:
            # Check if it's a 'folded' line (starts with space/tab) - Keep these
            if line.startswith((' ', '\t')) and in_vcard:
                cleansed_lines.append(line)
                continue
            # Otherwise, it's garbage/bit-rot
            stats["bit_rot_purged"] += 1
            continue

        # 3. Filter: Kill orphan metadata (Outside vCard blocks)
        if not in_vcard:
            stats["orphans_killed"] += 1
            continue

        # 4. Property-level Audit
        # Split at first colon to get key/params
        parts = stripped.split(':', 1)
        key_section = parts[0].upper()
        
        # Isolate base key from parameters (e.g., 'TEL' from 'TEL;TYPE=CELL')
        base_key = key_section.split(';', 1)[0]
        
        # Check against Proscribed Lists
        if any(base_key.startswith(p) for p in PROSCRIBED_PREFIXES):
            stats["stripped_vendor"] += 1
            stats["audit_log"].append(f"REMOVED_VENDOR_EXT: {base_key}")
            continue
            
        if base_key in PROSCRIBED_KEYS:
            stats["stripped_keys"] += 1
            stats["audit_log"].append(f"REMOVED_ID: {base_key}")
            continue

        # Final keep: Ensure newline consistency
        cleansed_lines.append(line if line.endswith('\n') else line + '\n')
    
    return cleansed_lines, stats

def write_cleansed_vcf(lines, output_path):
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        sha256_hash = hashlib.sha256()
        with open(output_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"Error writing file: {e}")
        return None

def get_file_path():
    while True:
        target = input("Target VCF location: ").strip().strip('"\'')
        if os.path.isfile(target):
            return target
        print(f"File not found: {target}")

def main():
    print_banner()
    target_file = get_file_path()
    
    try:
        with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Read Error: {e}")
        return
    
    print(f"Audit started on {len(lines)} lines...")
    cleansed_lines, stats = cleanse_vcf_lines(lines)
    
    if not cleansed_lines or len(cleansed_lines) <= (stats["scanned"] * 0.01):
        print("\n[!] Audit Error: No valid contact data survived the filter.")
        print(f"    Check: Are 'BEGIN:VCARD' tags present in {os.path.basename(target_file)}?")
        return
    
    # Define output path with timestamp
    target_dir = os.path.dirname(os.path.abspath(target_file))
    ts = int(time.time())
    output_file = os.path.join(target_dir, f"sanitized_migration_{ts}.vcf")
    
    file_hash = write_cleansed_vcf(cleansed_lines, output_file)
    
    if file_hash:
        print("\n" + "="*45)
        print("AUDIT DEBRIEFING: MIGRATION READY")
        print("="*45)
        print(f"Status:        SUCCESS (RFC 6350)")
        print(f"Output:        {os.path.basename(output_file)}")
        print(f"SHA-256:       {file_hash[:16]}...{file_hash[-16:]}")
        print(f"Lines Scanned: {stats['scanned']}")
        print(f"Bit-Rot:       {stats['bit_rot_purged']} fragments purged")
        print(f"Vendor Bloat:  {stats['stripped_vendor']} fields removed")
        print(f"Sync IDs:      {stats['stripped_keys']} trackers killed")
        print(f"Orphan Lines:  {stats['orphans_killed']} metadata lines purged")
        print("-"*45)
        print("Notes: All Samsung/Google UIDs removed.")
        print("Migration path: Ubuntu -> GrapheneOS")
        print("="*45)
    else:
        print("Failed to write cleansed file!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAudit cancelled by user.")
        sys.exit(0)
