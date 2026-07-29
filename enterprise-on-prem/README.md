# 3LC Enterprise On-Prem Deployment Example

A worked example of running 3LC in **Docker Compose** and in **Kubernetes**.

The two are documented as separate deployments below. Read [Part 1](#part-1-docker-compose)
on its own if Docker Compose is all you need. [Part 2](#part-2-kubernetes-on-docker-desktop)
does not replace Part 1 - it *builds on* it, deploying the container images that Part 1
produces. See [How the two parts relate](#how-the-two-parts-relate).

This is the **Enterprise On-Prem** deployment: fully self-hosted, licensed, with no
dependency on a 3LC-hosted account. For the 3LC-hosted variant, see
[`../default`](../default/README.md).

## What gets deployed

| Component | Image | Built from | Listens on | Purpose |
| --- | --- | --- | --- | --- |
| Object Service | `tlc-enterprise-object-service:latest` | `object_service.Dockerfile` | 5015 | Serves 3LC table and run data |
| Dashboard | `tlc-enterprise-dashboard:latest` | `dashboard.Dockerfile` | 8080 | 3LC web UI |
| nginx proxy | `nginx:alpine` | (pulled) | 80 | Single entry point; routes to the Dashboard and Object Service |

Both 3LC images install from the **private** 3LC package repository and so require
`TLC_PYPI_ACCESS_KEY` and `TLC_PYPI_SECRET_KEY` at build time. This is the main build-time
difference from the Default deployment, which installs from the public index.

### How the components authenticate

Three distinct secrets:

| Secret | Held by | Purpose |
| --- | --- | --- |
| `TLC_PYPI_ACCESS_KEY`, `TLC_PYPI_SECRET_KEY` | the Docker build | Download the `3lc` and `3lc-dashboard` wheels from the private repository. Build-time only; not present in the running containers. |
| `TLC_LICENSE` | Object Service | 3LC license key, validated at startup. See [licensing](https://docs.3lc.ai/3lc/latest/getting-started/deployment-options/enterprise-on-prem/licensing.html). |
| `TLC_OBJECT_SERVICE_AUTH_SECRET` | Dashboard **and** Object Service | Shared secret authenticating Dashboard-to-Object-Service requests. Must be identical on both. See [secure communication](https://docs.3lc.ai/3lc/latest/getting-started/deployment-options/enterprise-on-prem/secure-communication.html). |

## Configuration

Both parts need the same settings, but each takes them from a different place:

| Setting | Docker Compose reads it from | Kubernetes reads it from |
| --- | --- | --- |
| PyPI access and secret keys | `.env`, passed as build args | not read; images are built by Part 1 |
| License key | `TLC_LICENSE` in `.env` | `global.licenseKey` in `docker-desktop.yml` |
| Object Service auth secret | `TLC_OBJECT_SERVICE_AUTH_SECRET` in `.env` | `global.objectServiceAuthSecret` in `docker-desktop.yml` |
| Project storage location | the `./mounts/3lc` bind mount in `docker-compose.yml` | `global.pvc_host_path` in `docker-desktop.yml` |

Before either part, create the project folder:

```bat
mkdir mounts
mkdir mounts\3lc
mkdir mounts\3lc\project
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

## Part 1: Docker Compose

Self-contained. Requires only Docker.

### Prerequisites

1. Docker Desktop (WSL 2 backend on Windows)
2. `.env` and `mounts/` created as described under [Configuration](#configuration)

### Build and run

```bash
docker compose up --build
```

This builds `tlc-enterprise-object-service:latest` and `tlc-enterprise-dashboard:latest` and starts them behind
the nginx proxy.

### Access

| URL | Serves |
| --- | --- |
| <http://localhost:8080> | Dashboard, through the nginx proxy |
| <http://localhost:8080/api> | Object Service, through the nginx proxy |
| <http://localhost:5001> | Dashboard, published directly (bypasses the proxy) |
| <http://localhost:5002> | Object Service, published directly (bypasses the proxy) |

`http://localhost:8080/api/live` is an unauthenticated health endpoint - a quick way to
confirm the Object Service is up.

Note the Dashboard is told where the Object Service is via a command override in
`docker-compose.yml`: `--object-service http://localhost:8080/api`. That URL is resolved
by the **browser**, not by the Dashboard container, which is why it is a `localhost`
address rather than a container name.

### Stop

```bash
docker compose down
```

### Where routing is defined

`default.conf`, mounted into the nginx container at `/etc/nginx/conf.d/default.conf`.
It proxies `/` to `dashboard:8080` and `/api/` to `object_service:5015`.

> Kubernetes uses a **second, separate** copy of this routing (see
> [Where routing is defined in Kubernetes](#where-routing-is-defined-in-kubernetes)).
> If you change one, change the other.

## Part 2: Kubernetes on Docker Desktop

Builds on Part 1.

### How the two parts relate

The Helm chart **does not build images**. It deploys the images Part 1 built:

```text
docker compose up --build                      Helm chart
  |                                            |
  +- builds tlc-enterprise-object-service -----+ deploys it as the object-service Deployment
  +- builds tlc-enterprise-dashboard ----------+ deploys it as the dashboard Deployment
  |                                            |
  +- runs nginx with default.conf              + deploys nginx:alpine with the equivalent
                                                 routing from helm/values.yaml
```

Two consequences:

- **You must run the Part 1 build first.** `docker-desktop.yml` sets
  `imagePullPolicy: Never`, which tells Kubernetes to use the images already in the local
  Docker daemon and never contact a registry. Without the compose build, the pods fail
  with `ErrImageNeverPull`.
- **Docker Desktop's Kubernetes shares the local image daemon**, which is why this works
  at all. This holds only for the Kubeadm provisioning method, not kind - see
  [Cluster provisioning method](#cluster-provisioning-method). On any other
  cluster you must push the images to a registry instead - see
  [Deploying to a real cluster](#deploying-to-a-real-cluster).

The PyPI keys are needed only by the Part 1 build, so they never appear in the Helm
values. The license key and auth secret *are* needed at runtime, so they must be supplied
again in `docker-desktop.yml`.

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

Edit `docker-desktop.yml`:

- `global.licenseKey` is your 3LC license key. Intentionally blank; the deploy fails
  without it. Kubernetes does **not** read `.env`.
- `global.objectServiceAuthSecret` is the shared Dashboard-to-Object-Service secret. Also
  intentionally blank.
- `global.dnsName` is how a **browser** reaches the deployment. `helm/values.yaml` builds
  the Dashboard's Object Service URL as `http://{dnsName}/api`, so this must be an address
  that resolves from the browser: `localhost:30000` locally, your real hostname otherwise.
- `global.pvc_host_path` is the absolute path to this folder's `mounts` directory, in
  Docker Desktop's host-mount form. A Windows path like
  `C:\sources\tlc\3lc-deployment-examples\enterprise-on-prem\mounts` becomes
  `/run/desktop/mnt/host/c/sources/tlc/3lc-deployment-examples/enterprise-on-prem/mounts`.
  The checked-in value is an example and will not match your checkout.

Both secrets are passed as plain values into the pod spec here, to keep the example
readable. In a real deployment, use Kubernetes Secrets.

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
with the list of available contexts if the one you named does not exist.

The equivalent command:

```bash
# Install or upgrade the release, pinned to the local Docker Desktop cluster.
# Every subchart is local, under helm/charts, so there is no chart repository
# to add and no dependencies to fetch.
helm upgrade -i tlc-demo ./helm \
  --kube-context docker-desktop \
  --namespace tlc-demo --create-namespace \
  -f docker-desktop.yml
```

### Access through the NodePort

| URL | Serves |
| --- | --- |
| <http://localhost:30000> | Dashboard, through the nginx proxy |
| <http://localhost:30000/api> | Object Service, through the nginx proxy |

Port 30000 is a NodePort pinned in `docker-desktop.yml` so the URL is predictable and
matches `global.dnsName`. Note this differs from Part 1's port 8080 - the two can run side
by side.

### Verify

```bash
kubectl --context docker-desktop get pods -n tlc-demo
curl http://localhost:30000/api/live
```

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
| `dashboard.imagePullPolicy`, `object-service.imagePullPolicy` | `Never` | `Always` (the chart default) |
| `global.dnsName` | `localhost:30000` | your real hostname; the Dashboard's Object Service URL is built from it |
| `global.licenseKey`, `global.objectServiceAuthSecret` | plain values in the pod spec | Kubernetes Secrets |
| `global.pvc_host_path` | a `hostPath` under Docker Desktop | a real PersistentVolumeClaim, replacing the `hostPath` volume |
| `nginx.service.type` and `nginx.service.nodePorts` | `NodePort` pinned to 30000 | `LoadBalancer` or an Ingress |
| replicas | `1`, hardcoded in the chart templates | set per component, with a PodDisruptionBudget |
| resource requests and limits | not set | set per component |

Push the images built in Part 1 under the registry name first:

```bash
docker tag tlc-enterprise-object-service:latest <registry>/tlc-enterprise-object-service:<tag>
docker tag tlc-enterprise-dashboard:latest      <registry>/tlc-enterprise-dashboard:<tag>
docker push <registry>/tlc-enterprise-object-service:<tag>
docker push <registry>/tlc-enterprise-dashboard:<tag>
```

The `hostPath` volume is a demonstration convenience only - it pins the workload to one
node and is not appropriate for production.

## Using the deployment

Browse to <http://localhost:8080>, or <http://localhost:30000> if you deployed with Part
2. The Dashboard is served from your own deployment; unlike the Default deployment,
nothing is hosted by 3LC.

The Object Service sits behind the same entry point under `/api`. It is an HTTP API, not
a web UI: `/api/` returns **403** because every route except the `/api/live` health check
requires authentication. That is expected, and not a sign of a broken deployment.

> At startup the Object Service prints its own address, for example
> `http://172.19.0.4:5015`. That is the container's address on the Docker network and is
> **not reachable from your browser**. Use the published URLs above instead.

## Layout

| Path | Used by | Purpose |
| --- | --- | --- |
| `object_service.Dockerfile` | both | Object Service image definition |
| `dashboard.Dockerfile` | both | Dashboard image definition |
| `docker-compose.yml` | Part 1 - Docker | Service definitions, ports, env, bind mounts |
| `default.conf` | Part 1 - Docker | nginx routing |
| `.env.example` | Part 1 - Docker | Template listing the required variables |
| `.env` | Part 1 - Docker | Your filled-in copy of `.env.example` (not committed) |
| `helm/` | Part 2 - Kubernetes | Umbrella chart: `values.yaml` plus the per-component subcharts in `helm/charts` (object-service, nginx, and on Enterprise the dashboard). No external chart dependencies. |
| `docker-desktop.yml` | Part 2 - Kubernetes | Values overlay for the local Docker Desktop cluster |
| `deploy.sh` | Part 2 - Kubernetes | The three Helm commands above, scripted |
| `mounts/` | both | Host-side project storage (not committed) |
