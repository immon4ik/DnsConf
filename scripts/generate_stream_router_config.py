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
        description="Build nginx stream router config for domains assigned to a node IP"
    )
    parser.add_argument("--input", required=True, help="Path to custom hosts file")
    parser.add_argument("--node-name", required=True, help="Logical node name for logs")
    parser.add_argument("--node-ip", required=True, help="Public node IP used in custom hosts")
    parser.add_argument("--listen-port", type=int, default=443, help="Public listen port")
    parser.add_argument("--relay-port", type=int, default=9443, help="Local relay backend port")
    parser.add_argument(
        "--relay-upstream-host",
        default="127.0.0.1",
        help="Host/IP used by the router to reach the relay backend",
    )
    parser.add_argument("--default-upstream", required=True, help="Default upstream in host:port format")
    parser.add_argument(
        "--default-upstream-name",
        default="default_upstream",
        help="Upstream block name for default traffic",
    )
    parser.add_argument("--output", required=True, help="Path to rendered nginx config")
    return parser.parse_args()


def parse_domains(hosts_path: Path, node_ip: str) -> list[str]:
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
        if ip != node_ip or not HOSTNAME_RE.fullmatch(host):
            continue
        domains.add(host)

    return sorted(domains)


def render_config(node_name: str, domains: list[str], listen_port: int, relay_port: int, relay_upstream_host: str, default_upstream_name: str, default_upstream: str) -> str:
    domain_lines = [f"    {domain} relay_backend;" for domain in domains]
    rendered_domains = "\n".join(domain_lines)

    return "\n".join(
        [
            "# Managed by DnsConf. Manual edits will be overwritten.",
            f"# node: {node_name}",
            "map_hash_bucket_size 128;",
            "map_hash_max_size 8192;",
            "map $ssl_preread_server_name $target_backend {",
            "    hostnames;",
            f"    default {default_upstream_name};",
            rendered_domains,
            "}",
            "",
            f"upstream {default_upstream_name} {{",
            f"    server {default_upstream};",
            "}",
            "",
            "upstream relay_backend {",
            f"    server {relay_upstream_host}:{relay_port};",
            "}",
            "",
            "server {",
            f"    listen {listen_port};",
            "    ssl_preread on;",
            "    proxy_pass $target_backend;",
            "    access_log off;",
            f"    error_log /var/log/nginx/{node_name}_stream_error.log info;",
            "    proxy_connect_timeout 10s;",
            "    proxy_timeout 1h;",
            "}",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    ipaddress.ip_address(args.node_ip)
    if ":" not in args.default_upstream:
        raise ValueError("default-upstream must be in host:port format")

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    domains = parse_domains(input_path, args.node_ip)
    output_path.write_text(
        render_config(
            args.node_name,
            domains,
            args.listen_port,
            args.relay_port,
            args.relay_upstream_host,
            args.default_upstream_name,
            args.default_upstream,
        ),
        encoding="utf-8",
    )
    print(f"Rendered {len(domains)} {args.node_name} relay domains into {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
