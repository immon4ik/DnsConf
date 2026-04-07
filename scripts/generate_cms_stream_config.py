#!/usr/bin/env python3

from __future__ import annotations

import argparse
import ipaddress
import re
from pathlib import Path


HOSTNAME_RE = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build cms nginx stream config from a generated custom.hosts file"
    )
    parser.add_argument("--input", required=True, help="Path to custom hosts file")
    parser.add_argument("--cms-ip", required=True, help="Public cms IP used in custom hosts")
    parser.add_argument(
        "--relay-port",
        type=int,
        default=9443,
        help="Local relay backend port on cms host",
    )
    parser.add_argument("--output", required=True, help="Path to rendered nginx config")
    return parser.parse_args()


def parse_domains(hosts_path: Path, cms_ip: str) -> list[str]:
    domains: set[str] = set()
    for raw_line in hosts_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        parts = stripped.split()
        if len(parts) < 2:
            continue

        ip = parts[0].strip()
        host = parts[1].strip().lower()
        if ip != cms_ip or not HOSTNAME_RE.fullmatch(host):
            continue
        domains.add(host)

    return sorted(domains)


def render_config(domains: list[str], relay_port: int) -> str:
    domain_lines = [f"    {domain} relay_backend;" for domain in domains]
    rendered_domains = "\n".join(domain_lines)

    return "\n".join(
        [
            "# Managed by DnsConf. Manual edits will be overwritten.",
            "map_hash_bucket_size 128;",
            "map_hash_max_size 8192;",
            "map $ssl_preread_server_name $target_backend {",
            "    hostnames;",
            "    default anchor_vless;",
            rendered_domains,
            "}",
            "",
            "upstream anchor_vless {",
            "    server 127.0.0.1:8443;",
            "}",
            "",
            "upstream relay_backend {",
            f"    server 127.0.0.1:{relay_port};",
            "}",
            "",
            "server {",
            "    listen 443;",
            "    ssl_preread on;",
            "    proxy_pass $target_backend;",
            "    access_log off;",
            "    error_log /var/log/nginx/anchor_stream_error.log info;",
            "    proxy_connect_timeout 10s;",
            "    proxy_timeout 1h;",
            "}",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    ipaddress.ip_address(args.cms_ip)
    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    domains = parse_domains(input_path, args.cms_ip)
    output_path.write_text(
        render_config(domains, args.relay_port),
        encoding="utf-8",
    )
    print(f"Rendered {len(domains)} cms relay domains into {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
