# Kubernetes Gateway Setup with Helm & kgateway (Envoy)

This repository contains the configuration required to deploy a Kubernetes Gateway using **K-Gateway**. This setup replaces traditional Ingress with the more expressive **Kubernetes Gateway API**, providing advanced routing for the banking application suite.

## 🏗️ Architecture Overview

The setup follows the **Kubernetes Gateway API** model. Here is how the traffic flows:

1.  **Traffic Entry:** External requests hit the **Gateway** (configured in `gateway.yaml`), which is managed by the **K-Gateway Controller**.
2.  **Envoy Proxy:** K-Gateway provisions an **Envoy Proxy** instance that listens for incoming traffic.
3.  **Routing logic:** The Envoy Proxy uses **HTTPRoutes** (configured in `httproutes.yaml`) to determine which microservice should handle the request based on the path prefix (e.g., `/api/users` goes to `user-service`).
4.  **Service Delivery:** Traffic is forwarded to the appropriate backend service (`account`, `frontend`, `transaction`, or `user`) within the `banking` namespace.

---

## 🚀 Setup Instructions

### Step 1: Install Helm
Helm is the package manager for Kubernetes required to install K-Gateway. Follow the official documentation to install it for your specific OS.

* **For Debian/Ubuntu:** [Helm Installation Guide](https://helm.sh/docs/intro/install/#from-apt-debianubuntu)

### Step 2: Install K-Gateway (CRDs & Controller)
We are installing K-Gateway from the Envoy Proxy repository. This will install the necessary Custom Resource Definitions (CRDs) and the K-Gateway controller.

* **Installation Guide:** [K-Gateway Helm Install](https://kgateway.dev/docs/envoy/main/install/helm/#install)

> [!IMPORTANT]
> Ensure your Kubernetes context is set to the correct cluster before running the Helm install commands.

### Step 3: Apply Gateway Manifests
Once the controller is running, you need to apply the networking configurations provided in this repository.

1.  **Deploy the Gateway:**
    This defines the entry point and the listener (ports) for your traffic.
    ```bash
    kubectl apply -f gateway.yaml
    ```

2.  **Deploy the HTTPRoutes:**
    This defines the routing rules for the `account`, `frontend`, `transaction`, and `user` services.
    ```bash
    kubectl apply -f httproutes.yaml
    ```

---

## 🛠️ Service Routing Summary

The following routes are configured in the `httproutes.yaml`:

| Service | Path Prefix | Target Port |
| :--- | :--- | :--- |
| **Frontend** | `/` | 80 |
| **Account Service** | `/api/accounts` | 3002 |
| **Transaction Service** | `/api/transactions` | 3003 |
| **User Service** | `/api/users` | 3001 |

---

## 🔍 Verification
To verify the setup is working correctly, run:
```bash
# Check if the Gateway has been assigned an IP address
kubectl get gateway -n banking

# Check the status of the routes
kubectl get httproute -n banking
```
