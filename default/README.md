# 3LC Default Deployment Example

A worked example of running 3LC in **Docker Compose** and in **Kubernetes**.

The two are documented as separate deployments below. Read [Part 1](#part-1-docker-compose)
on its own if Docker Compose is all you need. [Part 2](#part-2-kubernetes-on-docker-desktop)
does not replace Part 1 - it *builds on* it, deploying the container images that Part 1
produces. See [How the two parts relate](#how-the-two-parts-relate).

This is the **Default** (3LC-hosted account) deployment. Components authenticate with a
3LC account API key. For the licensed, fully self-hosted deployment, see
[`../enterprise-on-prem`](../enterprise-on-prem/README.md).

## What gets deployed

| Component | Image | Built from | Listens on | Purpose |
| --- | --- | --- | --- | --- |
| Object Service | `tlc-default-object-service:latest` | `object_service.Dockerfile` | 5015 | Serves 3LC table and run data |
| nginx proxy | `nginx:alpine` | (pulled) | 80 | Single entry point; routes to the Object Service |

The Object Service is the `3lc` Python package's built-in service (`3lc service`), so the
image is just Python plus `pip install 3lc`.

## Configuration

Both parts read the same two settings, but each takes them from a different place:

| Setting | Docker Compose reads it from | Kubernetes reads it from |
| --- | --- | --- |
| 3LC account API key | `TLC_API_KEY` in `.env` | `global.apiKey` in `docker-desktop.yml` |
| Project storage location | the `./mounts/3lc` bind mount in `docker-compose.yml` | `global.pvc_host_path` in `docker-desktop.yml` |

Before either part, create the project folder and the `.env` file:

```bat
mkdir mounts
mkdir mounts\3lc
mkdir mounts\3lc\project
```

`.env` (used by Docker Compose only; Kubernetes does not read it):

```ini
# 3LC account API key, used by the Object Service to authorize requests
TLC_API_KEY=
```

`mounts/3lc` is mounted as `/data/3lc` inside the Object Service container, and
`TLC_CONFIG_PROJECT_ROOT_URL` points at `/data/3lc/project`, so 3LC projects written by
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

This builds `tlc-default-object-service:latest` from `object_service.Dockerfile` and starts it
behind the nginx proxy.

### Access

| URL | Serves |
| --- | --- |
| <http://localhost:8080> | Object Service, through the nginx proxy |
| <http://localhost:5002> | Object Service, published directly (bypasses the proxy) |

`http://localhost:8080/live` is an unauthenticated health endpoint - a quick way to
confirm the stack is up.

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
  +- runs nginx with default.conf           + deploys bitnami/nginx with the equivalent
                                              routing from helm/values.yaml
```

Two consequences:

- **You must run the Part 1 build first.** `docker-desktop.yml` sets
  `imagePullPolicy: Never`, which tells Kubernetes to use the image already in the local
  Docker daemon and never contact a registry. Without the compose build, the pod fails
  with `ErrImageNeverPull`.
- **Docker Desktop's Kubernetes shares the local image daemon**, which is why this works
  at all. On any other cluster you must push the images to a registry instead - see
  [Deploying to a real cluster](#deploying-to-a-real-cluster).

### Additional prerequisites

1. Everything from Part 1, and `docker compose build` (or `up --build`) has been run at least once
2. Kubernetes enabled in Docker Desktop
3. `helm` installed (Windows or WSL)

### Configure

Edit `docker-desktop.yml`:

- `global.apiKey` is your 3LC account API key. Intentionally blank; the deploy fails
  without it. Kubernetes does **not** read `.env`.
- `global.pvc_host_path` is the absolute path to this folder's `mounts` directory, in
  Docker Desktop's host-mount form. A Windows path like
  `C:\sources\tlc\3lc-deployment-examples\default\mounts` becomes
  `/run/desktop/mnt/host/c/sources/tlc/3lc-deployment-examples/default/mounts`. The
  checked-in value is an example and will not match your checkout.

### Deploy

```bash
./deploy.sh
```

or equivalently:

```bash
# Add the bitnami repo so the chart can resolve its nginx dependency
helm repo add bitnami https://charts.bitnami.com/bitnami
# Fetch chart dependencies listed in helm/requirements.yaml
helm dependency build ./helm
# Install or upgrade the release
helm upgrade -i tlc-demo ./helm --namespace tlc-demo --create-namespace -f docker-desktop.yml
```

### Access through the NodePort

| URL | Serves |
| --- | --- |
| <http://localhost:30000> | Object Service, through the nginx proxy |

Port 30000 is a NodePort pinned in `docker-desktop.yml` so the URL is predictable.
Note this differs from Part 1's port 8080 - the two can run side by side.

### Verify

```bash
kubectl get pods -n tlc-demo
curl http://localhost:30000/live
```

### Uninstall

```bash
helm uninstall tlc-demo --namespace tlc-demo
```

### Where routing is defined in Kubernetes

`helm/values.yaml`, under `nginx.serverBlock`: a Go-templated nginx server block passed
to the bitnami nginx chart. It is the Kubernetes counterpart to Part 1's `default.conf`
and must be kept in sync with it by hand.

### Deploying to a real cluster

`docker-desktop.yml` is a values overlay for the local-cluster case. For a real cluster,
supply your own overlay that changes:

| Value | Local (`docker-desktop.yml`) | Real cluster |
| --- | --- | --- |
| `global.containerRegistry` | empty | your registry, with trailing `/` |
| `global.imageTag` | `latest` | an immutable tag you pushed |
| `object-service.imagePullPolicy` | `Never` | `Always` (the chart default) |
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
docker tag tlc-default-object-service:latest <registry>/tlc-default-object-service:<tag>
docker push <registry>/tlc-default-object-service:<tag>
```

The `hostPath` volume is a demonstration convenience only - it pins the workload to one
node and is not appropriate for production.

## Layout

| Path | Used by | Purpose |
| --- | --- | --- |
| `object_service.Dockerfile` | both | Object Service image definition |
| `docker-compose.yml` | Part 1 - Docker | Service definitions, ports, env, bind mounts |
| `default.conf` | Part 1 - Docker | nginx routing |
| `.env` | Part 1 - Docker | Secrets and keys (not committed) |
| `helm/` | Part 2 - Kubernetes | Umbrella chart: `values.yaml`, `requirements.yaml`, per-component charts |
| `docker-desktop.yml` | Part 2 - Kubernetes | Values overlay for the local Docker Desktop cluster |
| `deploy.sh` | Part 2 - Kubernetes | The three Helm commands above, scripted |
| `mounts/` | both | Host-side project storage (not committed) |
