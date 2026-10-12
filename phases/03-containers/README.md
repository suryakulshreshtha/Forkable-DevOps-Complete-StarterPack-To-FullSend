# Phase 3 · Containers: build once, run anywhere

**Time:** 1–2 weeks · **Roadmap map:** milanm/DevOps-Roadmap step 6 (containers)

**You finish with:** a small, non-root, health-checked image of the app, built
the way production teams build them, and a tool that audits any image.

## Why hiring teams care

Every DevOps/SRE posting we read for this pack lists containers; NVIDIA's asks for
"advanced experience with Kubernetes (EKS) and Docker". Containers are also the
unit everything later in this pack ships: CI builds one, Kubernetes runs it,
Prometheus scrapes it.

---

## 1. Concepts in one table

| Idea | Meaning | Why it matters |
|---|---|---|
| Image | A read-only, layered filesystem plus start-up settings | Build once, run the identical thing in CI, staging and production |
| Container | A running process started from an image, isolated by the kernel | Cheap to start and throw away |
| Layer cache | Each Dockerfile instruction is a layer, reused if nothing above it changed | Order instructions from rarely-changing to often-changing for fast builds |
| Registry | Where images are stored and pulled from (GHCR here, Phase 4) | The hand-off point between CI and deployment |
| Tag vs digest | `python:3.14-slim-trixie` can move; `@sha256:…` never does | Pin digests in production; see the Phase 7 supply-chain story |
| Multi-stage build | Build in one stage, copy only results into a clean final stage | Compilers and caches never reach production |
| PID 1 and signals | The first process gets `SIGTERM` on `docker stop`, then `SIGKILL` after a grace period | Use exec-form `ENTRYPOINT [...]` so Python is PID 1 and receives the signal |

## 2. Read the Dockerfile

Open [`Dockerfile`](../../Dockerfile) next to this table.

| Line(s) | Why it is written that way |
|---|---|
| `ARG PYTHON_VERSION=3.14` | One place to change the Python version. |
| `FROM python:${PYTHON_VERSION}-slim-trixie AS build` | Docker Official Image, Debian 13 "slim": smaller and fewer packages to patch. |
| `COPY pyproject.toml …` before `COPY src` | Metadata changes rarely, so its layer stays cached. |
| `pip wheel --wheel-dir /wheels .` | Turns the app and its dependencies into wheels in the build stage. |
| second `FROM … AS runtime` | Starts again from a clean base; only the wheels cross over. |
| `useradd --uid 10001` and `USER 10001:10001` | Never run as root. A fixed UID lets Kubernetes verify `runAsNonRoot`. |
| `ENV HOST=0.0.0.0` | Inside a container the app must listen on all interfaces to be reachable. |
| `HEALTHCHECK …` | Docker marks the container unhealthy if `/healthz/live` stops answering. |
| `ENTRYPOINT ["python", "-m", "fullsend"]` | Exec form: no shell in between, so signals reach Python. |
| [`.dockerignore`](../../.dockerignore) | Ignores everything, then allows only what the build needs; secrets and `.git` never enter the build context. |

## 3. Lab: build, run, prove, audit

Docker commands are the same in macOS Terminal and Windows PowerShell (`$(...)`
works in both shells).

| Step | Command |
|---|---|
| Build, stamping the commit | `docker build --build-arg GIT_SHA=$(git rev-parse HEAD) -t fullsend:dev .` |
| Run, published on localhost only | `docker run -d --name fullsend -p 127.0.0.1:8000:8000 fullsend:dev` |
| Smoke test | `python scripts/smoke_test.py http://127.0.0.1:8000` |
| Read the JSON logs | `docker logs fullsend --tail 20` |
| Health as Docker sees it | `docker inspect --format "{{.State.Health.Status}}" fullsend` |
| Audit the image | `docker image inspect fullsend:dev > image.json` then `python phases/03-containers/image_audit.py image.json` |
| Layers and their sizes | `docker history fullsend:dev` |
| Stop cleanly (SIGTERM) and remove | `docker stop fullsend` then `docker rm fullsend` |

Then experiment:

1. **Cache:** change a string in `src/fullsend/main.py` and rebuild. Which steps say `CACHED`? Change `pyproject.toml` and rebuild. What changed, and why?
2. **Config at run time:** `docker run --rm -p 127.0.0.1:8000:8000 -e CHAOS_ERROR_RATE=0.5 fullsend:dev`, then run the smoke test a few times. Same image, different behaviour, no rebuild.
3. **Root check:** `docker run --rm --entrypoint id fullsend:dev` prints the user the app runs as.
4. **Break the audit on purpose:** comment out `USER 10001:10001`, rebuild, re-run `image_audit.py`, then restore it.

## 4. Several containers together: Compose

Compose describes multi-container setups in one YAML file. You have two in this repo:

| File | What it runs | Phase |
|---|---|---|
| [`phases/01-foundations/nginx-lab/compose.yaml`](../01-foundations/nginx-lab/compose.yaml) | Nginx load-balancing two app containers | 1 |
| [`observability/compose.yaml`](../../observability/compose.yaml) | App + Prometheus + Grafana | 6 |

| Step | Command |
|---|---|
| Start in the background, rebuilding images | `docker compose -f <file> up --build -d` |
| What is running | `docker compose -f <file> ps` |
| Logs of one service | `docker compose -f <file> logs <service>` |
| Stop and remove | `docker compose -f <file> down` |

## 5. Scanning images

CI builds the image and scans it with Trivy before anything is pushed (see the
`image` job in [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)): it fails
on HIGH or CRITICAL vulnerabilities that already have a fix. Notice that the Trivy
action is pinned to a full commit SHA, not a tag. Phase 7 tells the March 2026
supply-chain attack on Trivy's own GitHub Action that makes that pin matter.

## The Python tool in this phase

| Script | What it does |
|---|---|
| [`image_audit.py`](image_audit.py) | Reads `docker image inspect` JSON and checks non-root user, health check, exposed port, start command, secret-looking ENV values and size |

## Check yourself

```text
python -m pytest phases/03-containers
```

The checks also guard this repo's own `Dockerfile`: if someone removes the
`USER` line, the build of the course fails.

## Interview questions

1. What is the difference between an image and a container?
2. Why does instruction order in a Dockerfile change build speed?
3. Why run as a non-root user if the container is isolated anyway?
4. `docker stop` takes ten seconds and the app loses in-flight requests. What are two likely causes?
5. Shell form versus exec form for `ENTRYPOINT`: what breaks with the shell form?
6. When would you pin an image by digest instead of a tag? What do you give up?
7. How do you keep secrets out of an image, at build time and at run time?

## AI exercise (with guardrails)

Ask an assistant to review the `Dockerfile` for security and size. For every
suggestion: does it apply to this image? Try it, rebuild, and measure with
`image_audit.py` and `docker history`. Record which suggestions made things
better, which made no difference, and any that would have broken the app.

## Done when

- [ ] You built and ran the image, and the smoke test passed against it
- [ ] `image_audit.py` passes for your build
- [ ] You can explain each line of the Dockerfile without notes
- [ ] `python -m pytest phases/03-containers` passes

## Official docs

- Dockerfile reference: <https://docs.docker.com/reference/dockerfile/>
- Multi-stage builds: <https://docs.docker.com/build/building/multi-stage/>
- Building best practices: <https://docs.docker.com/build/building/best-practices/>
- `docker stop`: <https://docs.docker.com/reference/cli/docker/container/stop/>
- Compose file reference: <https://docs.docker.com/reference/compose-file/>
- Python Docker Official Image tags: <https://github.com/docker-library/official-images/blob/master/library/python>

Previous: [Phase 2](../02-workflow/README.md) · Next: [Phase 4 · CI/CD](../04-cicd/README.md)
