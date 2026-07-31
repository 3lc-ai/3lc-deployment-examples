# 3LC Default Deployment Example

A worked example of running 3LC in **Docker Compose** and in **Kubernetes**.

The two are documented as separate deployments below. Read [Part 1](#part-1-docker-compose)
on its own if Docker Compose is all you need. [Part 2](#part-2-kubernetes-on-docker-desktop)
does not replace Part 1 - it *builds on* it, deploying the container images that Part 1
produces. See [How the two parts relate](#how-the-two-parts-relate).

Both parts serve plain HTTP. [Serving over HTTPS](#serving-over-https) is an optional
overlay that applies to either one, in two different topologies.

This is the **Default** (3LC-hosted account) deployment. Components authenticate with a
3LC account API key. For the licensed, fully self-hosted deployment, see
[`../enterprise-on-prem`](../enterprise-on-prem/README.md).

## What gets deployed

| Component | Image | Built from | Listens on | Purpose |
| --- | --- | --- | --- | --- |
| Object Service | `tlc-default-object-service:latest` | `object_service.Dockerfile` | 5015 | Serves 3LC table and run data |
| Compute Service | `tlc-default-compute-service:latest` | `compute_service.Dockerfile` | 5020 | Insights, training, import and export |
| nginx proxy | `nginx:alpine` | (pulled) | 80 | Single entry point; routes to the Object Service |

The Object Service is the `3lc` Python package's built-in service (`3lc service`), so the
image is just Python plus `pip install 3lc`.

## Configuration

Both parts read the same two settings, but each takes them from a different place:

| Setting | Docker Compose reads it from | Kubernetes reads it from |
| --- | --- | --- |
| 3LC account API key | `TLC_API_KEY` in `.env` | `global.apiKey`, passed to Helm - see [Configure](#configure) |
| Project storage location | the `./mounts/3lc` bind mount in `docker-compose.yml` | `global.pvc_host_path` in `docker-desktop.yml` |
| Compute Service plugin state | the `./mounts/3lc-compute` bind mount in `docker-compose.yml` | the same directory, reached with `subPath` on `global.pvc_host_path` |

Before either part, create the project folder:

```bat
mkdir mounts
mkdir mounts\3lc
mkdir mounts\3lc\project
mkdir mounts\3lc-compute
```

Then copy `.env.example` to `.env` **in this folder** and fill it in:

```bash
cp .env.example .env        # Windows cmd: copy .env.example .env
```

Docker Compose reads `.env` from the directory it runs in, so it must sit next to
`docker-compose.yml`. A `.env` at the repository root is **not** read. Kubernetes does not
read it at all, see [Configure](#configure) in Part 2.

`mounts/3lc` is mounted as `/data/3lc` inside the Object Service container, and
`TLC_PROJECT_ROOT_URL` points at `/data/3lc/project`, so 3LC projects written by
the service appear in `mounts/3lc/project` on your machine.

`mounts/3lc-compute` is mounted as `/root/.3lc-compute` inside the Compute Service, and
holds everything it remembers: `settings.json`, which records the installed plugins, and a
virtual environment per plugin under `managed-plugins/`. Without it an install appears to
succeed and the plugin then disappears the next time the container or pod is replaced,
because that state lives in the container's own filesystem. uv's wheel cache is kept
alongside them, so later installs reuse earlier downloads instead of fetching them again.

Both parts use the same host directory, so a plugin installed under Docker Compose is
already there in Kubernetes and the other way round. That is usually convenient. Avoid
installing plugins from both at the same time, though: each install rewrites the same
`settings.json`, so two that finish together can lose one of the entries.

## Part 1: Docker Compose

Self-contained. Requires only Docker.

### Prerequisites

1. Docker Desktop (WSL 2 backend on Windows)
2. `.env` and `mounts/` created as described under [Configuration](#configuration)

### Build and run

```bash
docker compose up --build
```

This builds `tlc-default-object-service:latest` and `tlc-default-compute-service:latest` and starts
them behind the nginx proxy.

### Access

| URL | Serves |
| --- | --- |
| <http://localhost:8080> | Object Service, through the nginx proxy |
| <http://localhost:8080/compute> | Compute Service, through the nginx proxy |
| <http://localhost:5001> | Object Service, published directly (bypasses the proxy) |
| <http://localhost:5002> | Compute Service, published directly (bypasses the proxy) |

### Verify

Both services expose an unauthenticated health endpoint, so the whole stack can be checked
without credentials:

```bash
curl http://localhost:8080/live            # Object Service, through the proxy
curl http://localhost:8080/compute/health  # Compute Service, through the proxy
```

Two `200`s mean the proxy is routing and both services started.

The Compute Service becomes ready a few seconds after the Object Service, so a **502** on
`/compute/health` right after `up` usually just means it is not listening yet. Retry before
investigating; if it persists, `docker compose logs compute_service`.

Anything other than `/live` returns **403** without authentication, which is correct - see
[Using the deployment](#using-the-deployment).

### Stop

```bash
docker compose down
```

### Where routing is defined

`default.conf`, mounted into the nginx container at `/etc/nginx/conf.d/default.conf`.
It proxies `/` to `object_service:5015`.

> Kubernetes uses a **second, separate** copy of this routing (see
> [Where routing is defined in Kubernetes](#where-routing-is-defined-in-kubernetes)).
> If you change one, change the other.

## Part 2: Kubernetes on Docker Desktop

Builds on Part 1.

### How the two parts relate

The Helm chart **does not build images**. It deploys the images Part 1 built:

```text
docker compose up --build                   Helm chart
  |                                         |
  +- builds tlc-default-object-service -----+ deploys it as the object-service Deployment
  |                                         |
  +- runs nginx with default.conf           + deploys nginx:alpine with the equivalent
                                              routing from helm/values.yaml
```

Two consequences:

- **You must run the Part 1 build first.** `docker-desktop.yml` sets
  `imagePullPolicy: Never`, which tells Kubernetes to use the image already in the local
  Docker daemon and never contact a registry. Without the compose build, the pod fails
  with `ErrImageNeverPull`.
- **Docker Desktop's Kubernetes shares the local image daemon**, which is why this works
  at all. This holds only for the Kubeadm provisioning method, not kind - see
  [Cluster provisioning method](#cluster-provisioning-method). On any other
  cluster you must push the images to a registry instead - see
  [Deploying to a real cluster](#deploying-to-a-real-cluster).

### Additional prerequisites

1. Everything from Part 1, and `docker compose build` (or `up --build`) has been run at least once
2. Kubernetes enabled in Docker Desktop, using the **Kubeadm** cluster provisioning
   method (see below)
3. `helm` installed (Windows or WSL)

#### Cluster provisioning method

Docker Desktop can provision its cluster two ways, chosen under
**Settings > Kubernetes > Cluster settings**. These examples require **Kubeadm**, not
**kind**. Check which you have with:

```bash
kubectl --context docker-desktop get nodes
```

| Node name | Provisioning method | Works with these examples |
| --- | --- | --- |
| `docker-desktop` | Kubeadm | Yes |
| `desktop-control-plane` | kind | No |

The difference that matters is the image store. A Kubeadm cluster shares the Docker
engine's images, which is what lets `imagePullPolicy: Never` find the images Part 1
built. kind instead requires Docker Desktop's containerd image store, as its entry in the
settings dialog notes, and runs its nodes as containers with their own containerd. The
same deployment therefore fails with `ErrImageNeverPull`, and the pinned NodePort is
unreachable on `localhost` because the node container publishes no ports.

### Configure

Kubernetes does **not** read `.env`, so the API key has to reach Helm some other way.
`deploy.sh` handles that for you: it reads `TLC_API_KEY` from `.env`, the same file Part 1
uses, and passes it to Helm.

`global.apiKey` in `docker-desktop.yml` is intentionally blank and should stay that way.
The file is tracked by git, so a key typed into it is one `git commit -a` away from being
published. If you run your own Helm command instead of `deploy.sh`, pass it the same way:

```bash
--set-string global.apiKey=$TLC_API_KEY
```

> Leaving it blank is caught by the chart, which stops before deploying anything:
> `global.apiKey is required`. Nothing reaches the cluster, so there is no
> half-deployed release to clean up.

Then edit `docker-desktop.yml` for the rest:

- `global.pvc_host_path` is the absolute path to this folder's `mounts` directory, in
  Docker Desktop's host-mount form. A Windows path like
  `C:\sources\tlc\3lc-deployment-examples\default\mounts` becomes
  `/run/desktop/mnt/host/c/sources/tlc/3lc-deployment-examples/default/mounts`. The
  checked-in value is an example and will not match your checkout.

### Deploy

> **Check which cluster you are about to deploy into.** Helm and kubectl act on your
> current kubectl context unless told otherwise, and on a developer machine that may be
> a shared or production cluster. Run `kubectl config current-context` to see what you
> would otherwise hit. Every command below pins the context explicitly to avoid surprises.

```bash
./deploy.sh                # deploys to the docker-desktop context
./deploy.sh my-cluster     # or name a different context explicitly
```

`deploy.sh` prints the context and cluster it resolved before it does anything, and fails
with the list of available contexts if the one you named does not exist. It reads
`TLC_API_KEY` from `.env`, the same file Part 1 uses, and passes it to Helm.

The equivalent command:

```bash
# Install or upgrade the release, pinned to the local Docker Desktop cluster.
# Every subchart is local, under helm/charts, so there is no chart repository
# to add and no dependencies to fetch.
helm upgrade -i tlc-demo ./helm \
  --kube-context docker-desktop \
  --namespace tlc-demo --create-namespace \
  -f docker-desktop.yml \
  --set-string global.apiKey=$TLC_API_KEY
```

This is what `deploy.sh` runs, minus the context checks. Use it directly if the key comes
from somewhere other than `.env`.

### Access through the NodePort

| URL | Serves |
| --- | --- |
| <http://localhost:30000> | Object Service, through the nginx proxy |
| <http://localhost:30000/compute> | Compute Service, through the nginx proxy |

Port 30000 is a NodePort pinned in `docker-desktop.yml` so the URL is predictable.
Note this differs from Part 1's port 8080 - the two can run side by side.

### Verify in the cluster

Wait for every pod to reach `Running` **and** `1/1` ready - a pod can be `Running` for a
few seconds before its readiness probe passes:

```bash
kubectl --context docker-desktop get pods -n tlc-demo
```

Then check the same two endpoints as Part 1, on the NodePort:

```bash
curl http://localhost:30000/live            # Object Service, through the proxy
curl http://localhost:30000/compute/health  # Compute Service, through the proxy
```

If a pod never becomes ready, `kubectl --context docker-desktop logs -n tlc-demo <pod>`
is the next step.

Because Part 1 uses port 8080 and Part 2 uses 30000, both can run at once and be compared
side by side.

### Uninstall

```bash
helm uninstall tlc-demo --kube-context docker-desktop --namespace tlc-demo
```

### Where routing is defined in Kubernetes

`helm/values.yaml`, under `nginx.serverBlock`: a Go-templated nginx server block rendered
into a ConfigMap by the in-repo `nginx` subchart and mounted as the proxy's
`/etc/nginx/conf.d/default.conf`. It is the Kubernetes counterpart to Part 1's `default.conf`
and must be kept in sync with it by hand.

### Deploying to a real cluster

`docker-desktop.yml` is a values overlay for the local-cluster case. For a real cluster,
supply your own overlay that changes:

| Value | Local (`docker-desktop.yml`) | Real cluster |
| --- | --- | --- |
| `global.containerRegistry` | empty | your registry, with trailing `/` |
| `global.imageTag` | `latest` | an immutable tag you pushed |
| `object-service.imagePullPolicy`, `compute-service.imagePullPolicy` | `Never` | `Always` (the chart default) |
| `global.dnsName` | `localhost:30000` | your real hostname, but see the note below |
| `global.apiKey` | a plain value in the pod spec | a Kubernetes Secret |
| `global.pvc_host_path` | a `hostPath` under Docker Desktop | a real PersistentVolumeClaim, replacing the `hostPath` volume |
| `nginx.service.type` and `nginx.service.nodePorts` | `NodePort` pinned to 30000 | `LoadBalancer` or an Ingress |
| replicas | `1`, hardcoded in the chart templates | set per component, with a PodDisruptionBudget |
| resource requests and limits | not set | set per component |

`global.dnsName` is declared in `helm/values.yaml` but **not consumed** by anything in
this surface - no component here derives a browser-facing URL from it. It is
meaningful in the Enterprise On-Prem surface, where the Dashboard's Object Service URL is
built from it.

Push the images built in Part 1 under the registry name first:

```bash
docker tag tlc-default-object-service:latest  <registry>/tlc-default-object-service:<tag>
docker tag tlc-default-compute-service:latest <registry>/tlc-default-compute-service:<tag>
docker push <registry>/tlc-default-object-service:<tag>
docker push <registry>/tlc-default-compute-service:<tag>
```

The `hostPath` volume is a demonstration convenience only - it pins the workload to one
node and is not appropriate for production.

## Using the deployment

The Object Service is an HTTP API, not a web UI. Browsing to it returns **403**: every
route except the `/live` health check requires authentication. That is expected, and not
a sign of a broken deployment.

To work with your data, open the 3LC Dashboard and tell it where this deployment is:

```text
https://dashboard.3lc.ai?object_service=http://localhost:8080
```

Use `http://localhost:30000` instead if you deployed with Part 2, or the https address
from [Serving over HTTPS](#serving-over-https) if you enabled that.

The Dashboard is hosted by 3LC and runs in your browser. The URL above is what points it
at your Object Service; your table and run data is fetched by the browser directly from
your own deployment. The Object Service allows cross-origin requests, which is what makes
this work.

> At startup the Object Service prints a `Dashboard URLs:` banner containing an address
> like `http://172.19.0.3:5015`. That is the container's address on the Docker network
> and is **not reachable from your browser**. Use the published URL above instead.

## Serving over HTTPS

Both parts above serve plain HTTP, which works on a single machine because browsers
treat `localhost` as a trustworthy origin. Serve any component from anywhere else and that
stops being true: a browser will not let an https page call a plain-HTTP service, so the
whole deployment has to move to https together.

In the Default deployment, the Hub and Dashboard you use are hosted by 3LC over https, and
they call the services deployed here from your browser. That works over plain HTTP today
only because they are on `localhost`. Move them to a shared host and they must be https.

The 3LC services cannot terminate TLS themselves. nginx does it, and the hop from nginx to
each service stays plain HTTP on the internal network. The browser sees https throughout.
This is the same arrangement an Ingress, a load balancer, or a corporate reverse proxy
uses, so swapping nginx for one of those only changes who holds the certificate and nothing
else.

Everything below is an overlay on Part 1 or Part 2. The base files are untouched, so plain
HTTP keeps working exactly as documented above.

> Unlike the HTTP setups, **the Compose and Kubernetes HTTPS deployments cannot run at the
> same time**: both bind port 443 on the host. Take one down before bringing the other up.

### Generate the certificates

```bash
./generate-certs.sh
```

This writes `certs/ca.crt`, `certs/tls.crt` and `certs/tls.key`. It runs openssl in a
container, so nothing needs installing, and `certs/` is gitignored.

No public certificate authority can issue for these names. `.localhost` is not a real
domain, so Let's Encrypt and similar have no way to validate ownership. Avoiding browser
warnings therefore means trusting the CA generated here.

### Trust the CA, once

| | |
| --- | --- |
| Windows | `certutil -user -addstore Root certs\ca.crt` |
| macOS | `sudo security add-trusted-cert -d -k /Library/Keychains/System.keychain certs/ca.crt` |
| Linux | copy `certs/ca.crt` into `/usr/local/share/ca-certificates/` and run `sudo update-ca-certificates` |

Firefox keeps its own trust store, so import there separately if you use it. To undo on
Windows: `certutil -user -delstore Root "3LC Default deployment example local CA"`.

In a real deployment you skip all of this and drop in a certificate from your own PKI, or
one issued by cert-manager in the cluster.

### Checking from the command line

Two things trip up `curl` here, and both apply to every Verify step below:

- **`*.localhost` does not resolve outside a browser.** Chrome, Edge and Firefox map these
  names to 127.0.0.1 themselves; the operating system resolver does not, and neither does
  `curl`. Pass `--resolve <host>:443:127.0.0.1`.
- **On Windows, `curl` uses Schannel**, the operating system TLS stack, which refuses to
  proceed when it cannot check certificate revocation. A private CA publishes no revocation
  list, so add `--ssl-revoke-best-effort` on Windows only. Without it you get
  `CRYPT_E_NO_REVOCATION_CHECK` or `the revocation status is unknown`. The certificate is
  fine; only that check fails.

If you would rather not trust the CA at all, add `--cacert certs/ca.crt` and the commands
work without the import. On Windows that does not replace `--ssl-revoke-best-effort` -
revocation is checked either way, so you need both.

### One hostname per component

This is the arrangement to copy. Each component gets its own address, which is how they
are laid out in a real deployment.

| URL | Serves |
| --- | --- |
| <https://object-service.localhost> | Object Service |
| <https://compute.localhost> | Compute Service |

Docker Compose:

```bash
docker compose -f docker-compose.yml -f docker-compose.tls-per-host.yml up --build
```

Kubernetes:

```bash
helm upgrade -i tlc-demo ./helm   --kube-context docker-desktop   --namespace tlc-demo --create-namespace   -f docker-desktop.yml -f tls-per-host-values.yaml   --set-file nginx.tls.crt=certs/tls.crt   --set-file nginx.tls.key=certs/tls.key
```

`--set-file` passes the certificate contents into the chart, which creates the
`kubernetes.io/tls` Secret, so there is no separate `kubectl create secret` step. The
Service becomes a `LoadBalancer` on 443 rather than the NodePort used for HTTP; Docker
Desktop binds that straight onto the host, so the URLs are the same as the Compose ones.

Because each component is told where the others are, any one of them can live
somewhere else. Point a URL at another host and only that component moves; nothing
else in the deployment changes.

Nothing is served under a path prefix here, so each component's own absolute paths work
untouched, and one certificate covers every name through its subject alternative names.

#### Verify the per-host setup

```bash
curl --resolve object-service.localhost:443:127.0.0.1 https://object-service.localhost/live
curl --resolve compute.localhost:443:127.0.0.1        https://compute.localhost/health
```

Add `--ssl-revoke-best-effort` on Windows, as described under
[Checking from the command line](#checking-from-the-command-line).

In a browser, open <https://object-service.localhost/live> and check for a padlock with no
warning. A warning here means the CA import did not take effect - restart the browser,
since trust decisions are cached for the life of the process.

The point of this topology is the two origins, so the browser is where it is really
confirmed: with the Dashboard pointed at `https://object-service.localhost`, its requests
to the Object Service are **cross-origin**, and the developer tools Network tab should show
them succeeding over https with no mixed-content warnings in the console.

### If you would rather use a single hostname

There is also a variant that puts everything behind one name, `3lc.localhost`, routed by
path. It needs one certificate and one DNS name, which suits a single-host pilot, but it
cannot express a deployment where components live in different places.

| URL | Serves |
| --- | --- |
| <https://3lc.localhost/> | Object Service |
| <https://3lc.localhost/compute/> | Compute Service |

```bash
docker compose -f docker-compose.yml -f docker-compose.tls-gateway.yml up --build
# or, for Kubernetes, swap tls-per-host-values.yaml for tls-gateway-values.yaml
```

#### Verify the single-hostname setup

```bash
curl --resolve 3lc.localhost:443:127.0.0.1 https://3lc.localhost/live
curl --resolve 3lc.localhost:443:127.0.0.1 https://3lc.localhost/compute/health
```

Under Docker Compose, plain HTTP is still published on 8080 and redirects:

```bash
curl -I http://3lc.localhost:8080/     # 301 to https://3lc.localhost/
```

The redirect drops the port, because 443 is the default for https.

**There is no such redirect on Kubernetes.** The Service is a `LoadBalancer` on 443 only,
so nothing answers on the HTTP NodePort in this variant. That difference between the two
deployment modes is expected, not a fault.

## Layout

| Path | Used by | Purpose |
| --- | --- | --- |
| `object_service.Dockerfile` | both | Object Service image definition |
| `compute_service.Dockerfile` | both | Compute Service image definition |
| `docker-compose.yml` | Part 1 - Docker | Service definitions, ports, env, bind mounts |
| `default.conf` | Part 1 - Docker | nginx routing |
| `.env.example` | Part 1 - Docker | Template listing the required variables |
| `.env` | Part 1 - Docker | Your filled-in copy of `.env.example` (not committed) |
| `helm/` | Part 2 - Kubernetes | Umbrella chart: `values.yaml` plus the per-component subcharts in `helm/charts` (object-service, nginx, and on Enterprise the dashboard). No external chart dependencies. |
| `docker-desktop.yml` | Part 2 - Kubernetes | Values overlay for the local Docker Desktop cluster |
| `deploy.sh` | Part 2 - Kubernetes | The Helm command above, with context checks and the secrets read from `.env` |
| `mounts/3lc/` | both | Host-side project storage (not committed) |
| `mounts/3lc-compute/` | both | Compute Service state: installed plugins, their virtual environments, and uv's cache (not committed) |
| `generate-certs.sh` | HTTPS | Creates the local CA and certificate in `certs/` |
| `tls-per-host.conf` | HTTPS, Part 1 | nginx config, one hostname per component |
| `docker-compose.tls-per-host.yml` | HTTPS, Part 1 | Compose overlay, one hostname per component |
| `tls-per-host-values.yaml` | HTTPS, Part 2 | Values overlay, one hostname per component |
| `tls-gateway.conf` | HTTPS, Part 1 | nginx config, single hostname |
| `docker-compose.tls-gateway.yml` | HTTPS, Part 1 | Compose overlay, single hostname |
| `tls-gateway-values.yaml` | HTTPS, Part 2 | Values overlay, single hostname |
