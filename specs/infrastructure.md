# Component Spec: Infrastructure and Security

**Version:** 0.1 · **Date:** November 27, 2026 · **Owner:** Suriyadeepan Narayanasamy · **Builder role:** DevOps Engineer
**Status:** Hosting choice, Terraform and the security split are APPROVED (D-083, D-086, D-087). The exact resources, permissions and owner steps below are PROPOSED. **Nothing is created in AWS until the owner approves this spec and reviews the first `terraform plan`.**
**Blocker:** Q-001, the organizers' approval to use a personal AWS account.

## 1. Objective and scope
Host the demo app online for judges, train models through a SageMaker Pipeline, and keep it secure, cheap and easy to tear down.

```
Judge's browser ──password──▶ Lightsail container (Streamlit app + fallback model)
                                   │  narrow access key: invoke the endpoint, invoke Haiku
                                   ├──▶ SageMaker serverless endpoint (registered model)
                                   └──▶ Bedrock, Claude Haiku 4.5 (outreach drafts)
SageMaker Pipeline (run on demand) ──▶ S3 (data, notes, models) ──▶ Model registry
Owner's laptop: Terraform, MLflow UI, notebooks
```

## 2. Inputs and dependencies
Approved: D-082 (judge-facing app), D-083 (hosting), D-084 (pipeline, MLflow), D-086 (Terraform), D-087 (security split). Depends on: Q-001 (account approval), Q-003 (Bedrock credits).

## 3. Owner-only checklist
The agent never does these steps. Do them in this order. Root is used only for steps 1 and 2.

| # | Step | Signed in as | How to check |
|---|---|---|---|
| 1 | Root: MFA on, no root access keys | Root | Done (owner, Nov 27). IAM → Security credentials shows MFA assigned and no access keys |
| 2 | Account → "IAM user and role access to Billing information" → Activate | Root | Admin user can open Billing |
| 3 | Turn on IAM Identity Center in us-east-1; create your user; give it the AdministratorAccess permission set; register MFA; sign out of root | Root, then your admin user | Sign in through the Identity Center portal works with MFA |
| 4 | Budget alert at $50 | Admin | Done (owner, Nov 27). Billing → Budgets lists it |
| 5 | Cost Anomaly Detection: a monitor for AWS services with an email alert | Admin | Billing → Cost Anomaly Detection lists the monitor |
| 6 | Bedrock → Model catalog: open Claude Haiku 4.5 in us-east-1 and submit Anthropic's first-use form if asked | Admin | The Bedrock playground answers a test prompt |
| 7 | Create the Terraform state bucket `tfstate-lpp-<account-id>` (deliberately not `lpp-*`, so the deployer role cannot touch it): block all public access, versioning on, default encryption on | Admin | S3 → bucket → Properties shows versioning enabled |
| 8 | Create the permission boundary policy `lpp-boundary` and the deployer role `lpp-deployer` from section 4 (JSON files in `infra/bootstrap/`) | Admin | IAM → Roles shows `lpp-deployer` with `lpp-boundary` attached |
| 9 | Add an AWS CLI profile `lpp` that assumes `lpp-deployer`; Terraform always runs with this profile | Admin, on your laptop | `aws sts get-caller-identity --profile lpp` shows the `lpp-deployer` role |
| 10 | After the first `terraform apply`: create one access key for the IAM user `lpp-app-runtime` and put it only in your local `.env` file (`.env` is git-ignored). Set the app password there too | Admin | `git check-ignore .env` prints `.env`; `make deploy-app` starts the container |
| 11 | After judging: delete that access key, then run the teardown (section 8) | Admin | No `lpp-` resources left except the data and state buckets |

## 4. The deployer role (limits for the infrastructure agent's work)
Terraform is written by the agent and run by the owner with the `lpp` profile, so even a wrong plan can only touch what this role allows.

| Allowed | Denied |
|---|---|
| S3 on buckets named `lpp-*`; SageMaker models, endpoint configs, endpoints, pipelines, model package groups and processing/training jobs named `lpp-*`; Lightsail container services named `lpp-*`; ECR repositories named `lpp-*`; CloudWatch Logs `/aws/sagemaker/*` and `/lpp/*`; Bedrock model list and read | Anything outside us-east-1 (except Bedrock's US inference profile regions); `iam:CreateAccessKey`, `iam:CreateLoginProfile` and `iam:UpdateLoginProfile` on any user (keys are made only by the owner); the state bucket `tfstate-lpp-*` (the owner's profile runs the backend); IAM users or roles not named `lpp-*`; creating any role or user without the `lpp-boundary` boundary; changing `lpp-boundary` or `lpp-deployer` themselves; Organizations, account, billing, IAM Identity Center; deleting the state bucket |

`lpp-boundary` caps every role or user Terraform creates at: read and write on `lpp-*` buckets, SageMaker invoke and job actions on `lpp-*` resources, Bedrock invoke on Claude Haiku 4.5 only, and logs. So nothing Terraform creates can ever have more power than that.

## 5. Resources Terraform creates (all tagged `Project=late-payment-prediction`)
| Resource | Settings |
|---|---|
| S3 `lpp-data-<account-id>` | Public access blocked, encryption on, versioning on, `prevent_destroy`. Prefixes: `raw/` (restricted), `generated/notes_raw/` (restricted, contains fake personal details), `generated/notes_masked/`, `models/`, `pipeline-runs/` |
| IAM role `lpp-sagemaker-exec` | Used by pipeline jobs and the endpoint: read `raw/` and `generated/`, write `models/` and `pipeline-runs/`, logs, Bedrock invoke on Haiku (note reader step) |
| SageMaker model package groups `lpp-stage1`, `lpp-stage2` | Registry; a model is used only when its status is Approved |
| SageMaker serverless endpoint `lpp-stage1` (and `lpp-stage2`) | Memory 2048 MB, max concurrency 2. The approved model package ARN is a Terraform variable |
| IAM user `lpp-app-runtime` | No console access. May only invoke the two `lpp-` endpoints and Claude Haiku 4.5. Its access key is created by the owner (step 10), so it never appears in Terraform state |
| Lightsail container service `lpp-app` | Power Small, scale 1, HTTPS only. The deployment, with its environment variables, is pushed by `make deploy-app` from the owner's local `.env`, so secrets stay out of Terraform state and git. Lightsail shows container environment variables in plain text to anyone with Lightsail read access in the account; acceptable here because only the owner has console access and the key can do nothing but call the two endpoints and Haiku. It is deleted after judging (step 11) |

The SageMaker Pipeline definition is created with the SageMaker Python SDK (`make pipeline`), not Terraform, because it changes with the code. Terraform only provides the role and buckets it uses.

## 6. Terraform rules
1. Backend: S3 bucket from step 7, key `lpp/terraform.tfstate`, `encrypt = true`, `use_lockfile = true` (S3 native locking; needs Terraform 1.11 or later; no DynamoDB table).
2. Every run uses `-lock-timeout=5m`, so a second run waits for the first instead of failing.
3. One infrastructure run at a time (coordinator spec, section 8).
4. Every change goes through `make plan`; the owner reads the plan; only then `make apply`.
5. After each successful apply, the commit is tagged `infra-good-YYYYMMDD-N`.
6. No secrets in `.tf` files, variables files or state.

## 7. Recovery
| Situation | One command |
|---|---|
| Something is broken or was changed by hand | `make restore TAG=infra-good-...`: checks out that tag's `infra/` folder and runs `terraform apply`, putting everything back as the code says |
| Everything is tangled | `make rebuild`: destroy, then apply. The state bucket (created outside Terraform) and the data bucket (`prevent_destroy`, versioned) survive |
| A run crashed and left a lock | Confirm nothing is running, then `terraform force-unlock <LOCK_ID>` (the ID is in the error message) |
| A file in S3 was overwritten | Restore the previous version from S3 versioning. Terraform restores infrastructure, not file contents |

## 8. Teardown after judging
`make destroy` removes the app, the endpoints, the IAM user and the registry. Then the owner deletes the access key (step 11). The data and state buckets are kept until the owner deletes them by hand.

## 9. Cost estimate (to be checked against the AWS bill)
| Item | Estimate |
|---|---|
| Lightsail Small, billed by the hour | About $0.50 a day |
| Serverless endpoint | Pennies for judge traffic; billed only while predicting |
| Pipeline runs (small instances, minutes each) | Cents per run |
| Bedrock Haiku: note reader and capped outreach drafts | Low single-digit dollars in total |
| S3 | Pennies |
| **Weekend build plus a week of judging** | **Roughly $10 to $20**, well within the $50 budget alert |

## 10. Testing requirements and acceptance criteria
| # | Check |
|---|---|
| I1 | `terraform plan` shows only `lpp-` resources in us-east-1 |
| I2 | A request to the app without the password is refused |
| I3 | The S3 buckets reject public access (S3 console shows "Bucket and objects not public") |
| I4 | With the endpoint stopped, the app still scores, using the fallback model, and the status bar says so |
| I5 | `lpp-app-runtime` is refused if it tries anything except the two endpoints and Haiku |
| I6 | No secret found in the repo (`git grep` for key patterns, and CI) |
| I7 | `make destroy` leaves no billable `lpp-` resources |
| I8 | The app limits each session: at most 5 outreach drafts and 200 scoring requests per session, and a lockout after 5 wrong passwords from one session; Bedrock calls stop when a daily cap is reached |
| I9 | Budget protection: the $50 budget sends alerts at 50%, 80% and 100%; at 100% an AWS Budgets action (owner-created) attaches a deny policy to `lpp-app-runtime`, stopping Bedrock and endpoint calls; the app then falls back to the packaged model and template drafts |

## 11. Full build (not in the hackathon)
GitHub Actions deploys through a short-lived OIDC role instead of the owner's laptop; separate dev and demo environments; the app runs on ECS or EKS in the client's account from the same container image.

## Change log
| Date | Change |
|---|---|
| Nov 27, 2026 | v0.1: first draft from the owner's voice decisions |
| Nov 27, 2026 | v0.2 after the independent review (R-09): state bucket renamed outside `lpp-*`; deployer denied access-key creation; `.env` git-ignored; plain-text Lightsail variables noted; per-session limits and a budget action added |
