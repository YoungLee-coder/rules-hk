#!/usr/bin/env python3
"""Validate AI-Only-Proxy.conf routing semantics (Shadowrocket DOMAIN-SUFFIX logic)."""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

CONF = Path(__file__).resolve().parents[1] / "AI-Only-Proxy.conf"

ALLOWED_POLICY_GROUPS = frozenset(
    {"Cursor", "OpenAI", "Claude", "Gemini", "Krill", "Kiro", "Manus"}
)


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

    for kind, _, policy in rules:
        if kind == "FINAL":
            continue
        if policy != "DIRECT" and policy not in ALLOWED_POLICY_GROUPS:
            errors.append(f"未允许的策略组: {policy}")

    cursor_hosts = [
        "api2.cursor.sh",
        "accounts.spacex.ai",
        "accounts.x.ai",
        "grok.com",
    ]
    for h in cursor_hosts:
        if resolve(h, rules) != "Cursor":
            errors.append(f"Cursor 应走 Cursor 组: {h} -> {resolve(h, rules)}")

    service_checks = [
        ("chatgpt.com", "OpenAI"),
        ("claude.ai", "Claude"),
        ("gemini.google.com", "Gemini"),
        ("api.krill-code.net", "Krill"),
        ("kiro.dev", "Kiro"),
        ("manus.im", "Manus"),
    ]
    for h, group in service_checks:
        if resolve(h, rules) != group:
            errors.append(f"{group} 应走 {group} 组: {h} -> {resolve(h, rules)}")

    removed = [
        ("perplexity.ai", "Perplexity"),
        ("copilot.microsoft.com", "Copilot"),
        ("githubcopilot.com", "GitHub Copilot"),
        ("windsurf.com", "Windsurf"),
        ("poe.com", "Poe"),
        ("midjourney.com", "Midjourney"),
        ("devin.ai", "Devin"),
    ]
    for h, name in removed:
        got = resolve(h, rules)
        if got not in (None, "DIRECT"):
            errors.append(f"{name} 应已移除分流: {h} -> {got}")

    # 未写入 conf 的域名（含中国大陆 AI）应随 FINAL 直连
    final_direct = [
        "chat.deepseek.com",
        "kimi.ai",
        "qwen.ai",
        "trae.ai",
    ]
    for h in final_direct:
        if resolve(h, rules) != "DIRECT":
            errors.append(f"未列域名应 FINAL 直连: {h} -> {resolve(h, rules)}")

    general_direct = [
        "www.google.com",
        "github.com",
        "x.com",
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

    print(f"分流规则（策略组）: {proxy_count}")
    print(f"显式 DIRECT 规则: {direct_count}")
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
