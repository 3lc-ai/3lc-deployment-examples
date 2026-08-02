# 3LC Deployment Examples

Worked examples of deploying 3LC with Docker Compose and with Kubernetes.

## Pick a deployment surface

| | [`default/`](default/README.md) | [`enterprise-on-prem/`](enterprise-on-prem/README.md) |
| --- | --- | --- |
| **Use when** | You have a 3LC-hosted account | You self-host everything under a 3LC license |
| **Components** | Object Service, Compute Service, nginx proxy | Object Service, Compute Service, Dashboard, Hub, nginx proxy |
| **You browse to** | 3LC hosted Hub and Dashboard | self-hosted Hub and Dashboard |
| **Authentication** | 3LC account API key (`TLC_API_KEY`) | License key (`TLC_LICENSE`) plus a shared auth secret |
| **Packages installed from** | the public 3LC indexes | the private 3LC index for the Object Service, Dashboard and Hub; the public indexes for the Compute Service |

The two folders are independent and self-contained. They deliberately share no files, so
each can be copied out and adapted on its own - at the cost of some duplication between
them.

## What the components are

| Component | Port | Purpose |
| --- | --- | --- |
| Object Service | 5015 | Serves 3LC table and run data. An HTTP API, not a web UI |
| Compute Service | 5020 | Insights, training, import and export |
| Dashboard | 8080 | Web UI for exploring tables and runs. Self-hosted on Enterprise; the Default surface uses the 3LC-hosted one |
| Hub | 8081 | The primary web entry point. Self-hosted on Enterprise; the Default surface uses the 3LC-hosted one |
| nginx proxy | 80 | Single entry point that routes to all of the above |

Everything sits behind the proxy, so a deployment is reached at one address:

```text
Default                            Enterprise On-Prem
  /          Object Service          /                  Hub
  /compute/  Compute Service         /dashboard/        Dashboard
                                     /object-service/   Object Service
                                     /compute/          Compute Service
```

Each service is also published on its own host port for direct access, which the surface
READMEs list.

## Docker and Kubernetes

Each surface documents two deployments:

- **Part 1 - Docker Compose.** Self-contained. Builds the images and runs them. Requires
  only Docker.
- **Part 2 - Kubernetes.** Builds on Part 1. The Helm chart **does not build images**; it
  deploys the images Part 1 produced. This works on Docker Desktop because its Kubernetes
  shares the local Docker image store, which holds only when the cluster is provisioned
  with **Kubeadm** rather than kind. On any other cluster you push the images to a
  registry first.

So Part 1 stands alone, and Part 2 composes it. Each surface's README explains exactly
what is reused and what has to be configured a second time.

## Testing the examples

`tests/` exercises the deployments end to end: for each surface, each platform and each
topology it builds the images, brings the deployment up, checks every component answers,
and tears it down again. That is twelve combinations, and a full run takes five to ten
minutes.

```bash
uv sync                                             # once, to create the environment
uv run pytest                                       # all twelve combinations
uv run pytest -m compose                            # Compose only, about two minutes
uv run pytest -m kubernetes                         # Helm only, about four minutes
uv run pytest tests/default                         # one surface
uv run pytest tests/default/kubernetes              # one surface on one platform
uv run pytest tests/default/compose/test_http.py    # one combination
uv run pytest --keep-stack tests/default/compose/test_http.py   # leave it up, to poke at it
```

The tests are laid out by surface, then platform, one module per topology:

```text
tests/
  checks.py           the assertions, written once
  deployments.py      which components each surface serves, and at which URL
  conftest.py         brings a deployment up, waits for it, tears it down
  default/
    compose/          test_http.py  test_tls_per_host.py  test_tls_gateway.py
    kubernetes/       test_http.py  test_tls_per_host.py  test_tls_gateway.py
  enterprise_on_prem/
    compose/          ... the same three
    kubernetes/       ... the same three
```

Each test module is only wiring: it names its topology and subclasses the shared checks, so
an assertion is written once and runs against all twelve deployments. The Default surface has
no Dashboard or Hub, so those checks skip there rather than being duplicated away.

Configuration is resolved the way Docker Compose resolves it: from the environment when the
variable is set there, otherwise from the surface's `.env`. So a local run uses `.env`,
while CI can export the variables and never create the file. When a required value is
missing altogether the tests skip rather than fail, since that is a machine setup problem
and not a defect in the examples.

The HTTPS topologies need certificates, and the tests run `generate-certs.sh` for a surface
if its `certs/` is not already populated. They do **not** touch the operating system trust
store: each request is verified against the generated `certs/ca.crt` directly, so the tests
need no administrator rights and leave no trust changes behind. Trusting the CA, as the
surface READMEs describe, is only needed for a browser.

The Kubernetes deployments need `helm` and `kubectl` on PATH and a Kubeadm-provisioned
Docker Desktop cluster; they skip with a reason when any of that is absent. They build the
images with Compose first, because the chart deploys images rather than building them.

Only one deployment can run at a time, on either platform: both surfaces publish the same
host ports, and all four HTTPS deployments bind 443. The fixture therefore stops every
example deployment, Compose and Helm alike, before starting one. Running the tests will
take down a deployment you have up by hand.

### What the tests do and do not prove

They prove that **each component comes up and is reachable at its documented address**: the
services answer their health endpoints, the Dashboard and Hub return their own pages rather
than another component's, and the Hub's links resolve. That covers the routing, the
overlays, the certificates and the URLs the READMEs publish.

They do **not** prove that the components talk to each other. The Hub and Dashboard are
browser applications: they fetch from the Object Service and Compute Service from the
browser. Confirming the components are genuinely connected means either reproducing the
browser's authenticated API calls, or driving a real browser, which is beyond the scope of
these examples. To verify inter-connectivity, follow the "Verify..." sections in each
deployment README.

## What these examples are not

They are reference material, not production manifests. Specifically:

- Secrets are passed as plain environment variables and Helm values, not Kubernetes Secrets.
- Storage is a `hostPath` bind mount, not a PersistentVolumeClaim.
- Traffic is plain HTTP by default. Each surface documents an optional HTTPS variant,
  with certificates generated locally; a real deployment supplies its own.
- The nginx routing is maintained twice per surface - once for Compose (`default.conf`),
  once for Helm (`nginx.serverBlock` in `helm/values.yaml`) - and the two must be kept in
  sync by hand.

Each README's "Deploying to a real cluster" section lists what to change.
