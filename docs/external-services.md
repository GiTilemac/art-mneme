# External Services

Every online service that ArtMneme uses, with its account, resources, secrets and costs.
Secret values are never written here, only their names and where they are kept.
Step-by-step commands stay in `README.md`; this file links to them.

When a new service is added (for example Grafana Cloud for observability), add a section in the same form.

---

## AWS

| Field | Value |
|---|---|
| Purpose | Hosting: the server, the photos, the app images and the backups. |
| Decided | 2026-10-26 by the project owner (`docs/architecture.md` > Deployment Shape, Photo Storage). |
| Account | A separate AWS account used only for ArtMneme. AWS CLI profile: `artmneme-deploy` (IAM user `artmneme-deploy`). Region: `eu-central-1`. |
| Created resources | CloudFormation stack `artmneme` (prod), defined in `deploy/cloudformation.yaml`: EC2 server (t3.micro) with an Elastic IP, a security group (ports 80 and 443 only), the private S3 photo bucket, the ECR repository `artmneme` (images tagged `YYYYMMDD-HHMMSS-shortsha`, the newest also `dev`; the last 5 kept), the server's IAM role, and a daily disk snapshot (7 kept). |
| Secrets | `/artmneme/postgres-password` in SSM Parameter Store (SecureString). The server reaches S3, ECR and SSM through its IAM role; no access keys are stored on it. |
| Cost and limits | About $13 a month (server, public IP address, disk, snapshots), paid from the account's $100 starting credit. Budget alarm: "My Zero-Spend Budget". |
| Create or update | `README.md` > Deploy to AWS (`make deploy-stack` once; new versions through CI/CD: CI builds the image, "Deploy to prod" starts it). |
| Access to the server | `aws ssm start-session --target <InstanceId>` (Session Manager, no SSH). |
| Remove | Delete the stack `artmneme`. The photo bucket is kept on purpose and must be emptied and deleted by hand. The disk snapshots are deleted with their policy; delete any left ones by hand. |
| GitHub Actions access | Stack `artmneme-github-production` (`deploy/github-oidc.yaml`): the GitHub OIDC provider and the role that GitHub Actions uses: the build stage of CI pushes images with it, and "Deploy to prod" starts them. Only workflow runs on `main` of `GiTilemac/art-mneme` may use it; it may only push, tag and list images in the ECR repository, read the app stack and run commands on that stack's server. |

### Third parties used by the AWS setup (no account)

| Service | Purpose |
|---|---|
| Let's Encrypt | Free HTTPS certificate, requested by Caddy on the server. |
| sslip.io | Turns the server's IP address into a hostname (`<address>.sslip.io`), so a certificate is possible without a domain. |

---

## GitHub

| Field | Value |
|---|---|
| Purpose | The repository `GiTilemac/art-mneme`, its issues, and CI/CD with GitHub Actions (`.github/workflows/ci-cd.yml` for tests, `.github/workflows/deploy-prod.yml` for the manual deploy to prod). Lovable also pushes to this repository. |
| Account | The project owner's GitHub account. |
| Secrets | None. The repository variable `AWS_DEPLOY_ROLE_ARN_PROD` holds the role's address (not secret); AWS access is through OIDC. |
| Cost and limits | Free plan. The repository is private: about 2,000 Actions minutes a month are included, and environments are not available. |
| Set up | `README.md` > CI/CD. |

---

## Grafana Cloud

| Field | Value |
|---|---|
| Purpose | The observability stack for dev and prod: metrics, traces and logs from the backend, and the dashboard "ArtMneme application metrics". Separate from the application stack. |
| Decided | 2026-10-26 by the project owner (instead of an own observability server on AWS). |
| Account | The project owner's Grafana Cloud account, free tier. Grafana is opened at the stack's `grafana.net` address with that account. |
| Secrets | For the dashboard and alert upload and the on-call engineer: the Grafana address and a service-account token (role Admin), in SSM as `/artmneme/grafana-url` and `/artmneme/grafana-token`. For sending data: the OTLP endpoint and the token header: in SSM as `/artmneme/otel-exporter-otlp-endpoint` and `/artmneme/otel-exporter-otlp-headers` (prod), and as the environment variables `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS` on the developer's computer (dev). Never in the repository. |
| Cost and limits | Free tier: limited metrics series, logs and traces per month, short retention. ArtMneme's volume is far below it. |
| Alerting | The rule "Artwork creations are failing" goes to the default contact point: the account's email address. |
| Set up | `README.md` > Telemetry > Grafana Cloud, and > Alert and on-call engineer. |

---

## Claude Code (on-call engineer)

| Field | Value |
|---|---|
| Purpose | The headless agent that `make on-call` starts for each new alert (`docs/team/on-call-engineer.md`). |
| Account | The developer's own Claude Code login on their computer. No API key is stored. |
| Cost and limits | Within the developer's Claude Code plan; each alert starts one session. |
