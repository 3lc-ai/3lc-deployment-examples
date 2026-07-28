# 3LC Deployment Examples

Worked examples of deploying 3LC with Docker Compose and with Kubernetes.

## Pick a deployment surface

| | [`default/`](default/README.md) | [`enterprise-on-prem/`](enterprise-on-prem/README.md) |
| --- | --- | --- |
| **Use when** | You have a 3LC-hosted account | You self-host everything under a 3LC license |
| **Components** | Object Service, nginx proxy | Object Service, Dashboard, nginx proxy |
| **Authentication** | 3LC account API key (`TLC_API_KEY`) | License key (`TLC_LICENSE`) + shared auth secret |
| **Packages installed from** | the public 3LC index | the private 3LC index (requires PyPI keys) |

The two folders are independent and self-contained. They deliberately share no files, so
each can be copied out and adapted on its own - at the cost of some duplication between
them.

## Docker and Kubernetes

Each surface documents two deployments:

- **Part 1 - Docker Compose.** Self-contained. Builds the images and runs them. Requires
  only Docker.
- **Part 2 - Kubernetes.** Builds on Part 1. The Helm chart **does not build images**; it
  deploys the images Part 1 produced. On Docker Desktop this works because Kubernetes
  shares the local Docker image daemon; on any other cluster you push the images to a
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
