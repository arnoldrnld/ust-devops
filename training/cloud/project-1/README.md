# HabitFlow: AWS 3-Tier Infrastructure and Deployment Guide

This document is infrastructure-first and follows this rollout order:
1. Build AWS networking and shared services in detail.
2. Launch dummy EC2 instances and deploy manually.
3. Validate end-to-end behavior.
4. Create golden AMIs.
5. Move to launch templates + Auto Scaling Groups (ASG).

Target architecture:
- Route 53 + ACM + Internet-facing ALB for user entry.
- Public frontend EC2 tier (React build served by NGINX).
- Internal ALB for service routing.
- Private backend EC2 tier (FastAPI microservices).
- Amazon RDS PostgreSQL (Multi-AZ).
- Optional separate DB VPC with VPC peering.

## 1. Application Components in This Repo

- `frontend/`: React app.
- `auth-service/`: FastAPI auth service (port `8001`).
- `habit-service/`: FastAPI habit service (port `8002`).
- `journal-service/`: FastAPI journal service (port `8003`).
- `nginx/habitflow.conf`: NGINX frontend + reverse proxy to internal ALB.
- `sql/schema.sql`: PostgreSQL schema.
- `systemd/*.service`: service units for boot persistence.

Health endpoints:
- Auth: `GET /health` and `GET /auth/health`
- Habit: `GET /health`
- Journal: `GET /health`

## 2. AWS Services Used and Why

- Amazon VPC: isolated network boundaries for tiers.
- Subnets (public/private/data): tier isolation per AZ.
- Route tables + associations: define egress/ingress path per subnet.
- Internet Gateway (IGW): internet path for public workloads.
- NAT Gateway: outbound internet for private instances.
- Security Groups: stateful least-privilege filtering.
- Network ACLs (optional hardening): stateless subnet filtering.
- Application Load Balancer (ALB): L7 routing and health checks.
- EC2: frontend and backend compute.
- Launch Template: immutable EC2 configuration for scaling.
- Auto Scaling Group: high availability and self-healing.
- Amazon RDS for PostgreSQL (Multi-AZ): managed relational database.
- AWS Certificate Manager (ACM): TLS certificate for HTTPS.
- Amazon Route 53: DNS alias to external ALB.
- IAM Roles/Instance Profiles: secure AWS API access from EC2.
- Amazon CloudWatch + SNS: logs, metrics, and alerting.
- Systems Manager (optional but recommended): shell access without bastion.

## 3. Final Network Plan (Detailed)

Use this CIDR plan:

### 3.1 App VPC
- VPC CIDR: `10.0.0.0/16`
- DNS hostnames: `enabled`
- DNS resolution: `enabled`

Subnets:
- Public Subnet AZ1a: `10.0.1.0/24`
- Private App Subnet AZ1a: `10.0.2.0/24`
- Public Subnet AZ1b: `10.0.3.0/24`
- Private App Subnet AZ1b: `10.0.4.0/24`

### 3.2 DB VPC (Optional Pattern)
If a separate database VPC is required:
- DB VPC CIDR: `172.31.0.0/16`
- DB Subnet AZ-a: `172.31.1.0/24`
- DB Subnet AZ-b: `172.31.2.0/24` (create this second subnet for Multi-AZ)
- RDS is private only.
- VPC peering between App VPC and DB VPC.

Note: Production best practice is usually to place RDS in private DB subnets in the same VPC as app tier. Keep the peered VPC model only if required by your architecture standard.

## 4. Build Core Networking (Step-by-Step)

## 4.1 Create App VPC
1. Create VPC `habitflow-app-vpc` with CIDR `10.0.0.0/16`.
2. Enable DNS hostnames and DNS resolution.

## 4.2 Create App Subnets
Create all four subnets and pin each to correct AZ:
1. `public-az1a` -> `10.0.1.0/24`
2. `private-app-az1a` -> `10.0.2.0/24`
3. `public-az1b` -> `10.0.3.0/24`
4. `private-app-az1b` -> `10.0.4.0/24`

Set `auto-assign public IPv4`:
- Enabled only for public subnets.
- Disabled for private app subnets.

## 4.3 Create and Attach IGW
1. Create Internet Gateway `habitflow-igw`.
2. Attach it to `habitflow-app-vpc`.

## 4.4 Create NAT Gateway
1. Allocate one Elastic IP.
2. Create NAT Gateway in `public-az1a` (`10.0.1.0/24`).
3. Wait until NAT state is `Available`.

## 4.5 Create Route Tables and Associations
Create two route tables:

1. `rt-public`
- Route: `10.0.0.0/16` -> local (automatic)
- Route: `0.0.0.0/0` -> `habitflow-igw`

Associate `rt-public` with:
- `public-az1a` (`10.0.1.0/24`)
- `public-az1b` (`10.0.3.0/24`)

2. `rt-private-app`
- Route: `10.0.0.0/16` -> local
- Route: `0.0.0.0/0` -> NAT Gateway

Associate `rt-private-app` with:
- `private-app-az1a` (`10.0.2.0/24`)
- `private-app-az1b` (`10.0.4.0/24`)

## 4.6 Create DB VPC and Peering (Optional)
1. Create DB VPC `habitflow-db-vpc` CIDR `172.31.0.0/16`.
2. Create two private DB subnets (different AZs).
3. Create RDS subnet group using both DB subnets.
4. Create VPC peering connection between app and DB VPC.
5. Update route tables:
- In app private route table: `172.31.0.0/16` -> peering connection.
- In DB route table: `10.0.0.0/16` -> peering connection.
6. Ensure SG/NACL rules allow `5432` from backend tier to RDS.

## 5. Security Controls

## 5.1 Security Groups
Create these SGs:

1. `sg-external-alb`
- Inbound: `80` from `0.0.0.0/0`
- Inbound: `443` from `0.0.0.0/0`
- Outbound: all

2. `sg-frontend-ec2`
- Inbound: `80` from `sg-external-alb`
- Inbound: `22` from admin CIDR or bastion SG only
- Outbound: all

3. `sg-internal-alb`
- Inbound: `80` from `sg-frontend-ec2`
- Outbound: to backend SG on `8001-8003`

4. `sg-backend-ec2`
- Inbound: `8001-8003` from `sg-internal-alb`
- Inbound: `22` from bastion/admin CIDR only
- Outbound: `5432` to `sg-rds`
- Outbound: `443` to internet via NAT (patching/package installs)

5. `sg-rds`
- Inbound: `5432` from `sg-backend-ec2`
- No public inbound

6. `sg-bastion` (if bastion is used)
- Inbound: `22` from approved administrator CIDR only
- Outbound: `22` to frontend/backend instance SGs

## 5.2 NACL Baseline (Optional)
Use SGs as primary control. Add NACLs for additional guardrails:
- Public subnet NACL: allow `80/443`, `22` (restricted), and ephemeral return.
- Private app subnet NACL: allow `8001-8003` from internal ALB subnet CIDRs and ephemeral return.
- DB subnet NACL: allow `5432` from private app subnet CIDRs and ephemeral return.

## 6. Load Balancers and DNS/TLS

## 6.1 Internal ALB (Service Router)
- Scheme: `internal`
- Subnets: private app subnets (`10.0.2.0/24`, `10.0.4.0/24`)
- SG: `sg-internal-alb`
- Listener: HTTP `80`

Target groups:
- `tg-auth` -> HTTP `8001`, health check path `/health`
- `tg-habit` -> HTTP `8002`, health check path `/health`
- `tg-journal` -> HTTP `8003`, health check path `/health`

Listener rules:
- `/auth/*` -> `tg-auth`
- `/habits/*` -> `tg-habit`
- `/journal/*` -> `tg-journal`

## 6.2 External ALB (User Entry)
- Scheme: `internet-facing`
- Subnets: public subnets (`10.0.1.0/24`, `10.0.3.0/24`)
- SG: `sg-external-alb`
- Listeners:
- HTTP `80` redirect to HTTPS `443`
- HTTPS `443` with ACM certificate

Target group:
- `tg-frontend` -> HTTP `80`, health check `/`

## 6.3 ACM and Route 53
1. Request ACM cert in same region as external ALB:
- Domain: `lavenbloom.xyz` and `*.lavenbloom.xyz` (if needed)
- Validation: DNS in Route 53
2. Attach cert to external ALB HTTPS listener.
3. Route 53 record:
- Type: `A` (Alias)
- Name: `lavenbloom.xyz` (or subdomain)
- Target: external ALB DNS name

## 7. RDS PostgreSQL Setup

1. Engine: PostgreSQL (latest supported stable version per platform standards).
2. Deployment: Multi-AZ DB instance.
3. Networking:
- Private subnets only.
- Public access: `No`.
- SG: `sg-rds`.
4. Database config:
- DB name: `habitflow` (example)
- Port: `5432`
- Storage autoscaling enabled.
- Automated backups enabled.
5. Save endpoint and credentials in a secure location (use Secrets Manager for production).

Initialize schema:
```bash
psql "host=<RDS-ENDPOINT> port=5432 dbname=<DB_NAME> user=<DB_USER> password=<DB_PASSWORD> sslmode=require" -f sql/schema.sql
```

## 8. Phase 1: Manual Deployment on Dummy EC2 (Before AMIs)

This is the mandatory first phase.

## 8.1 Launch Dummy Instances
Launch at least:
1. One frontend EC2 in public subnet (`10.0.1.0/24`) with `sg-frontend-ec2`.
2. One backend EC2 in private subnet (`10.0.2.0/24`) with `sg-backend-ec2`.
3. Optional bastion in public subnet with `sg-bastion`.

Instance profile IAM role permissions (minimum):
- SSM core (if using Session Manager)
- CloudWatch Agent (optional)

## 8.2 Clone and Install on Frontend EC2
```bash
sudo apt update -y
sudo apt install -y git nginx nodejs npm
cd /home/ubuntu
git clone <YOUR_REPO_URL> habitflow
cd habitflow/frontend
cp .env.example .env
npm install
npm run build
sudo cp /home/ubuntu/habitflow/nginx/habitflow.conf /etc/nginx/sites-available/habitflow.conf
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/habitflow.conf /etc/nginx/sites-enabled/habitflow.conf
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx
```

Important edit before restarting nginx:
- In `nginx/habitflow.conf`, replace `http://<INTERNAL-ALB-DNS>` with actual internal ALB DNS.

## 8.3 Clone and Install on Backend EC2
```bash
sudo apt update -y
sudo apt install -y git python3 python3-venv python3-pip
cd /home/ubuntu
git clone <YOUR_REPO_URL> habitflow
cd /home/ubuntu/habitflow
```

For each service:
```bash
cd /home/ubuntu/habitflow/auth-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

cd /home/ubuntu/habitflow/habit-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

cd /home/ubuntu/habitflow/journal-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Update all `.env` files with:
- `RDS_ENDPOINT`
- `DB_PORT=5432`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `JWT_SECRET` (same secret in all services)

## 8.4 Install and Start systemd Services
```bash
sudo cp /home/ubuntu/habitflow/systemd/auth.service /etc/systemd/system/
sudo cp /home/ubuntu/habitflow/systemd/habit.service /etc/systemd/system/
sudo cp /home/ubuntu/habitflow/systemd/journal.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable auth.service habit.service journal.service
sudo systemctl restart auth.service habit.service journal.service
```

## 8.5 Register Dummy Instances in Target Groups
- Add frontend dummy instance to `tg-frontend`.
- Add backend dummy instance to `tg-auth`, `tg-habit`, `tg-journal`.

## 8.6 Validation Checklist (Must Pass Before AMI)
From backend EC2:
```bash
curl -s http://127.0.0.1:8001/health
curl -s http://127.0.0.1:8002/health
curl -s http://127.0.0.1:8003/health
```

From frontend EC2:
```bash
curl -I http://127.0.0.1/
```

From an internet client:
- Open `https://<domain>`.
- Register/login.
- Create/read/update/delete habits.
- Create/read/update/delete journal entries.

Reboot test:
```bash
sudo reboot
```
After reboot verify:
```bash
systemctl is-active nginx auth.service habit.service journal.service
```

Only proceed to AMI after this passes.

## 9. Phase 2: Create Golden AMIs

## 9.1 Frontend AMI
1. Stop unnecessary processes, clear temp files/log noise.
2. Ensure nginx config is correct and enabled.
3. Ensure app build exists in `/home/ubuntu/habitflow/frontend/build`.
4. Create image: `habitflow-frontend-ami-v1`.

## 9.2 Backend AMI
1. Ensure service venvs and `.env` placeholders/strategy are finalized.
2. Ensure systemd services are enabled and healthy.
3. Create image: `habitflow-backend-ami-v1`.

Tip: Use parameterized runtime config (SSM/Secrets Manager + bootstrapping) if DB endpoint/secret can change.

## 10. Phase 3: Launch Templates and Auto Scaling Groups

## 10.1 Launch Templates
Create two templates:

1. `lt-habitflow-frontend`
- AMI: `habitflow-frontend-ami-v1`
- Instance type: e.g., `t3.small`
- SG: `sg-frontend-ec2`
- IAM instance profile
- User data: optional lightweight checks/start commands

2. `lt-habitflow-backend`
- AMI: `habitflow-backend-ami-v1`
- Instance type: e.g., `t3.small`
- SG: `sg-backend-ec2`
- IAM instance profile
- User data: optional runtime config fetch + service restart

## 10.2 Auto Scaling Groups
Create ASGs across two AZs:

1. `asg-habitflow-frontend`
- Subnets: `10.0.1.0/24`, `10.0.3.0/24`
- Attach to `tg-frontend`
- Min `2`, Desired `2`, Max `4`
- Health checks: ELB + EC2

2. `asg-habitflow-backend-auth` (or one ASG per service pattern)
- Subnets: `10.0.2.0/24`, `10.0.4.0/24`
- Attach to matching backend target groups
- Min `2`, Desired `2`, Max `6`
- Health checks: ELB + EC2

If services are separated operationally, create three backend ASGs:
- `asg-auth-service`
- `asg-habit-service`
- `asg-journal-service`

## 10.3 Scale and Recovery Tests
1. Terminate one instance manually and verify ASG replacement.
2. Check target group health returns to healthy.
3. Run API smoke tests again.

## 11. App-Specific Configuration Map

## 11.1 Frontend
- File: `frontend/src/config.js`
- Set:
```javascript
const API_BASE_URL = "http://<INTERNAL-ALB-DNS>";
```

## 11.2 NGINX
- File: `nginx/habitflow.conf`
- Replace all `<INTERNAL-ALB-DNS>` with real internal ALB DNS.

## 11.3 Backend Env Files
- `auth-service/.env`
- `habit-service/.env`
- `journal-service/.env`

Values:
```env
RDS_ENDPOINT=<RDS-ENDPOINT>
DB_PORT=5432
DB_NAME=<DB_NAME>
DB_USER=<DB_USER>
DB_PASSWORD=<DB_PASSWORD>
JWT_SECRET=<SAME_SECRET_FOR_ALL_SERVICES>
JWT_ALGORITHM=HS256
JWT_EXP_MINUTES=1440
```

## 12. Observability, Alerts, and Ops Baseline

1. Send ALB access logs to S3.
2. Send app/system logs to CloudWatch Logs.
3. Create CloudWatch alarms:
- ALB `5XX` count
- Target group unhealthy host count
- EC2 CPU high
- RDS CPU/storage/connections
4. Send alarm notifications through SNS email topic.

## 13. Common Failure Points

- `502/504` from ALB: target group unhealthy, wrong port/path, service down.
- Frontend loads but API fails: NGINX proxy target not set to internal ALB DNS.
- DB connection failure: SG or peering routes missing, wrong RDS endpoint/credentials.
- Auth issues: mismatched `JWT_SECRET` across services.
- Instances in ASG not serving: AMI created before successful reboot validation.

## 14. Recommended Next Step After This Manual Pattern

After this manual, AMI-based flow is stable, move to Infrastructure as Code (Terraform/CloudFormation) so VPC, ALB, RDS, ASG, SG, and alarms are reproducible and versioned.
