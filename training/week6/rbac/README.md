# Kubernetes RBAC Hands-on Guide

## 📌 Overview

This lab demonstrates how Kubernetes **Role-Based Access Control (RBAC)** works by:

* Creating users using certificates
* Assigning roles and permissions
* Testing access control across namespaces
* Using Service Accounts for in-cluster access

---

## 🧑‍💻 1. Create Users and Configure Authentication

### 🔑 Step 1: Generate Private Keys

```bash
openssl genrsa -out user1.key 2048
openssl genrsa -out user2.key 2048
```

**Explanation:**

* Generates RSA private keys for `user1` and `user2`
* These keys will be used for authentication
* `2048` → key size (secure enough for most cases)

---

### 📄 Step 2: Generate Certificate Signing Requests (CSR)

```bash
openssl req -new -key user1.key -out user1.csr -subj "/CN=user1/O=dev"
openssl req -new -key user2.key -out user2.csr -subj "/CN=user2/O=QA"
```

**Explanation:**

* Creates CSRs for both users
* `/CN` (Common Name) → username in Kubernetes
* `/O` (Organization) → group (used for RBAC)

  * user1 → dev group
  * user2 → QA group

---

### 🔍 Step 3: Verify Files

```bash
ls | grep user
```

**Explanation:**

* Confirms keys and CSR files are created successfully

---

### 🔐 Step 4: Sign Certificates Using Kubernetes CA

```bash
openssl x509 -req -CA /etc/kubernetes/pki/ca.crt -CAkey /etc/kubernetes/pki/ca.key -CAcreateserial -days 730 -in user1.csr -out user1.crt

openssl x509 -req -CA /etc/kubernetes/pki/ca.crt -CAkey /etc/kubernetes/pki/ca.key -CAcreateserial -days 730 -in user2.csr -out user2.crt
```

**Explanation:**

* Signs CSR with Kubernetes Certificate Authority
* Produces `.crt` files (client certificates)
* `-days 730` → valid for 2 years

---

### ⚙️ Step 5: Add Users to kubeconfig

```bash
kubectl config set-credentials user1 --client-certificate=user1.crt --client-key=user1.key

kubectl config set-credentials user2 --client-certificate=user2.crt --client-key=user2.key
```

**Explanation:**

* Adds users to kubeconfig
* Associates cert + key with each user
* Enables kubectl to authenticate as these users

---

### 🔎 Step 6: Verify kubeconfig

```bash
cat ~/.kube/config
```

**Explanation:**

* Confirms both users are registered in kubeconfig

---

## 📦 2. Create Namespace

```bash
kubectl create ns rbac
```

**Explanation:**

* Creates isolated namespace `rbac`
* RBAC rules will be applied here

---

## 🔄 3. Create Contexts for Users

```bash
kubectl config set-context user1-context --cluster=kubernetes --user=user1 --namespace=rbac

kubectl config set-context user2-context --cluster=kubernetes --user=user2 --namespace=rbac
```

**Explanation:**

* Context = (cluster + user + namespace)
* Allows switching between users easily

---

### 🔍 Verify Contexts

```bash
kubectl config get-contexts
```

* `*` indicates current active context

---

## 🚫 4. Test Access (Before RBAC)

```bash
kubectl config use-context user1-context
kubectl get pods
```

**Expected Output:** Permission Denied

**Explanation:**

* No roles assigned yet → access is blocked

---

## 🔐 5. Apply RBAC Roles and Bindings

Switch back to admin:

```bash
kubectl config use-context kubernetes-admin@kubernetes
```

Apply RBAC configs:

```bash
kubectl apply -f dev_role.yaml
kubectl apply -f dev_rolebinding.yaml
kubectl apply -f QA_role.yaml
kubectl apply -f QA_rolebinding.yaml
```

---

### 🔍 Verify

```bash
kubectl get roles -n rbac
kubectl get rolebindings -n rbac
```

---

### 📘 Note: Check Available Verbs

```bash
kubectl api-resources -o wide | grep pod
```

**Explanation:**

* Shows allowed operations like:

  * get, list, create, delete

---

## 🚀 6. Create Pod as user1

```bash
kubectl config use-context user1-context
kubectl run mypod --image=nginx
```

**Explanation:**

* user1 now has permission via dev role
* Creates pod successfully

---

## 👀 7. Access Pod as user2

```bash
kubectl config use-context user2-context
kubectl get pods
```

**Explanation:**

* user2 can view pods (based on QA role permissions)

---

## 🌐 8. Create Pod in Another Namespace

```bash
kubectl config use-context kubernetes-admin@kubernetes
kubectl create ns demo
kubectl run mypod2 --image=nginx -n demo
```

---

## 🚫 9. Access Denied in Another Namespace

```bash
kubectl config use-context user2-context
kubectl get pods -n demo
```

**Expected:** Permission Denied

---

### 🔍 Check Permissions

```bash
kubectl auth can-i list pods --as=user2 -n demo
```

**Explanation:**

* Verifies if user has permission → returns `no`

---

## 🌍 10. Apply Cluster Role for Cross-Namespace Access

```bash
kubectl config use-context kubernetes-admin@kubernetes

kubectl apply -f QA_cluster_role.yaml
kubectl apply -f QA_cluster_binding.yaml
```

**Explanation:**

* ClusterRole → works across all namespaces
* ClusterRoleBinding → assigns it to user2

---

## ✅ 11. Access Pod Again

```bash
kubectl config use-context user2-context
kubectl get pods -n demo
```

**Expected:** Success

---

## 🤖 12. Service Account (Default Behavior)

```bash
kubectl config use-context kubernetes-admin@kubernetes
kubectl apply -f sapod.yaml
kubectl exec -it sapod -n rbac -- sh
kubectl get pods
```

**Expected:** Permission Denied

**Explanation:**

* Pods use **default service account**
* No permissions assigned → access denied

---

## 🆕 13. Create Custom Service Account

```bash
kubectl create sa mysa
kubectl get sa
```

---

## 🔧 14. Attach Service Account to Pod

Update `sapod.yaml`:

```yaml
spec:
  serviceAccountName: mysa
```

Apply again:

```bash
kubectl delete pod sapod -n rbac
kubectl apply -f sapod.yaml
```

---

## 🔗 15. Bind Service Account to Role

Update `QA_rolebinding.yaml`:

```yaml
subjects:
- kind: ServiceAccount
  name: mysa
```

Apply:

```bash
kubectl apply -f QA_rolebinding.yaml
```

**Explanation:**

* Grants permissions to the service account

---

## 🔍 16. Access Kubernetes from Inside Pod

```bash
kubectl exec -it sapod -- sh
kubectl get pods
```

**Explanation:**

* Now pod can access Kubernetes API
* Uses service account token automatically

---

## 🧠 Key Concepts Summary

| Concept        | Description                 |
| -------------- | --------------------------- |
| Authentication | Verified using certificates |
| Authorization  | Controlled via RBAC         |
| Role           | Namespace-level permissions |
| ClusterRole    | Cluster-wide permissions    |
| RoleBinding    | Assigns role to user        |
| ServiceAccount | Identity for pods           |

---

## 🎯 Final Outcome

You learned how to:

* Create Kubernetes users with certificates
* Assign RBAC permissions
* Restrict and grant access across namespaces
* Use service accounts inside pods

---

## 🚀 Pro Tip

To debug permissions quickly:

```bash
kubectl auth can-i <verb> <resource> --as=<user> -n <namespace>
```

---

## 📌 Conclusion

This lab demonstrates the **complete RBAC lifecycle**:

* Identity → Authentication → Authorization → Enforcement

Understanding this flow is critical for securing Kubernetes clusters effectively.
