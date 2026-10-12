# Phase 0 · Set up your workstation

**Time:** 1–2 hours · **You finish with:** the app running on your laptop and every check passing.

Everything in this repository runs from Python with one task runner, so after
setup the commands are identical on macOS and Windows. Only installation and
virtual-environment activation differ, and both are shown side by side below.

> **Shortcut:** if you use VS Code or GitHub Codespaces, open the repository in its
> dev container (`.devcontainer/devcontainer.json`). Python 3.14, Docker, kubectl,
> Helm and Terraform are installed for you, so you can skip to [step 5](#5-run-the-checks).

---

## 1. Get the code

Fork this repository on GitHub (the **Fork** button), then clone your fork. Same command everywhere:

| Step | Command (macOS Terminal and Windows PowerShell) |
|---|---|
| Clone your fork | `git clone https://github.com/<your-github-user>/Forkable-DevOps-Complete-StarterPack-To-FullSend.git` |
| Enter it | `cd Forkable-DevOps-Complete-StarterPack-To-FullSend` |

(No Git yet? Install it in step 2 first.)

## 2. Install the tools

Phase 0 needs only **Python** and **Git**. Docker is needed from Phase 3, and
kubectl, kind, Helm and Terraform from Phase 5 (their install tables are in
[Phase 5](../05-kubernetes-iac-cloud/README.md#install-the-cluster-tools)).

**Which Python?** Use **3.14**. Python 3.15.0 came out on 2026-10-09, three days
before this pack was written, and some packages may not ship wheels for it yet.
CI tests 3.13 and 3.14, and tries 3.15 without failing the build.

### macOS

| Tool | Command (Terminal) | Notes |
|---|---|---|
| Homebrew | `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"` | Package manager. Homebrew supports macOS Sequoia 15 and newer. |
| Python 3.14 | `brew install python@3.14` | Or the macOS installer from python.org. |
| Git | `brew install git` | Or `xcode-select --install` for Apple's bundled Git. |
| Docker Desktop | Download from the [Docker Desktop for Mac page](https://docs.docker.com/desktop/setup/install/mac-install/) | Needed from Phase 3. |

### Windows

Use **PowerShell**. `winget` is part of App Installer on Windows 11 and on
Windows 10 version 1809 or later; check with `winget --version`.

| Tool | Command (PowerShell) | Notes |
|---|---|---|
| Python Install Manager | `winget install 9NQ7512CXL7T -e --accept-package-agreements --disable-interactivity` | Command from the Python on Windows docs. Or install it from the Microsoft Store or python.org/downloads. |
| Python 3.14 | `py install 3.14` (open a new PowerShell window first) | The install manager is how the CPython team now ships Python for Windows. `py list` shows what is installed. |
| Git | `winget install --id Git.Git -e --source winget` | Command from git-scm.com. The winget package is not maintained by the Git for Windows project. |
| WSL 2 | `wsl --install` in PowerShell **run as Administrator**, then restart | Docker Desktop's default backend. Needs Windows 10 version 2004 (build 19041) or newer, or Windows 11. |
| Docker Desktop | Download from the [Docker Desktop for Windows page](https://docs.docker.com/desktop/setup/install/windows-install/) | Needed from Phase 3. Check its Windows edition and build requirements on that page. |

> **Docker Desktop licence:** it is free for personal use, education, non-commercial
> open source, and businesses with fewer than 250 employees **and** under $10 million
> annual revenue. Larger organisations need a paid subscription (Docker's install
> docs). On Linux, Docker Engine has no such requirement.

## 3. Create a virtual environment

A virtual environment keeps this project's packages separate from everything
else on your machine. These are the only commands that really differ.

### macOS

| Step | Command (Terminal) |
|---|---|
| Create | `python3.14 -m venv .venv` |
| Activate | `source .venv/bin/activate` |
| Check | `python --version` should print 3.14.x |
| Leave later | `deactivate` |

### Windows

| Step | Command (PowerShell) |
|---|---|
| Create | `py -V:3.14 -m venv .venv` |
| Allow activation scripts (once) | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| Activate | `.venv\Scripts\Activate.ps1` |
| Check | `python --version` should print 3.14.x |
| Leave later | `deactivate` |

The execution-policy command comes from the Python `venv` documentation; it lets
PowerShell run the signed activation script for your user only.

## 4. Install the project

From here on, every command is the same on macOS and Windows (with the virtual
environment active):

| Step | Command |
|---|---|
| Install the app, test tools, and a Chromium browser for Playwright | `python tasks.py setup` |
| See which other tools you have | `python phases/00-setup/doctor.py` |
| List every task | `python tasks.py` |

`tasks.py` replaces a Makefile: Make is not installed on Windows by default, and
shell syntax differs between platforms, but Python behaves the same everywhere.

## 5. Run the checks

| Step | Command | What you should see |
|---|---|---|
| Everything CI checks | `python tasks.py check` | `✓ all checks passed` |
| Browser tests | `python tasks.py e2e` | `5 passed` |
| Watch the browser tests | `python tasks.py e2e --headed` | A Chromium window clicking through the app |
| Run the app | `python tasks.py serve` | Open <http://127.0.0.1:8000> |
| This phase's self-check | `python -m pytest phases/00-setup` | All green |

Explore the running app:

| URL | What it is |
|---|---|
| <http://127.0.0.1:8000> | The UI: record deployments, see change fail rate |
| <http://127.0.0.1:8000/docs> | Interactive API docs that FastAPI builds from the code |
| <http://127.0.0.1:8000/metrics/> | Raw Prometheus metrics |
| <http://127.0.0.1:8000/healthz/ready> | The readiness probe Kubernetes will call |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `python: command not found` (macOS) | Use `python3.14`, or check that Homebrew's bin directory is on your PATH (Homebrew prints the line to add after installing). |
| `py` not found (Windows) | Open a new PowerShell window after installing the Python Install Manager. |
| `Activate.ps1 cannot be loaded because running scripts is disabled` | Run the `Set-ExecutionPolicy` command from step 3. |
| `playwright install` fails behind a corporate proxy | Ask IT to allow Playwright's browser download host, or set `E2E_CHROMIUM_EXECUTABLE` to an existing Chromium binary (see `tests/e2e/conftest.py`). |
| `Address already in use` on port 8000 | Something else uses the port: set `PORT=8001` (macOS: `PORT=8001 python tasks.py serve`; Windows: `$env:PORT=8001; python tasks.py serve`). |

## Done when

- [ ] `python tasks.py check` passes
- [ ] `python tasks.py e2e` passes
- [ ] You recorded a deployment in the UI and found it at `/api/v1/deployments`
- [ ] `python phases/00-setup/doctor.py` shows Python and Git as ready

## Official docs

- Python venv: <https://docs.python.org/3/library/venv.html>
- Python on Windows (install manager): <https://docs.python.org/3/using/windows.html>
- Homebrew: <https://brew.sh/>
- winget: <https://learn.microsoft.com/en-us/windows/package-manager/winget/>
- Git downloads: <https://git-scm.com/install/windows> · <https://git-scm.com/install/mac>
- WSL install: <https://learn.microsoft.com/en-us/windows/wsl/install>
- Docker Desktop: <https://docs.docker.com/desktop/setup/install/mac-install/> · <https://docs.docker.com/desktop/setup/install/windows-install/>

Next: [Phase 1 · Foundations](../01-foundations/README.md)
