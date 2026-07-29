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

## What these examples are not

They are reference material, not production manifests. Specifically:

- Secrets are passed as plain environment variables and Helm values, not Kubernetes Secrets.
- Storage is a `hostPath` bind mount, not a PersistentVolumeClaim.
- Traffic is plain HTTP.
- The nginx routing is maintained twice per surface - once for Compose (`default.conf`),
  once for Helm (`nginx.serverBlock` in `helm/values.yaml`) - and the two must be kept in
  sync by hand.

Each README's "Deploying to a real cluster" section lists what to change.
