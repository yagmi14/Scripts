#!/usr/bin/env bash
set -u

# reality_domain_probe_interactive.sh
#
# Usage:
#   ./reality_domain_probe_interactive.sh
#   ./reality_domain_probe_interactive.sh -i
#   ./reality_domain_probe_interactive.sh www.example.com www.example.org
#   ./reality_domain_probe_interactive.sh -f domains.txt
#   ./reality_domain_probe_interactive.sh --default
#
# Interactive mode:
#   - Run without arguments or with -i.
#   - Enter domains separated by spaces, commas, semicolons, or new lines.
#   - Press Enter on an empty line to start testing.
#   - Type "default" to use the built-in default list.
#   - Type "q" or "quit" to exit.

DEFAULT_DOMAINS=(
  www.hetzner.com
  www.ionos.de
  www.strato.de
  www.telekom.de
  www.de-cix.net
  www.denic.de
  www.bundesbank.de
  www.bahn.de
  www.lufthansa.com
  www.sap.com
  www.amd.com
  www.nvidia.com
  www.sony.com
  www.oracle.com
  aws.amazon.com
  www.amazon.com
)

DOMAINS=()

usage() {
  cat <<'USAGE_EOF'
Usage:
  ./reality_domain_probe_interactive.sh
  ./reality_domain_probe_interactive.sh -i
  ./reality_domain_probe_interactive.sh www.example.com www.example.org
  ./reality_domain_probe_interactive.sh -f domains.txt
  ./reality_domain_probe_interactive.sh --default

Options:
  -i, --interactive   Interactive domain input mode
  -f, --file FILE     Read domains from a file, one or more per line
  --default           Use built-in default domain list
  -h, --help          Show this help

Interactive input:
  - Separate domains with spaces, commas, semicolons, or new lines.
  - Press Enter on an empty line to start testing.
  - Type "default" to use the built-in default list.
  - Type "q" or "quit" to exit.
USAGE_EOF
}

need() {
  command -v "$1" >/dev/null 2>&1
}

trim_domain() {
  # Normalize user input into a hostname:
  # - remove protocol
  # - remove path/query/fragment
  # - remove trailing dot
  # - remove port for normal host:port input
  # - lowercase
  local raw="$1"
  local d

  d="$(printf '%s' "$raw" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  d="${d#http://}"
  d="${d#https://}"
  d="${d%%/*}"
  d="${d%%\?*}"
  d="${d%%#*}"
  d="${d%.}"
  d="$(printf '%s' "$d" | tr '[:upper:]' '[:lower:]')"

  # Strip a simple numeric port from hostname:443.
  # This intentionally does not try to parse IPv6 literals, because REALITY
  # domain probing is intended for hostnames.
  if printf '%s' "$d" | grep -Eq '^[a-z0-9.-]+:[0-9]+$'; then
    d="${d%:*}"
  fi

  printf '%s' "$d"
}

is_valid_domain() {
  local d="$1"

  # Accept ordinary DNS names. Reject empty strings, underscores, wildcards,
  # spaces, and raw URLs that were not normalized.
  [ -n "$d" ] || return 1
  [ "${#d}" -le 253 ] || return 1
  printf '%s' "$d" | grep -Eq '^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$'
}

add_domain_token() {
  local token="$1"
  local d
  d="$(trim_domain "$token")"

  if is_valid_domain "$d"; then
    DOMAINS+=("$d")
  elif [ -n "$token" ]; then
    printf 'Skip invalid input: %s\n' "$token" >&2
  fi
}

add_domains_from_text() {
  local text="$1"
  local token

  # Split on whitespace, comma, and semicolon.
  while IFS= read -r token; do
    add_domain_token "$token"
  done < <(printf '%s\n' "$text" | tr ',;' '\n\n' | tr '[:space:]' '\n' | sed '/^$/d')
}

dedupe_domains() {
  local d
  local seen=" "
  local unique=()

  for d in "${DOMAINS[@]}"; do
    case "$seen" in
      *" $d "*) ;;
      *)
        unique+=("$d")
        seen="${seen}${d} "
        ;;
    esac
  done

  DOMAINS=("${unique[@]}")
}

read_domains_file() {
  local file="$1"

  if [ ! -r "$file" ]; then
    printf 'Cannot read file: %s\n' "$file" >&2
    exit 1
  fi

  add_domains_from_text "$(cat "$file")"
}

interactive_input() {
  local line
  local collected=()

  cat >&2 <<'PROMPT_EOF'
Interactive domain input mode
- Enter domains separated by spaces, commas, semicolons, or new lines.
- Press Enter on an empty line to start testing.
- Type "default" to use the built-in default list.
- Type "q" or "quit" to exit.

Domains:
PROMPT_EOF

  while true; do
    printf '> ' >&2
    IFS= read -r line || break

    case "$(printf '%s' "$line" | tr '[:upper:]' '[:lower:]' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')" in
      q|quit|exit)
        printf 'Exit.\n' >&2
        exit 0
        ;;
      default)
        DOMAINS=("${DEFAULT_DOMAINS[@]}")
        return
        ;;
      "")
        break
        ;;
      *)
        collected+=("$line")
        ;;
    esac
  done

  if [ "${#collected[@]}" -eq 0 ]; then
    printf 'No domain entered. Use --default if you want the built-in list.\n' >&2
    exit 1
  fi

  add_domains_from_text "$(printf '%s\n' "${collected[@]}")"
}

cname_chain() {
  local d="$1"
  if need dig; then
    dig +short CNAME "$d" | paste -sd' ' -
  elif need host; then
    host -t CNAME "$d" 2>/dev/null | awk '/alias for/ {print $NF}' | paste -sd' ' -
  else
    echo ""
  fi
}

a_records() {
  local d="$1"
  if need dig; then
    dig +short A "$d" | paste -sd',' -
  elif need host; then
    host -t A "$d" 2>/dev/null | awk '/has address/ {print $NF}' | paste -sd',' -
  else
    echo ""
  fi
}

aaaa_records() {
  local d="$1"
  if need dig; then
    dig +short AAAA "$d" | paste -sd',' -
  elif need host; then
    host -t AAAA "$d" 2>/dev/null | awk '/has IPv6 address/ {print $NF}' | paste -sd',' -
  else
    echo ""
  fi
}

cdn_guess() {
  local s="$1"
  s="$(printf '%s' "$s" | tr '[:upper:]' '[:lower:]')"

  case "$s" in
    *cloudfront*|*.amazonaws.com*|*amazonaws.com*) echo "CloudFront/AWS CDN" ;;
    *akamai*|*edgesuite*|*edgekey*|*akamaiedge*|*akadns*) echo "Akamai CDN" ;;
    *cloudflare*|*cdn.cloudflare.net*) echo "Cloudflare CDN" ;;
    *fastly*|*map.fastly*|*global.prod.fastly*) echo "Fastly CDN" ;;
    *azureedge*|*azurefd*|*msedge*|*trafficmanager*) echo "Microsoft/Azure edge" ;;
    *vercel*|*vercel-dns*|*vercel-infra*) echo "Vercel edge" ;;
    *googleusercontent*|*googlehosted*|*gvt1*) echo "Google edge/LB" ;;
    *) echo "unknown/non-obvious" ;;
  esac
}

ip_cdn_hint() {
  # Lightweight heuristic only. CNAME remains more reliable than this.
  local iplist="$1"

  case "$iplist" in
    104.16.*|104.17.*|104.18.*|104.19.*|104.20.*|104.21.*|104.22.*|104.23.*|104.24.*|104.25.*|104.26.*|104.27.*|104.28.*|104.29.*|104.30.*|104.31.*|172.64.*|172.65.*|172.66.*|172.67.*|188.114.*)
      echo "Cloudflare IP range hint"
      ;;
    13.32.*|13.33.*|13.35.*|18.64.*|18.65.*|18.66.*|18.67.*|54.192.*|54.230.*|99.84.*|99.86.*)
      echo "CloudFront IP range hint"
      ;;
    151.101.*)
      echo "Fastly IP range hint"
      ;;
    76.76.21.*)
      echo "Vercel IP range hint"
      ;;
    *)
      echo ""
      ;;
  esac
}

ping_avg() {
  local d="$1"
  if need ping; then
    ping -c 5 -W 2 "$d" 2>/dev/null | awk -F'/' '/rtt|round-trip/ {print $5}'
  else
    echo ""
  fi
}

curl_metrics() {
  local d="$1"
  if need curl; then
    curl -o /dev/null -sS --connect-timeout 5 --max-time 10 \
      -w '%{remote_ip}\t%{time_connect}\t%{time_appconnect}\t%{http_version}\t%{ssl_verify_result}\t%{http_code}' \
      "https://${d}/" 2>/dev/null || printf '\t\t\t\t\t'
  else
    printf '\t\t\t\t\t'
  fi
}

xray_check() {
  local d="$1"
  if need xray; then
    # Xray official docs recommend checking with: xray tls ping example.com
    timeout 15 xray tls ping "$d" 2>&1 | head -n 35 | tr '\n' ' ' | sed 's/[[:space:]][[:space:]]*/ /g'
  else
    echo "xray-not-installed"
  fi
}

parse_args() {
  if [ "$#" -eq 0 ]; then
    interactive_input
    return
  fi

  while [ "$#" -gt 0 ]; do
    case "$1" in
      -h|--help)
        usage
        exit 0
        ;;
      -i|--interactive)
        interactive_input
        ;;
      --default)
        DOMAINS=("${DEFAULT_DOMAINS[@]}")
        ;;
      -f|--file)
        shift
        if [ "${1:-}" = "" ]; then
          printf 'Missing file after -f/--file.\n' >&2
          exit 1
        fi
        read_domains_file "$1"
        ;;
      --)
        shift
        while [ "$#" -gt 0 ]; do
          add_domain_token "$1"
          shift
        done
        break
        ;;
      -*)
        printf 'Unknown option: %s\n' "$1" >&2
        usage >&2
        exit 1
        ;;
      *)
        add_domain_token "$1"
        ;;
    esac
    shift || true
  done
}

parse_args "$@"
dedupe_domains

if [ "${#DOMAINS[@]}" -eq 0 ]; then
  printf 'No valid domains to test.\n' >&2
  exit 1
fi

printf 'Testing %s domain(s): %s\n' "${#DOMAINS[@]}" "${DOMAINS[*]}" >&2
printf 'domain\tping_avg_ms\tremote_ip\tconnect_s\ttls_s\thttp_ver\tssl_verify\thttp_code\ta_records\taaaa_records\tcname_chain\tcdn_guess\tip_hint\txray_tls_ping_summary\n'

for d in "${DOMAINS[@]}"; do
  cn="$(cname_chain "$d")"
  arec="$(a_records "$d")"
  aaaarec="$(aaaa_records "$d")"
  cdn="$(cdn_guess "$cn")"
  pavg="$(ping_avg "$d")"
  metrics="$(curl_metrics "$d")"

  # Extract the remote IP from curl metrics for a simple CDN range hint.
  remote_ip="$(printf '%s' "$metrics" | awk -F'\t' '{print $1}')"
  hint="$(ip_cdn_hint "$remote_ip,$arec,$aaaarec")"

  xray="$(xray_check "$d")"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$d" "$pavg" "$metrics" "$arec" "$aaaarec" "$cn" "$cdn" "$hint" "$xray"
done
