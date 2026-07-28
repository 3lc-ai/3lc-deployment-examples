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
  at all. This holds only for the Docker Desktop provisioning method, not kind - see
  [Kubernetes provisioning method](#kubernetes-provisioning-method). On any other
  cluster you must push the images to a registry instead - see
  [Deploying to a real cluster](#deploying-to-a-real-cluster).

### Additional prerequisites

1. Everything from Part 1, and `docker compose build` (or `up --build`) has been run at least once
2. Kubernetes enabled in Docker Desktop, using the **Docker Desktop** provisioning
   method (see below)
3. `helm` installed (Windows or WSL)

#### Kubernetes provisioning method

Docker Desktop can provision its cluster two ways, chosen under
**Settings > Kubernetes > Cluster settings**. These examples require the **Docker
Desktop** method, not **kind**. Check which you have with:

```bash
kubectl --context docker-desktop get nodes
```

| Node name | Provisioner | Works with these examples |
| --- | --- | --- |
| `docker-desktop` | Docker Desktop (kubeadm) | Yes |
| `desktop-control-plane` | kind | No |

The difference that matters is the image store. The Docker Desktop cluster shares the
Docker engine's images, which is what lets `imagePullPolicy: Never` find the images Part
1 built. A kind cluster runs its nodes as containers with their own containerd, so the
same deployment fails with `ErrImageNeverPull`, and the pinned NodePort is unreachable on
`localhost` because the node container publishes no ports.

If you must use kind, load each locally built image into the node first, and reach the
services with `kubectl port-forward` rather than the NodePort:

```bash
docker save <image>:latest | docker exec -i desktop-control-plane ctr -n k8s.io images import -
kubectl --context docker-desktop -n tlc-demo port-forward svc/tlc-demo-nginx 8080:80
```

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

The equivalent commands:

```bash
# Add the bitnami repo so the chart can resolve its nginx dependency
helm repo add bitnami https://charts.bitnami.com/bitnami
# Fetch chart dependencies listed in helm/requirements.yaml
helm dependency build ./helm
# Install or upgrade the release, pinned to the local Docker Desktop cluster
helm upgrade -i tlc-demo ./helm \
  --kube-context docker-desktop \
  --namespace tlc-demo --create-namespace \
  -f docker-desktop.yml
```

### Access through the NodePort

| URL | Serves |
| --- | --- |
| <http://localhost:30000> | Object Service, through the nginx proxy |

Port 30000 is a NodePort pinned in `docker-desktop.yml` so the URL is predictable.
Note this differs from Part 1's port 8080 - the two can run side by side.

### Verify

```bash
kubectl --context docker-desktop get pods -n tlc-demo
curl http://localhost:30000/live
```

### Uninstall

```bash
helm uninstall tlc-demo --kube-context docker-desktop --namespace tlc-demo
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
| `.env.example` | Part 1 - Docker | Template listing the required variables |
| `.env` | Part 1 - Docker | Your filled-in copy of `.env.example` (not committed) |
| `helm/` | Part 2 - Kubernetes | Umbrella chart: `values.yaml`, `requirements.yaml`, per-component charts |
| `docker-desktop.yml` | Part 2 - Kubernetes | Values overlay for the local Docker Desktop cluster |
| `deploy.sh` | Part 2 - Kubernetes | The three Helm commands above, scripted |
| `mounts/` | both | Host-side project storage (not committed) |
