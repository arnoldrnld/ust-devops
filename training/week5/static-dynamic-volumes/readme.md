# Kubernetes Storage Concepts: Detailed Guide from Basics to NFS

This document is a concept-first deep dive into Kubernetes storage. It starts with fundamentals and builds toward real NFS implementation patterns (static and dynamic), including corrected and production-aware setup steps.

## 1. Why Storage Matters in Kubernetes

Kubernetes is designed for resilient, replaceable workloads. Pods can be restarted, rescheduled, or replaced at any time due to:

- node failure
- deployment rollout
- autoscaling
- health-check failures

By default, container filesystems are not durable across Pod replacement. That means application data can disappear unless externalized to a volume.

Storage is essential for:

- databases (MySQL, PostgreSQL, MongoDB)
- file uploads (profile images, documents)
- ML/data processing checkpoints
- shared content across replicas
- audit/compliance retention

Core design question:

- Should data survive Pod deletion?
  - If no, ephemeral storage is enough.
  - If yes, persistent storage is required.

## 2. Ephemeral vs Persistent Storage

## 2.1 Ephemeral Storage

What it is:

- Storage whose lifecycle is coupled to a Pod.

Common type:

- `emptyDir`

How `emptyDir` behaves:

- Created when Pod is scheduled on a node.
- Shared by all containers in that Pod.
- Survives container restart in same Pod.
- Removed permanently when Pod is deleted.

Use cases:

- temporary cache
- scratch space for data transformation
- inter-container data sharing in a single Pod

Benefits:

- simple
- fast to use
- no PV/PVC setup needed

Limitations:

- non-durable
- not shareable across Pods/nodes

## 2.2 Persistent Storage

What it is:

- Storage independent of Pod lifecycle.

Core objects:

- `PersistentVolume` (PV): storage resource in cluster
- `PersistentVolumeClaim` (PVC): request for storage by workload

Behavior:

- Pod mounts PVC.
- Pod can be recreated and still access same data.
- Data durability depends on backend and reclaim policy.

Use cases:

- any stateful workload
- long-lived content
- workload migration with retained data

## 3. Kubernetes Storage Building Blocks

## 3.1 PersistentVolume (PV)

PV defines:

- capacity (`1Gi`, `100Gi`, etc.)
- access mode (`RWO`, `RWX`, `ROX`)
- backend type (`hostPath`, `nfs`, cloud disk)
- reclaim policy (`Retain`, `Delete`)
- optional `storageClassName`

PV lifecycle states:

- `Available`: free for binding
- `Bound`: connected to PVC
- `Released`: claim deleted but volume not yet reusable
- `Failed`: provisioning/recycle failure

## 3.2 PersistentVolumeClaim (PVC)

PVC requests:

- storage size
- access mode
- storage class

PVC lifecycle states:

- `Pending`: waiting for matching PV or provisioner
- `Bound`: successfully attached to PV

PVC is what applications should reference, not PV directly.

## 3.3 StorageClass

StorageClass defines dynamic provisioning behavior:

- provisioner name
- reclaim policy
- volume binding mode
- custom parameters

In dynamic setups, PVC + StorageClass trigger automatic PV creation.

## 4. Static vs Dynamic Provisioning

## 4.1 Static Provisioning

Flow:

1. Admin pre-creates PV.
2. Application creates PVC.
3. PVC binds to matching PV.

Best when:

- strict/manual control needed
- migration with pre-existing storage
- small environments/labs

Tradeoffs:

- operational overhead
- scaling friction

## 4.2 Dynamic Provisioning

Flow:

1. Admin creates StorageClass + provisioner.
2. App creates PVC with `storageClassName`.
3. Provisioner auto-creates backend storage and PV.

Best when:

- many teams/namespaces
- repeatable self-service workflows
- cloud-native operations

Tradeoffs:

- requires healthy provisioner
- naming/config mismatch causes `Pending` claims

## 5. Access Modes and Their Impact

- `ReadWriteOnce` (RWO): one node can mount read-write.
- `ReadOnlyMany` (ROX): many nodes can mount read-only.
- `ReadWriteMany` (RWX): many nodes can mount read-write.

Important:

- Access mode support is backend-dependent.
- NFS is a common and practical choice for RWX.

## 6. Reclaim Policy (Often Missed)

Reclaim policy controls what happens to storage after PVC deletion.

- `Delete`:
  
  - underlying storage is removed automatically.
  - best for temporary environments.
- `Retain`:
  
  - storage and data are preserved after claim deletion.
  - best for critical data and manual recovery workflows.

Operational implication:

- choosing wrong policy can either leak storage or delete important data.

## 7. What is NFS?

NFS (Network File System) lets systems mount a remote directory over network as if it were local disk.

Why it is valuable in Kubernetes:

- supports shared writable storage (`RWX`)
- allows multiple Pods on different nodes to write/read same directory
- simpler shared-files model for web/content workloads

Typical workloads using NFS:

- CMS media directories
- shared config/content artifacts
- multi-replica apps requiring common filesystem

## 8. NFS in Kubernetes: Static vs Dynamic

## 8.1 Static NFS Pattern

You create:

- NFS-backed PV (`nfs.server`, `nfs.path`)
- PVC binding that PV
- Pod/Deployment mounting PVC

Characteristics:

- high control
- manual volume management
- good for fixed, known shares

## 8.2 Dynamic NFS Pattern (with nfs-subdir-external-provisioner)

You create:

- provisioner deployment via Helm
- StorageClass using that provisioner
- PVC with that StorageClass

Provisioner does:

- creates subdirectory per PVC on NFS export
- auto-creates PV objects
- binds claims automatically

Characteristics:

- scalable and automated
- ideal for teams with frequent claim creation

## 9. Corrected NFS Setup (Detailed)

## 9.1 Step 1: Prepare NFS Server (Ubuntu)

Install packages:

```bash
sudo apt update
sudo apt install -y nfs-kernel-server nfs-common
```

Create export directory:

```bash
sudo mkdir -p /nfs-storage
sudo chmod 0777 /nfs-storage
```

Configure exports:

```bash
sudo vi /etc/exports
```

Add:

```bash
/nfs-storage *(rw,sync,no_subtree_check,no_root_squash,insecure)
```

Apply and start service:

```bash
sudo exportfs -rav
sudo systemctl restart nfs-kernel-server
sudo systemctl enable nfs-kernel-server
sudo systemctl status nfs-kernel-server
```

Validate export:

```bash
showmount -e localhost
```

Why these options:

- `rw`: read/write from clients
- `sync`: safer writes (commit before reply)
- `no_subtree_check`: avoids subtree verification overhead
- `no_root_squash`: container root writes without UID remap
- `insecure`: allows non-privileged source ports (sometimes needed)

Production hardening suggestions:

- replace `*` with node CIDR or exact node IPs
- avoid broad `0777`; use controlled UID/GID and ACLs
- restrict network path using security groups/firewalls

## 9.2 Step 2: Prepare Worker Nodes

Install client packages on every node that may mount NFS volumes:

```bash
sudo apt update
sudo apt install -y nfs-common
```

Optional manual mount test:

```bash
sudo mkdir -p /nfs/data
sudo mount -t nfs <NFS_SERVER_IP>:/nfs-storage /nfs/data
df -h | grep /nfs/data
sudo umount /nfs/data
```

If manual mount fails, Kubernetes NFS mounts will also fail.

## 9.3 Step 3: Install Dynamic NFS Provisioner

Add and refresh Helm repo:

```bash
helm repo add nfs-subdir-external-provisioner https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner
helm repo update
```

Install provisioner:

```bash
helm install dev-nfs-provisioner nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
  --set nfs.server=<NFS_SERVER_IP> \
  --set nfs.path=/nfs-storage \
  --set storageClass.create=false \
  --namespace nfs-storage \
  --create-namespace
```

Validate:

```bash
kubectl get pods -n nfs-storage
kubectl get deploy -n nfs-storage
```

Uninstall if needed:

```bash
helm uninstall dev-nfs-provisioner -n nfs-storage
```

## 9.4 Step 4: Create StorageClass, PVC, and Workload

StorageClass must match provisioner name exactly. In this setup, it is typically:

- `cluster.local/dev-nfs-provisioner-nfs-subdir-external-provisioner`

Then:

1. create StorageClass
2. create PVC with `ReadWriteMany`
3. mount PVC in Deployment/Pod
4. write and verify file content

## 9.5 Step 5: Validate End-to-End

Run:

```bash
kubectl get sc
kubectl get pvc
kubectl get pv
kubectl describe pvc <pvc-name>
kubectl get pods
```

Check NFS server directory:

- a subdirectory for the PVC should appear (dynamic case)

Inside app pod:

```bash
kubectl exec -it <pod-name> -- sh
ls -la /data
tail -n 20 /data/file.txt
```

## 10. Troubleshooting Playbook

## 10.1 PVC `Pending`

Checks:

- `kubectl describe pvc <name>`
- storage class exists and names match
- provisioner pod is running
- provisioner name in StorageClass is exact
- requested size/access mode is supported

Common fix:

- correct `storageClassName`
- restart/fix provisioner
- fix permissions on `/nfs-storage`

## 10.2 Pod `ContainerCreating`

Checks:

- `kubectl describe pod <pod>` events
- node can reach NFS server IP
- export path exists and exported
- security group/firewall rules allow NFS traffic

Common fix:

- install `nfs-common` on node
- correct export path/IP
- open NFS ports in network policy/firewall

## 10.3 Permission Denied in Mounted Path

Checks:

- NFS export options
- ownership and mode on export directory
- app container UID/GID behavior

Common fix:

- validate `no_root_squash` (lab)
- align directory ownership with app user

## 10.4 Data Unexpectedly Deleted

Checks:

- StorageClass reclaim policy
- PVC/PV deletion order

Common fix:

- use `Retain` where data preservation is mandatory

## 11. Conceptual Architecture (Mental Model)

Dynamic NFS request path:

1. App creates PVC.
2. Kubernetes sees `storageClassName`.
3. External provisioner receives request.
4. Provisioner creates subdirectory on NFS export.
5. Provisioner creates PV bound to PVC.
6. Pod mounts PVC and reads/writes data.

This model helps debug where failures occur: claim, class, provisioner, NFS server, or Pod mount.

## 12. Best Practices Checklist

- Use PVCs in workloads, not hardcoded host paths.
- Use dynamic provisioning for scale.
- Use `RWX` only where genuinely needed.
- Set reclaim policy intentionally.
- Restrict NFS exports to node CIDRs, not `*`, outside labs.
- Monitor provisioner and PV/PVC events.
- Keep backup strategy independent of Kubernetes objects.

## 13. Quick Decision Guide

Use `emptyDir` when:

- data is temporary
- performance and simplicity matter

Use static PV/PVC when:

- storage is pre-created
- you need strict admin control

Use dynamic provisioning when:

- many claims are created frequently
- teams need self-service storage

Use NFS when:

- workloads need shared writable files across nodes (`RWX`)

## 14. Final Takeaway

Kubernetes storage is about separating compute lifecycle from data lifecycle.

- Ephemeral storage supports temporary workloads.
- PV/PVC supports durable workloads.
- Static provisioning gives control.
- Dynamic provisioning gives speed and scale.
- NFS is a strong fit for shared writable (`RWX`) workloads when set up with secure exports and a healthy provisioner.


