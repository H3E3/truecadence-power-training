#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-/opt/truecadence}"
DATA_DIR="$APP_DIR/data"
SERVICE="${TRUECADENCE_SERVICE:-truecadence}"
EXPECTED_USER="${TRUECADENCE_SERVICE_USER:-}"
EXPECTED_GROUP="${TRUECADENCE_SERVICE_GROUP:-}"

if [[ -z "$EXPECTED_USER" ]]; then
  EXPECTED_USER="$(systemctl show "$SERVICE" -p User --value 2>/dev/null || true)"
fi
if [[ -z "$EXPECTED_USER" ]]; then
  EXPECTED_USER="www-data"
fi
if [[ -z "$EXPECTED_GROUP" ]]; then
  EXPECTED_GROUP="$EXPECTED_USER"
fi

if [[ ! -d "$DATA_DIR" ]]; then
  echo "ERROR: data dir not found: $DATA_DIR" >&2
  exit 1
fi

echo "TrueCadence data permission check"
echo "APP_DIR=$APP_DIR"
echo "DATA_DIR=$DATA_DIR"
echo "SERVICE=$SERVICE"
echo "EXPECTED_USER=$EXPECTED_USER"
echo "EXPECTED_GROUP=$EXPECTED_GROUP"
echo

fail=0
check_path() {
  local path="$1"
  local kind="$2"
  if [[ ! -e "$path" ]]; then
    return 0
  fi
  local owner group mode
  owner="$(stat -c '%U' "$path")"
  group="$(stat -c '%G' "$path")"
  mode="$(stat -c '%a' "$path")"
  printf '%-8s %-55s owner=%s group=%s mode=%s\n' "$kind" "$path" "$owner" "$group" "$mode"
  if [[ "$owner" != "$EXPECTED_USER" || "$group" != "$EXPECTED_GROUP" ]]; then
    echo "ERROR: owner/group mismatch on $path; expected $EXPECTED_USER:$EXPECTED_GROUP" >&2
    fail=1
  fi
  if ! sudo -u "$EXPECTED_USER" test -r "$path"; then
    echo "ERROR: $EXPECTED_USER cannot read $path" >&2
    fail=1
  fi
  if ! sudo -u "$EXPECTED_USER" test -w "$path"; then
    echo "ERROR: $EXPECTED_USER cannot write $path" >&2
    fail=1
  fi
}

check_path "$DATA_DIR" dir
find "$DATA_DIR" -maxdepth 1 -type f -name '*.json' -print0 | sort -z | while IFS= read -r -d '' f; do
  check_path "$f" file
  sudo -u "$EXPECTED_USER" python3 -m json.tool "$f" >/dev/null
  echo "JSON_OK $f"
done

if [[ "$fail" -ne 0 ]]; then
  echo
  echo "Permission check FAILED." >&2
  echo "Suggested repair after backup: sudo chown -R $EXPECTED_USER:$EXPECTED_GROUP '$DATA_DIR' && sudo find '$DATA_DIR' -type d -exec chmod 775 {} + && sudo find '$DATA_DIR' -type f -name '*.json' -exec chmod 660 {} +" >&2
  exit 1
fi

echo
echo "DATA_PERMISSION_CHECK_OK"
