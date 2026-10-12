# Phase 1 · Foundations: Linux, networking, servers

**Time:** 2–3 weeks · **Roadmap map:** milanm/DevOps-Roadmap steps 2 (one language), 3 (Linux & scripting), 4 (networking & security), 5 (server management)

**You finish with:** a working mental model of what happens between "I typed a URL"
and "the app answered", plus four Python tools you will keep using.

## Why hiring teams care

- NVIDIA's senior SRE posting asks for "production Linux administration at scale",
  and its DevOps postings ask for Python, Go or Bash automation.
- Google's SRE postings list data structures and algorithms, and troubleshooting
  distributed systems, in their minimum qualifications.

So this phase pairs Linux and networking with real coding. (Postings read on
2026-10-12; links in [SOURCES.md](../../SOURCES.md#hiring-signals).)

---

## 1. Where to practise Linux

Servers almost always run Linux, so practise on Linux even if your laptop does not.

| Your laptop | Where to practise | Why |
|---|---|---|
| macOS | Terminal for daily work; a Linux container or the dev container for Linux-specific commands | macOS ships BSD versions of tools like `sed` and `ps`, whose flags differ from the GNU versions on Linux servers. |
| Windows | WSL (Ubuntu) from Phase 0, or the dev container | A real Linux kernel and userland next to Windows. |

## 2. The shell commands you will use every day

| Task | macOS / Linux | Windows PowerShell |
|---|---|---|
| Where am I, what is here | `pwd` · `ls -la` | `Get-Location` · `Get-ChildItem -Force` |
| Find files | `find . -name "*.py"` | `Get-ChildItem -Recurse -Filter *.py` |
| Search inside files | `grep -rn "healthz" src` | `Get-ChildItem -Recurse src -Filter *.py \| Select-String healthz` |
| Follow a log | `tail -f app.log` | `Get-Content app.log -Wait -Tail 20` |
| Processes | `ps aux \| grep fullsend` | `Get-Process python` |
| Stop a process | `kill <pid>` (sends SIGTERM) | `Stop-Process -Id <pid>` |
| Listening ports | macOS: `lsof -iTCP -sTCP:LISTEN -n -P` · Linux: `ss -ltnp` | `Get-NetTCPConnection -State Listen` |
| Disk space | `df -h` · `du -sh *` | `Get-PSDrive -PSProvider FileSystem` |
| Environment variables | `echo $HOME` · `export APP_ENV=dev` | `$env:USERPROFILE` · `$env:APP_ENV = "dev"` |
| DNS lookup | `dig example.org` or `nslookup example.org` | `Resolve-DnsName example.org` |
| HTTP request | `curl -si http://127.0.0.1:8000/healthz/live` | `curl.exe -si http://127.0.0.1:8000/healthz/live` |

On Windows, type `curl.exe`, not `curl`: the kind documentation does the same in
PowerShell, because `curl` can resolve to a PowerShell command with different options.

## 3. Linux concepts that show up in every incident

| Concept | What to know | Where you meet it in this repo |
|---|---|---|
| Processes and signals | `SIGTERM` asks a process to stop cleanly; `SIGKILL` cannot be caught. | On SIGTERM, uvicorn stops accepting connections and lets in-flight requests finish (up to 20 s, `src/fullsend/__main__.py`); then the app's lifespan hook logs `stopping` and flushes traces (`src/fullsend/main.py`). Kubernetes sends SIGTERM first, then SIGKILL after the grace period. |
| Users and permissions | Never run services as root. Files have owner/group/other read-write-execute bits. | The image runs as UID 10001 (`Dockerfile`). Kubernetes enforces `runAsNonRoot`. |
| Exit codes and pipes | `0` means success, anything else is failure; CI stops on non-zero. `\|` passes output on. | Every `tasks.py` task and every script here returns a meaningful exit code. |
| Environment variables | Configuration that changes per environment, never baked into code. | `src/fullsend/config.py` reads `APP_ENV`, `CHAOS_ERROR_RATE` and friends. |
| Logs to stdout | Containers and systemd collect stdout; apps should not manage log files. | The app logs one JSON object per line to stdout. |
| Services | On Linux servers, `systemd` starts and restarts services; `journalctl -u <name>` shows their logs. | Kubernetes plays the same role for containers in Phase 5. |

**Lab: watch a clean shutdown.**

| Step | macOS / Linux | Windows PowerShell |
|---|---|---|
| Start the app in one terminal | `python tasks.py serve` | `python tasks.py serve` |
| Find its process ID in another | `ps aux \| grep "m fullsend"` | `Get-Process python` |
| Ask it to stop | `kill <pid>` | `Stop-Process -Id <pid>` |
| Read the first terminal | A JSON line with `"msg": "stopping"` | The process ends without that line: `Stop-Process` ends the process immediately, so the clean-shutdown path never runs. Press Ctrl+C in the app's own window instead to see a clean stop. |

## 4. Networking: one request, four layers

When "the site is down", find **which layer** is broken first; each one has a different owner.

```text
 you ──DNS──▶ name → IP ──TCP──▶ port open? ──TLS──▶ certificate valid? ──HTTP──▶ status code
       │                │                       │                            │
  "cannot resolve"  "connection refused"   "certificate expired"        "503 from the app"
```

| Layer | Know this | Common failure |
|---|---|---|
| DNS | A/AAAA records map names to addresses; CNAME points a name at another name; TTL is how long answers are cached. | A record changed but clients still use the old answer until the TTL expires. |
| TCP | A connection is to an IP **and** port. A closed port refuses instantly; a firewall usually makes the attempt hang until it times out. | App listening on 127.0.0.1 instead of 0.0.0.0 inside a container. |
| TLS | The server proves its identity with a certificate for the requested name (SNI). Certificates expire. | Expired certificate: everything breaks at once, on a date you could have predicted. |
| HTTP | Methods (GET reads, POST creates), status classes (2xx ok, 4xx caller's fault, 5xx server's fault), headers. | A 502/503 from a proxy means the proxy is fine but the app behind it is not. |

Private address ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) are not
routable on the internet; NAT translates them. The IPs in `sample-access.log` come
from the ranges reserved for documentation (RFC 5737), so they belong to no one.

**Lab: break each layer on purpose.** Start the app (`python tasks.py serve`), then:

| Try | Command (same on every OS) | Expected first failing layer |
|---|---|---|
| Healthy, plain HTTP | `python phases/01-foundations/net_probe.py 127.0.0.1 --port 8000 --http --path /healthz/ready` | none |
| A real HTTPS site | `python phases/01-foundations/net_probe.py example.org` | none; note the TLS version and days to expiry |
| Name that cannot exist | `python phases/01-foundations/net_probe.py fullsend.invalid` | DNS (`.invalid` is reserved, RFC 2606) |
| Wrong port | `python phases/01-foundations/net_probe.py 127.0.0.1 --port 8001 --http` | TCP |
| Server error | Stop the app and start it with chaos on (macOS: `CHAOS_ERROR_RATE=1 python tasks.py serve`, Windows: `$env:CHAOS_ERROR_RATE=1; python tasks.py serve`), then probe `--path /api/v1/info` | HTTP (503) |

## 5. Server management: proxies, load balancers, caches

| Term | One-line meaning |
|---|---|
| Reverse proxy | Sits in front of your servers; clients talk to it, it talks to the app (Nginx, cloud load balancers, Kubernetes Ingress). |
| Forward proxy | Sits in front of clients; your requests go out through it (corporate proxies). |
| Load balancing | Spreads requests across several backends: round robin, least connections, or by client IP. |
| Health checks | The balancer stops sending traffic to a backend that fails its check. |
| Caching | Keep a recent answer and reuse it; trades freshness for speed and load. |
| TLS termination | The proxy handles HTTPS so backends can speak plain HTTP on a private network. |

**Lab: Nginx in front of two app containers** (needs Docker; do it now if Docker
is installed, otherwise come back after Phase 3). Files: [`nginx-lab/`](nginx-lab/).

| Step | macOS / Linux | Windows PowerShell |
|---|---|---|
| Start | `docker compose -f phases/01-foundations/nginx-lab/compose.yaml up --build -d` | same |
| Load balancing: run 4 times, watch `X-Upstream` change | `curl -si http://127.0.0.1:8080/api/v1/deployments \| grep -i x-upstream` | `curl.exe -si http://127.0.0.1:8080/api/v1/deployments \| Select-String X-Upstream` |
| Caching: run twice within 10 s, watch `MISS` then `HIT` | `curl -si http://127.0.0.1:8080/api/v1/info \| grep -i x-cache` | `curl.exe -si http://127.0.0.1:8080/api/v1/info \| Select-String X-Cache` |
| Analyse the proxy's log | `docker compose -f phases/01-foundations/nginx-lab/compose.yaml logs nginx --no-log-prefix \| python phases/01-foundations/log_report.py -` | same |
| Stop | `docker compose -f phases/01-foundations/nginx-lab/compose.yaml down` | same |

Question to answer in your notes: each backend keeps its own in-memory list of
deployments. Record one through the proxy, then list deployments several times.
What do you see, and why do real services keep state in a database instead?

## 6. The Python tools in this phase

| Script | What it does | Try |
|---|---|---|
| [`sysinfo.py`](sysinfo.py) | Host, OS, CPUs, load, disk, with warnings | `python phases/01-foundations/sysinfo.py` |
| [`net_probe.py`](net_probe.py) | DNS → TCP → TLS → HTTP, timed, stops at the first failure | see the lab above |
| [`log_report.py`](log_report.py) | Error rate, latency percentiles, top paths and clients from an access log | `python phases/01-foundations/log_report.py phases/01-foundations/sample-access.log` |
| [`dsa_warmups.py`](dsa_warmups.py) | Five interview-style problems from real ops work | read, then rewrite from scratch |

## 7. Coding-round warm-ups

[`dsa_warmups.py`](dsa_warmups.py) has five problems: top-k busy clients (heap),
a sliding-window rate limiter (deque), an LRU cache (ordered dict), merging
maintenance windows (sort + sweep), and a safe deploy order (topological sort).
For each: say the time complexity out loud, delete the body, rewrite it, and run
the checks.

## Check yourself

```text
python -m pytest phases/01-foundations
```

## Interview questions

1. A user says the site is down. Walk through how you find which layer is failing, and the command you would use at each layer.
2. What is the difference between a 502, a 503 and a 504 from a reverse proxy?
3. Why might a DNS change take hours to reach some users but not others?
4. Your container starts, but nothing outside it can connect. The app logs "listening on 127.0.0.1:8000". What is wrong?
5. What happens to in-flight requests when a process gets SIGTERM versus SIGKILL? How should a web service handle SIGTERM?
6. When would you choose least-connections over round-robin load balancing?
7. What can go wrong when you put a cache in front of an API that returns user-specific data?
8. Explain p50 versus p99 latency. Why is an average latency misleading?

## AI exercise (with guardrails)

Run `net_probe.py` against a host that fails, paste **only the output** into an AI
assistant, and ask it to explain the failure and suggest the next diagnostic
command. Then:

- Run the suggested command yourself and check the claim. Assistants can be confidently wrong about flags and outputs.
- Never paste secrets, internal hostnames or customer data into an external assistant.
- Record the prompt, the answer, and what you verified in your AI log (Phase 2 explains the log).

## Done when

- [ ] You can find a process, its port and its logs on macOS/Linux and on Windows
- [ ] You broke each network layer on purpose and recognised it from the output
- [ ] You saw round robin and a cache HIT in the Nginx lab (after Docker is installed)
- [ ] `python -m pytest phases/01-foundations` passes
- [ ] You rewrote at least two of the warm-ups from memory

## Official docs

- GNU Bash manual: <https://www.gnu.org/software/bash/manual/>
- Linux man pages: <https://man7.org/linux/man-pages/>
- Python `socket` and `ssl`: <https://docs.python.org/3/library/socket.html> · <https://docs.python.org/3/library/ssl.html>
- HTTP semantics, RFC 9110: <https://www.rfc-editor.org/rfc/rfc9110>
- TLS 1.3, RFC 8446: <https://www.rfc-editor.org/rfc/rfc8446>
- Documentation IP ranges, RFC 5737: <https://www.rfc-editor.org/rfc/rfc5737> · reserved names, RFC 2606: <https://www.rfc-editor.org/rfc/rfc2606>
- Nginx upstream, proxy and log modules: <https://nginx.org/en/docs/http/ngx_http_upstream_module.html> · <https://nginx.org/en/docs/http/ngx_http_proxy_module.html> · <https://nginx.org/en/docs/http/ngx_http_log_module.html>
- Python `graphlib` (topological sort): <https://docs.python.org/3/library/graphlib.html>

Previous: [Phase 0](../00-setup/README.md) · Next: [Phase 2 · Workflow](../02-workflow/README.md)
