# Introduction 
Provide a sample for how to run 3LC in Docker and Kubernetes.

# Getting Started
1. Install Docker Desktop
2. Use WSL as backend
3. Enable Kubernetes in Docker Desktop
4. Install helm (either on windows or WSL)
5. Create this folder structure (assume Windows)
   ```
   mkdir mounts
   mkdir mounts\3lc
   mkdir mounts\3lc\project
   ```
6. Create .env with these fields for docker-compose to build/run
   ```
   # Used to download `3lc-enterprise` wheel from private 3LC package repository
   TLC_PYPI_ACCESS_KEY=
   TLC_PYPI_SECRET_KEY=
   # Used for license authentication at startup of `tlc` Python Package and Object Service
   # See also: https://docs.3lc.ai/3lc/latest/user-guide/enterprise-managed/licensing.html
   TLC_LICENSE=
   # Used to authenticate requests from 3LC Dashboard to Object Service
   # See also: https://docs.3lc.ai/3lc/latest/user-guide/enterprise-managed/3lc-managed-architecture.html#lc-managed-secure-communication
   TLC_OBJECT_SERVICE_AUTH_SECRET=
   ```
# Run the samples

The /mounts/3lc folder is configured to be mounted as /data on the Object Service node.

## Docker-Compose
1. Run with `docker-compose up --build`
2. Browse to http://localhost:8080 to access dashboard. The Object Service will run on http://localhost:8080/api

## Kubernetes via Docker Desktop
1. Modify docker-desktop.yml to fit your environment. The current config assumes that current folder is in C:/tlc/kubernetes-deployment-sample/enterprise-customer-managed.
   `licenseKey` is the cryptlex license key. `objectServiceAuthSecret` is the Object Service authentication secret.
2. run 
   ```
   # Add bitnami repo so we can use the nginx chart from it
   helm repo add bitnami https://charts.bitnami.com/bitnami
   # Build the chart
   helm dependency build ./helm
   # Deploy the chart
   helm upgrade -i tlc-demo ./helm --namespace tlc-demo --create-namespace -f docker-desktop.yml
   ```
3. Browse to http://localhost:30000 to access the Dashboard. The Object Service will run on http://localhost:30000/api

