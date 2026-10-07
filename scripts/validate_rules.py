#!/usr/bin/env python3
"""Validate AI-Only-Proxy.conf routing semantics (Shadowrocket DOMAIN-SUFFIX logic)."""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

CONF = Path(__file__).resolve().parents[1] / "AI-Only-Proxy.conf"


def suffix_match(host: str, suffix: str) -> bool:
    host = host.lower().rstrip(".")
    suffix = suffix.lower().lstrip(".")
    if host == suffix:
        return True
    return host.endswith("." + suffix)


def domain_match(host: str, pattern: str) -> bool:
    return host.lower().rstrip(".") == pattern.lower().rstrip(".")


def wildcard_match(host: str, pattern: str) -> bool:
    host = host.lower()
    pattern = pattern.lower()
    regex = "^" + re.escape(pattern).replace(r"\*", ".*") + "$"
    return re.match(regex, host) is not None


def parse_rules(text: str) -> list[tuple[str, str, str]]:
    rules: list[tuple[str, str, str]] = []
    in_rule = False
    for line in text.splitlines():
        line = line.strip()
        if line == "[Rule]":
            in_rule = True
            continue
        if not in_rule:
            continue
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 2 and parts[0] == "FINAL":
            rules.append((parts[0], "", parts[1]))
            continue
        if len(parts) < 3:
            continue
        kind, target, policy = parts[0], parts[1], parts[2]
        rules.append((kind, target, policy))
    return rules


def resolve(host: str, rules: list[tuple[str, str, str]]) -> str | None:
    for kind, target, policy in rules:
        if kind == "FINAL":
            return policy
        if kind == "DOMAIN-SUFFIX" and suffix_match(host, target):
            return policy
        if kind == "DOMAIN" and domain_match(host, target):
            return policy
        if kind == "DOMAIN-WILDCARD" and wildcard_match(host, target):
            return policy
    return None


def main() -> int:
    text = CONF.read_text(encoding="utf-8")
    rules = parse_rules(text)
    enabled = [r for r in rules if r[0] != "FINAL" or True]
    # conflicts
    by_target: dict[tuple[str, str], set[str]] = defaultdict(set)
    for kind, target, policy in rules:
        if kind == "FINAL":
            continue
        by_target[(kind, target.lower())].add(policy)

    errors: list[str] = []
    for key, policies in by_target.items():
        if len(policies) > 1:
            errors.append(f"冲突: {key[0]},{key[1]} -> {policies}")

    if not rules or rules[-1][0] != "FINAL" or rules[-1][2] != "DIRECT":
        errors.append("最后一条启用规则必须是 FINAL,DIRECT")

    proxy_count = sum(1 for k, _, p in rules if k != "FINAL" and p != "DIRECT")
    direct_count = sum(1 for k, _, p in rules if k != "FINAL" and p == "DIRECT")

    cursor_hosts = [
        "api2.cursor.sh",
        "api3.cursor.sh",
        "api4.cursor.sh",
        "api5.cursor.sh",
        "agent.api5.cursor.sh",
        "agent.global.api5.cursor.sh",
        "repo42.cursor.sh",
        "authenticate.cursor.sh",
        "authenticator.cursor.sh",
        "prod.authentication.cursor.sh",
        "foo.authentication.cursor.sh",
        "us-asia.gcpp.cursor.sh",
        "marketplace.cursorapi.com",
        "cursor-cdn.com",
        "downloads.cursor.com",
        "anysphere-binaries.s3.us-east-1.amazonaws.com",
        "accounts.spacex.ai",
        "accounts.x.ai",
    ]
    for h in cursor_hosts:
        if resolve(h, rules) != "AI-Cursor":
            errors.append(f"Cursor/Grok 应走 AI-Cursor: {h} -> {resolve(h, rules)}")

    domestic = [
        "chat.deepseek.com",
        "kimi.ai",
        "qwen.ai",
        "trae.ai",
        "z.ai",
        "qoder.com",
        "lovart.ai",
        "tripo3d.ai",
    ]
    for h in domestic:
        if resolve(h, rules) != "DIRECT":
            errors.append(f"中国大陆 AI 应 DIRECT: {h} -> {resolve(h, rules)}")

    overseas = [
        "chatgpt.com",
        "claude.ai",
        "gemini.google.com",
        "api.openai.com",
        "grok.com",
    ]
    for h in overseas:
        if resolve(h, rules) in (None, "DIRECT"):
            errors.append(f"海外 AI 应走策略组: {h} -> {resolve(h, rules)}")

    if resolve("perplexity.ai", rules) not in (None, "DIRECT"):
        errors.append(
            f"Perplexity 应已移除分流: perplexity.ai -> {resolve('perplexity.ai', rules)}"
        )

    general_direct = [
        "www.google.com",
        "mail.google.com",
        "www.youtube.com",
        "www.bing.com",
        "github.com",
        "www.microsoft.com",
        "www.apple.com",
        "www.baidu.com",
        "www.taobao.com",
        "x.com",
        "twitter.com",
    ]
    for h in general_direct:
        if resolve(h, rules) != "DIRECT":
            errors.append(f"普通站点应 DIRECT: {h} -> {resolve(h, rules)}")

    false_pos = [
        ("cursor.sh.example.com", "DIRECT"),
        ("notcursor.sh", "DIRECT"),
    ]
    for h, want in false_pos:
        got = resolve(h, rules)
        if got != want:
            errors.append(f"边界案例 {h} 应为 {want}，实际 {got}")

    optional_block = text.split("# 可选兼容规则", 1)
    if len(optional_block) > 1:
        for line in optional_block[1].splitlines():
            s = line.strip()
            if s.startswith("FINAL,"):
                break
            if not s or s.startswith("#"):
                continue
            if "PROXY" in s:
                errors.append(f"可选规则被意外启用: {s}")

    print(f"PROXY 规则: {proxy_count}")
    print(f"DIRECT 规则: {direct_count}")
    print(f"启用规则总数（不含 FINAL）: {proxy_count + direct_count}")

    if errors:
        print("验证失败:")
        for e in errors:
            print(" -", e)
        return 1
    print("验证通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
