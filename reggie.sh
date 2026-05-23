BASH <rootless>

# === Color Codes for Display ===
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[1;34m'
PURPLE='\033[0;35m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# == Identity ==
echo -e "${PURPLE}###  - Toothless Reggie's Toothbox Reggie 1, 'reggie': Reggie the Trailer From The Code Transparency Lab"
echo -e "Session: ${BLUE}$(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "Platform: $(uname -o) $(uname -m) | Bash ${GREEN}$BASH_VERSION${NC}"



#!/bin/sh
# reggie.sh
# Usage:
#  ./reggie.sh                # audit current process
#  ./reggie.sh <pid>          # audit PID
#  ./reggie.sh /path/to/maps.dump  # audit saved maps file
#  ./reggie.sh --file <path>  # analyze single file (prints path, patch hint, and produces artifact)
#
# Outputs: ./reggie_out/timeline.txt and ./reggie_out/files/<sha256>.txt
SRC=${1:-$$}
OUT=${2:-./reggie_out}
ENTROPY_FLAG=1   # set 1 to compute fast entropy estimate
SNAP_INT=1

mkdir -p "$OUT/files" || exit 1
TIMELINE="$OUT/timeline.txt"
MAPS="$OUT/maps.dump"

# --- FILE MODE HANDLER ---
if [ "$1" = "--file" ]; then
  TARGET="$2"
  if [ -z "$TARGET" ]; then
    echo "Usage: $0 --file <path>" >&2
    exit 1
  fi
  if command -v realpath >/dev/null 2>&1; then
    TARGET_REAL=$(realpath -m "$TARGET" 2>/dev/null || echo "$TARGET")
  else
    TARGET_REAL=$(cd "$(dirname "$TARGET")" 2>/dev/null && echo "$(pwd)/$(basename "$TARGET")" || echo "$TARGET")
  fi

  if [ ! -e "$TARGET_REAL" ]; then
    echo "UNREACHABLE: $TARGET_REAL" >&2
    exit 2
  fi

  echo "REACHABLE: $TARGET_REAL"
  SCRIPT_PATH="$0"
  if [ ! -f "$SCRIPT_PATH" ]; then
    SCRIPT_PATH="$(command -v "$(basename "$0")" 2>/dev/null || echo "$0")"
  fi
  echo "PATCH-HINT: insert per-file analysis loop at marker: ## INSERT-FILE-MODULE-HERE"
  echo "SCRIPT: $SCRIPT_PATH"
  echo ""
  echo "Now running single-file analysis and producing artifact..."

  # per-file analysis (same logic used in main loop)
  path="$TARGET_REAL"
  statinfo=$(stat -c "%U:%G %a %y %s" "$path" 2>/dev/null || echo "stat-fail")
  sha=$(sha256sum "$path" | awk '{print $1}')
  outfile="$OUT/files/$sha.txt"
  IPURL_RE="([0-9]{1,3}\.){3}[0-9]{1,3}|https?://[A-Za-z0-9./:_-]+"

  fast_entropy() {
    f="$1"
    N=65536
    head -c $N "$f" 2>/dev/null | od -An -t u1 -v | tr -s ' ' '\n' | awk '
    {cnt[$1]++ ; total++}
    END{
      if(total==0){print 0; exit}
      e=0;
      for(c in cnt) { p=cnt[c]/total; e -= p * log(p)/log(2) }
      printf("%.4f", e)
    }'
  }

  if [ ! -f "$outfile" ]; then
    echo "PATH: $path" > "$outfile"
    echo "STAT: $statinfo" >> "$outfile"
    echo "SHA256: $sha" >> "$outfile"
    echo "" >> "$outfile"

    echo "=== STRINGS (filtered) ===" >> "$outfile"
    strings "$path" | grep -Ei 'exec|system|popen|dlopen|fork|ssh|su|sh|/data/|/system/|/dev/|passwd|shadow|socket|connect|bind|http|https|base64|eval' >> "$outfile" 2>/dev/null || true

    echo "" >> "$outfile"
    echo "=== ELF CHECK ===" >> "$outfile"
    head -c 4 "$path" | xxd -p -c4 | grep -qi '^7f454c46' && echo "ELF: yes" >> "$outfile" || echo "ELF: no" >> "$outfile"

    if [ "$ENTROPY_FLAG" -eq 1 ]; then
      echo "" >> "$outfile"
      echo "=== FAST ENTROPY (first 64KB) ===" >> "$outfile"
      ent=$(fast_entropy "$path")
      echo "$ent" >> "$outfile"
    fi

    echo "" >> "$outfile"
    echo "=== BASE64 BLOBS (>=8) decoded -> IP/URL matches ===" >> "$outfile"
    strings "$path" | grep -E '^[A-Za-z0-9+/=]{8,}$' | sort -u | while read -r b64; do
      dec=$(echo "$b64" | base64 -d 2>/dev/null || true)
      if [ -n "$dec" ]; then
        echo "----B64: $b64" >> "$outfile"
        echo "$dec" | grep -Eo -o "$IPURL_RE" | sort -u >> "$outfile" || true
      fi
    done

    echo "" >> "$outfile"
    echo "=== RAW IP/URL EXTRACT (from strings) ===" >> "$outfile"
    strings "$path" | grep -Eo -o "$IPURL_RE" | sort -u >> "$outfile" || true
  fi

  echo "FILE $sha $path TYPE:single-file" > "$TIMELINE"
  echo "Artifact written: $outfile"
  exit 0
fi
# --- end FILE MODE HANDLER ---


# get maps: either a file passed or /proc/<pid>/maps
if [ -r "$SRC" ] && [ -f "$SRC" ]; then
  cp -f "$SRC" "$MAPS"
elif [ -r "/proc/$SRC/maps" ]; then
  cp -f "/proc/$SRC/maps" "$MAPS"
else
  echo "Reggie cannot read maps from $SRC" >&2
  exit 1
fi

echo "Reggie's audit: $(date -u +"%Y-%m-%dT%H:%M:%SZ")" > "$TIMELINE"
echo "Source: $SRC" >> "$TIMELINE"
echo "" >> "$TIMELINE"

awk '{ if($6) print $0 }' "$MAPS" > "$OUT/maps.lines"
awk '{ if($6) print $6 }' "$MAPS" | sort -u > "$OUT/mapped_paths_by_reggie.txt"

fast_entropy() {
  f="$1"
  N=65536
  head -c $N "$f" 2>/dev/null | od -An -t u1 -v | tr -s ' ' '\n' | awk '
  {cnt[$1]++ ; total++}
  END{
    if(total==0){print 0; exit}
    e=0;
    for(c in cnt) { p=cnt[c]/total; e -= p * log(p)/log(2) }
    printf("%.4f", e)
  }'
}

classify_path() {
  p="$1"
  case "$p" in
    \[*\]) echo "anonymous";;
    /system/*|/vendor/*|/apex/*) echo "system-lib";;
    /data/data/*) echo "app-data";;
    /dev/*) echo "device";;
    /*) echo "file";;
    *) echo "unknown";;
  esac
}

IPURL_RE="([0-9]{1,3}\.){3}[0-9]{1,3}|https?://[A-Za-z0-9./:_-]+"

## INSERT-FILE-MODULE-HERE
while IFS= read -r path; do
  [ -z "$path" ] && continue
  if echo "$path" | grep -q '^\['; then
    echo "ANON $path" >> "$TIMELINE"
    continue
  fi

  if [ ! -r "$path" ]; then
    echo "UNREADABLE $path" >> "$TIMELINE"
    continue
  fi

  statinfo=$(stat -c "%U:%G %a %y %s" "$path" 2>/dev/null || echo "stat-fail")
  sha=$(sha256sum "$path" | awk '{print $1}')
  outfile="$OUT/files/$sha.txt"

  if [ ! -f "$outfile" ]; then
    echo "PATH: $path" > "$outfile"
    echo "STAT: $statinfo" >> "$outfile"
    echo "SHA256: $sha" >> "$outfile"
    echo "" >> "$outfile"

    echo "=== STRINGS (filtered) ===" >> "$outfile"
    strings "$path" | grep -Ei 'exec|system|popen|dlopen|fork|ssh|su|sh|/data/|/system/|/dev/|passwd|shadow|socket|connect|bind|http|https|base64|eval' >> "$outfile" 2>/dev/null || true

    echo "" >> "$outfile"
    echo "=== ELF CHECK ===" >> "$outfile"
    head -c 4 "$path" | xxd -p -c4 | grep -qi '^7f454c46' && echo "ELF: yes" >> "$outfile" || echo "ELF: no" >> "$outfile"

    if [ "$ENTROPY_FLAG" -eq 1 ]; then
      echo "" >> "$outfile"
      echo "=== FAST ENTROPY (first 64KB) ===" >> "$outfile"
      ent=$(fast_entropy "$path")
      echo "$ent" >> "$outfile"
    fi

    echo "" >> "$outfile"
    echo "=== BASE64 BLOBS (>=8) decoded -> IP/URL matches ===" >> "$outfile"
    strings "$path" | grep -E '^[A-Za-z0-9+/=]{8,}$' | sort -u | while read -r b64; do
      dec=$(echo "$b64" | base64 -d 2>/dev/null || true)
      if [ -n "$dec" ]; then
        echo "----B64: $b64" >> "$outfile"
        echo "$dec" | grep -Eo -o "$IPURL_RE" | sort -u >> "$outfile" || true
      fi
    done

    echo "" >> "$outfile"
    echo "=== RAW IP/URL EXTRACT (from strings) ===" >> "$outfile"
    strings "$path" | grep -Eo -o "$IPURL_RE" | sort -u >> "$outfile" || true
  fi

  typ=$(classify_path "$path")
  rwx=$(grep " $path\$" "$OUT/maps.lines" | awk '$2 ~ /[rwxps-]+/ { if($2 ~ /w/ && $2 ~ /x/) print "RWX"; else if($2 ~ /x/) print "X"; else if($2 ~ /w/) print "W"; else print "-" }' | sort -u | tr '\n' ',' | sed 's/,$//')
  echo "FILE $sha $path TYPE:$typ PERMS:$rwx" >> "$TIMELINE"
done < "$OUT/mapped_paths.txt"

echo "" >> "$TIMELINE"
echo "=== FLAGS & SUSPICIONS ===" >> "$TIMELINE"
grep -E "^FILE" "$TIMELINE" | while read -r _ sha pathrest; do
  path=$(echo "$pathrest" | awk '{print $1}')
  flag=""
  if echo "$path" | grep -q '^/data/data/' && ! echo "$path" | grep -q '/data/data/com.termux'; then
    flag="${flag}OTHER_APP "
  fi
  if echo "$pathrest" | grep -q 'PERMS:RWX'; then
    flag="${flag}RWX "
  fi
  if echo "$path" | grep -q '^/dev/'; then
    flag="${flag}DEVICE "
  fi
  if [ "$ENTROPY_FLAG" -eq 1 ]; then
    ent=$(grep -A1 "=== FAST ENTROPY" "$OUT/files/$sha.txt" 2>/dev/null | tail -n1)
    ent=$(echo "$ent" | tr -d '[:space:]')
    if [ -n "$ent" ] && command -v bc >/dev/null 2>&1 && [ "$(echo "$ent >= 7.5" | bc -l)" -eq 1 ]; then
      flag="${flag}HIGH_ENTROPY "
    fi
  fi

  if [ -n "$flag" ]; then
    echo "SUSPECT $sha $path $flag" >> "$TIMELINE"
  fi
done

echo "" >> "$TIMELINE"
echo "=== IOCs FOUND ===" >> "$TIMELINE"
for f in "$OUT/files"/*.txt; do
  grep -Eo "$IPURL_RE" "$f" 2>/dev/null | sort -u | while read -r i; do
    echo "$i  (file: $(basename "$f"))" >> "$TIMELINE"
  done
done

echo "Done. Timeline: $TIMELINE"
echo "Artifacts: $OUT/files/*.txt"



```

