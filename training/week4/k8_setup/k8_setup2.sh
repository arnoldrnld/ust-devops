#!/bin/bash
 
set -e
 
echo "===== Kubernetes Node Setup Started ====="
 
############################################
# STEP 1 — Disable Swap
############################################
echo "Disabling swap..."
 
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab
 
free -m
 
 
############################################
# STEP 2 — Load Kernel Modules
############################################
echo "Loading kernel modules..."
 
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF
 
sudo modprobe overlay
sudo modprobe br_netfilter
 
 
############################################
# STEP 3 — Configure Networking Parameters
############################################
echo "Configuring sysctl parameters..."
 
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF
 
sudo sysctl --system
 
 
############################################
# STEP 4 — Install containerd
############################################
echo "Installing containerd..."
 
curl -LO https://github.com/containerd/containerd/releases/download/v1.7.14/containerd-1.7.14-linux-amd64.ta…
 
sudo tar Cxzvf /usr/local containerd-1.7.14-linux-amd64.tar.gz
 
curl -LO https://raw.githubusercontent.com/containerd/containerd/main/containerd.service
 
sudo mkdir -p /usr/local/lib/systemd/system/
 
sudo mv containerd.service /usr/local/lib/systemd/system/
 
 
############################################
# Configure containerd
############################################
 
sudo mkdir -p /etc/containerd
 
containerd config default | sudo tee /etc/containerd/config.toml
 
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/g' /etc/containerd/config.toml
 
 
############################################
# Start containerd
############################################
 
sudo systemctl daemon-reload
sudo systemctl enable --now containerd
 
 
############################################
# STEP 5 — Install runc
############################################
 
echo "Installing runc..."
 
curl -LO https://github.com/opencontainers/runc/releases/download/v1.1.12/runc.amd64
 
sudo install -m 755 runc.amd64 /usr/local/sbin/runc
 
 
############################################
# STEP 6 — Install CNI Plugins
############################################
 
echo "Installing CNI plugins..."
 
curl -LO https://github.com/containernetworking/plugins/releases/download/v1.5.0/cni-plugins-linux-amd64-v1.…
 
sudo mkdir -p /opt/cni/bin
 
sudo tar Cxzvf /opt/cni/bin cni-plugins-linux-amd64-v1.5.0.tgz
 
 
############################################
# STEP 7 — Install Kubernetes Components
############################################
 
echo "Installing Kubernetes packages..."
 
sudo apt-get update
 
sudo apt-get install -y apt-transport-https ca-certificates curl gpg
 
 
############################################
# Add Kubernetes Repository
############################################
 
sudo mkdir -p /etc/apt/keyrings
 
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.34/deb/Release.key \
| sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
 
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] \
https://pkgs.k8s.io/core:/stable:/v1.34/deb/ /" \
| sudo tee /etc/apt/sources.list.d/kubernetes.list
 
 
############################################
# Install kubelet kubeadm kubectl
############################################
 
sudo apt-get update
 
sudo apt-get install -y kubelet kubeadm kubectl
 
sudo apt-mark hold kubelet kubeadm kubectl
 
 
############################################
# Verify installation
############################################
 
kubeadm version
kubectl version --client
 
 
############################################
# STEP 8 — Configure crictl
############################################
 
echo "Configuring crictl..."
 
sudo crictl config runtime-endpoint unix:///var/run/containerd/containerd.sock
 
 
############################################
# Installation Complete
############################################
 
echo "========================================="
echo "Node preparation completed successfully!"
echo "========================================="
 
echo ""
echo "NEXT STEPS:"
echo "Master Node:"
echo "sudo kubeadm init --pod-network-cidr=192.168.0.0/16 --apiserver-advertise-address=<MASTER_IP> --node-name master"
 
echo ""
echo "Worker Nodes:"
echo "Run the kubeadm join command generated from the master node."
