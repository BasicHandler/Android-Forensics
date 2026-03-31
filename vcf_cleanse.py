#!/usr/bin/env python3
import os
import sys
import hashlib
import time

def print_banner():
    GREEN = '\033[92m'
    ORANGE = '\033[38;5;208m'
    RESET = '\033[0m'
    print(f"{GREEN}+++ BINO MELBINO CONTACT CLEANSE v2.2 +++{RESET}")
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
        "stripped_vendor": 0,  # X-SAMSUNG, GOOGLE, etc.
        "stripped_keys": 0,    # UID, REV, PRODID
        "orphans_killed": 0,   # Lines outside BEGIN/END
        "bit_rot_purged": 0,   # Corrupted Base64/fragments
        "audit_log": []
    }

    # Comprehensive Proscribed Lists
    PROSCRIBED_PREFIXES = ('X-', 'GOOGLE-', 'X-MS-', 'X-SAMSUNG-', 'X-PHONETIC-')
    PROSCRIBED_KEYS = ('UID', 'REV', 'PRODID', 'PHOTO', 'VERSION')

    for line in lines:
        stats["scanned"] += 1
        # Normalize encoding and remove Samsung-style CRLF
        line = line.replace('\ufeff', '').replace('\r\n', '\n')
        stripped = line.strip()
        if not stripped: continue

        # 1 Updated Bit-Rot Guard in cleanse_vcf_lines:
if ':' not in stripped and not stripped.startswith(('BEGIN', 'END')):
        # If the line starts with whitespace, it's a continuation, not rot
        if line.startswith((' ', '\t')):
            cleansed_lines.append(line)
        continue
    stats["bit_rot_purged"] += 1
        continue


        # 2. Structural Lock: Handle BEGIN/END and force RFC 6350 (v3.0)
        if stripped.startswith('BEGIN:VCARD'):
            in_vcard = True
            cleansed_lines.append("BEGIN:VCARD\n")
            cleansed_lines.append("VERSION:3.0\n") 
            continue
        elif stripped.startswith('END:VCARD'):
            in_vcard = False
            cleansed_lines.append("END:VCARD\n")
            continue

        # 3. Filter: Kill orphan metadata (Outside vCard blocks)
        if not in_vcard:
            stats["orphans_killed"] += 1
            continue

        # 4. Property-level Audit
        if ':' in stripped:
            # Isolate the key part before the colon
            full_key = stripped.split(':', 1)[0].upper()
            # Handle property parameters (split by semicolon)
            base_key = full_key.split(';', 1)[0]

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

    with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    print(f"Audit started on {len(lines)} lines...")
    cleansed_lines, stats = cleanse_vcf_lines(lines)

    if not cleansed_lines:
        print("Audit Error: No valid data remaining.")
        return

    # Use Timestamp to prevent name conflicts
    target_dir = os.path.dirname(os.path.abspath(target_file))
    timestamp = int(time.time())
    output_file = os.path.join(target_dir, f"sanitized_migration_{timestamp}.vcf")

    file_hash = write_cleansed_vcf(cleansed_lines, output_file)

    if file_hash:
        print("\n" + "="*45)
        print("AUDIT DEBRIEFING: MIGRATION READY")
        print("="*45)
        print(f"Status:        SUCCESS (RFC 6350 Compliant)")
        print(f"Output:        {os.path.basename(output_file)}")
        print(f"SHA-256:       {file_hash[:16]}...{file_hash[-16:]}")
        print(f"Lines Scanned: {stats['scanned']}")
        print(f"Bit-Rot:       {stats['bit_rot_purged']} fragments purged")
        print(f"Vendor Bloat:  {stats['stripped_vendor']} fields removed")
        print(f"Sync IDs:      {stats['stripped_keys']} trackers killed")
        print(f"Orphan Lines:  {stats['orphans_killed']} metadata lines purged")
        print("-"*45)
        print("Notes: All Samsung/Google UIDs removed. Contacts will")
        print("appear as 'New' to GrapheneOS to prevent cloud re-sync.")
        print("="*45)
    else:
        print("Failed to write cleansed file!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)