# Rules-update（Cursor 自动化）

**Automation ID:** `3a498fb1-a8e3-11f1-b532-320a589b8025`  
**编辑入口:** [cursor.com/automations/3a498fb1-a8e3-11f1-b532-320a589b8025](https://cursor.com/automations/3a498fb1-a8e3-11f1-b532-320a589b8025)  
**仓库:** `YoungLee-coder/rules-hk`（分支 `main`）

## 如何同步到 Cursor

Cursor 暂不支持从仓库自动覆盖自动化 Prompt。每次合并本文件后，请打开上述链接，将下方 **「自动化 Prompt（复制用）」** 整段粘贴到 Instructions，保存并启用。

建议设置：单仓库 `rules-hk`、默认分支 `main`、启用 **Pull request creation**；定时触发按你原有 cron 即可。

---

## 自动化 Prompt（复制用）

```text
请检查并更新本仓库的 Shadowrocket 分流配置（AI-Only-Proxy.conf），直接完成域名核查、文件修改和验证，不要只给建议。

一、当前产品范围（必须遵守）

1. 仅维护 7 个海外服务的分流与策略组：Cursor（含 Grok/xAI 登录域）、OpenAI、Claude、Gemini、Krill、Kiro、Manus。
2. 策略组名称不含 AI 前缀：Cursor、OpenAI、Claude、Gemini、Krill、Kiro、Manus。
3. conf 里只写需要走代理的域名规则；不要写入中国大陆 AI 的显式 DIRECT 规则。DeepSeek、Kimi、通义等未列域名一律由 FINAL,DIRECT 直连。
4. 不要恢复已移除的服务分流（Perplexity、Copilot、GitHub Copilot、Windsurf、Poe、Midjourney、Devin 等），除非用户在本次运行中明确要求。
5. PROXY 表示跟随 Shadowrocket 首页当前节点；不要添加或修改节点、订阅或凭据。不启用 HTTPS 解密，不引入远程规则集或与本任务无关的规则。

二、策略组写法（Shadowrocket 易错点）

- 服务组格式：Name = select,DIRECT,PROXY,Name-选节点,policy-select-name=PROXY
- 节点子组格式：Name-选节点 = select,policy-regex-filter=.*
- 禁止在同一行同时写 DIRECT、PROXY 与 policy-regex-filter（否则界面只剩订阅节点，没有直连和跟随主节点）。
- 规则第三列策略名须与策略组名一致（如 ,Cursor、,OpenAI、,Kiro、,Manus）。

三、先读仓库内 SSOT

1. AI-Only-Proxy.conf、使用说明.md、docs/automations/Rules-update.md（本说明）、scripts/validate_rules.py、outputs/更新记录.md
2. 检查重复、冲突、过宽匹配、注释与可选兼容规则是否仍默认关闭。

四、联网核查域名

优先厂商官方 network / firewall / sign-in / API 文档。至少核对 7 个服务及其登录、CDN、更新域是否仍有效；Cursor 须覆盖 api2–api5、authentication、repo42、spacex.ai、x.ai 等官方列表。

新增或修改域名须有可追溯来源；未核实项写入更新记录，不得声称已全部确认。单次 DNS/HTTP 失败不能作为删除域名的唯一依据。

五、代理范围控制

- 不要整站代理 google.com、github.com、microsoft.com、cloudflare.com 等共享平台。
- Gemini 等仍用窄域规则；共享登录/CDN 默认保持可选兼容段注释关闭。
- 不要使用 DOMAIN-KEYWORD 等宽泛规则。

六、修改与交付

1. 更新 AI-Only-Proxy.conf；同步 使用说明.md；在 outputs/更新记录.md 追加本次摘要（日期、变更、来源、未核实项、验证结果）。
2. 运行 python3 scripts/validate_rules.py，必须全部通过。
3. 验证要点：7 组策略名合法；Cursor/Grok 走 Cursor 组；无 Perplexity 等已删服务；未列域名（如 kimi.ai）走 FINAL 直连；FINAL,DIRECT 在最后。

七、Git 与 PR

若有依据的变更：创建分支 cursor/<描述>-9895，提交并 push，打开 PR 到 main（可用 ManagePullRequest）。用户若在本轮消息中明确要求合并，再执行 merge；否则 PR 即可，不必默认 merge。

完成后用中文简要报告：改了什么、规则数量、validate 结果、限制与 PR 链接。
```
