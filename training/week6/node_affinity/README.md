# Kubernetes Scheduling Walkthrough

This repository demonstrates Kubernetes scheduling concepts using hands-on examples.

## Topics Covered

- NodeSelector
- Node Affinity (required & preferred)
- Operators (In, NotIn, Exists, DoesNotExist, Gt, Lt)
- AND vs OR behavior
- Taints & tolerations interaction
- Scheduling failures (Pending pods)

---

## 1. Setup

Create namespace:

```bash
kubectl create namespace scheduling-demo
```

Check nodes:

```bash
kubectl get nodes
```

---

## 2. Label Nodes

```bash
kubectl label node ip-172-31-15-1 env=prod
kubectl label node ip-172-31-8-107 env=dev
kubectl label node master gpu=true
kubectl label node master disk=ssd
```

Verify:

```bash
kubectl get nodes --show-labels
```

---

## 3. NodeSelector

### Working case

```yaml
nodeSelector:
  env: prod
```

Result:
- Pod scheduled on node with label `env=prod`

### Failure case

```yaml
nodeSelector:
  env: staging
```

Result:
- Pod stays in Pending
- No node matches label

Debug:

```bash
kubectl describe pod <pod-name>
```

---

## 4. Multiple Labels (AND condition)

```yaml
nodeSelector:
  gpu: "true"
  disk: ssd
```

Definition:
- All labels must match (logical AND)

---

## 5. Taints Interaction

Default taint on master:

```bash
node-role.kubernetes.io/control-plane:NoSchedule
```

Remove taint:

```bash
kubectl taint nodes master node-role.kubernetes.io/control-plane:NoSchedule-
```

---

## 6. Node Affinity (Required)

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: env
          operator: In
          values:
          - prod
```

Definition:
- Mandatory condition
- Pod will NOT schedule if not matched

---

## 7. Node Affinity (Preferred)

```yaml
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 10
      preference:
        matchExpressions:
        - key: env
          operator: In
          values:
          - staging
```

Definition:
- Soft rule
- Scheduler tries but does not guarantee

---

## 8. Multiple Preferred Rules (Scoring)

```yaml
preferredDuringSchedulingIgnoredDuringExecution:
- weight: 50
  preference:
    matchExpressions:
    - key: env
      operator: In
      values:
      - prod

- weight: 30
  preference:
    matchExpressions:
    - key: disk
      operator: In
      values:
      - ssd

- weight: 20
  preference:
    matchExpressions:
    - key: gpu
      operator: In
      values:
      - "true"
```

Definition:
- Scheduler selects node with highest total score
- Tie → non-deterministic selection

---

## 9. Operators

### Exists

```yaml
operator: Exists
```

Definition:
- Key must be present

---

### DoesNotExist

```yaml
operator: DoesNotExist
```

Definition:
- Key must NOT be present

---

### In

```yaml
operator: In
values: [prod]
```

Definition:
- Value must match one of the list

---

### NotIn

```yaml
operator: NotIn
values: [dev]
```

Definition:
- Value must NOT match

---

### Gt

```yaml
operator: Gt
values: ["2"]
```

Definition:
- Numeric label greater than value

---

### Lt

```yaml
operator: Lt
values: ["10"]
```

Definition:
- Numeric label less than value

---

## 10. OR vs AND Logic

### OR condition

```yaml
nodeSelectorTerms:
- matchExpressions:
  - key: env
    operator: In
    values: [prod]

- matchExpressions:
  - key: env
    operator: In
    values: [dev]
```

Definition:
- Multiple nodeSelectorTerms = OR

---

### AND condition

```yaml
matchExpressions:
- key: gpu
  operator: Exists

- key: disk
  operator: In
  values: [ssd]
```

Definition:
- Multiple matchExpressions = AND

---

## 11. Failure Debugging

```bash
kubectl describe pod <pod-name>
```

Typical error:

```
0/3 nodes are available:
- didn't match node selector
- had untolerated taint
```

Definition:
- Either label mismatch or taint issue

---

## 12. Key Takeaways

- nodeSelector = simple exact match
- required affinity = strict rule
- preferred affinity = scoring-based soft rule
- matchExpressions inside same block = AND
- nodeSelectorTerms = OR
- scheduler uses scoring + tie-breakers
- Pending pods are important for demos

---

## 13. Interview Tips

- Always show failure case (Pending)
- Always use `kubectl describe`
- Combine taints + affinity for advanced demos
- Explain scoring logic clearly

---

## 14. Folder Structure

```
class-demo/
  ns-basic.yaml
  ns-basic2.yaml
  ns-basic3.yaml
  affinity-required.yaml
  affinity-required2.yaml
  affinity-preferred.yaml
  affinity-preferred-multi.yaml
  affinity-exists.yaml
  affinity-notin.yaml
  affinity-doesnotexist.yaml
  affinity-gt.yaml
  affinity-lt.yaml
  affinity-or.yaml
  affinity-and.yaml
```

---

## 15. Conclusion

This repo demonstrates real-world Kubernetes scheduling behavior including success, failure, and edge cases. Useful for deep understanding and interview preparation.
