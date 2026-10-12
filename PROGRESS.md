# My progress

Copy this file into your fork and tick boxes as you go (`- [x]`). Each line links a
skill from 2026 job postings ([SOURCES.md](SOURCES.md#hiring-signals)) to proof you
can show in an interview.

## Phase 0 · Setup
- [ ] `python tasks.py check` and `python tasks.py e2e` pass on my machine
- [ ] I recorded a deployment in the UI and found it in `/api/v1/deployments`

## Phase 1 · Foundations
- [ ] I can find a process, its port and its logs on macOS/Linux and on Windows
- [ ] I broke DNS, TCP and HTTP on purpose and recognised each from `net_probe.py`
- [ ] I saw round robin and a cache HIT in the Nginx lab
- [ ] I rewrote two coding warm-ups from memory and can state their complexity

## Phase 2 · Workflow
- [ ] My commits pass the Conventional Commits hook
- [ ] I added the `?service=` filter test-first, through a pull request with CI green
- [ ] My `AI_LOG.md` has at least three honest entries

## Phase 3 · Containers
- [ ] I built the image, ran it, and the smoke test passed against it
- [ ] `image_audit.py` passes and I can explain every Dockerfile line

## Phase 4 · CI/CD
- [ ] CI is green on my fork and a ruleset protects `main`
- [ ] An image built by CI runs on my laptop
- [ ] I have a DORA baseline from `dora_from_git.py`

## Phase 5 · Kubernetes, IaC, cloud
- [ ] Lab A: deployed on kind, broke it, rolled it back
- [ ] Lab B: installed, upgraded, tested and rolled back with Helm
- [ ] Lab C: Argo CD synced my fork and undid a manual change
- [ ] `tf_plan_guard.py` read a real plan or the test fixtures
- [ ] If I ran the EKS lab: `terraform destroy` finished and billing shows no cluster
- [ ] Stretch: CKA booked

## Phase 6 · Reliability
- [ ] I can explain every panel of the dashboard under load
- [ ] I caused an incident, followed the runbook and wrote a blameless postmortem
- [ ] I can do burn-rate maths on a whiteboard

## Phase 7 · Security and AI
- [ ] I can map each pipeline threat to the control that stops it
- [ ] I can tell the 2026 Trivy incident and its lessons in two minutes
- [ ] `secret_scan.py --staged` runs before my commits
- [ ] The triage agent explained a real failure on my fork with a read-only token

## Phase 8 · Capstone
- [ ] My own service, public, scored at least 2 in every rubric row
- [ ] A stranger followed my quick start on macOS **and** Windows
