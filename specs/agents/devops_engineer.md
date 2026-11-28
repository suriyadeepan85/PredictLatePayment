# Infrastructure / DevOps Engineer Specification

**Version:** 0.1 · **Date:** November 26, 2026 · **Methodology:** sections 7.4 and 8 · **Status:** PROPOSED (D-079)

## 1. Objective and scope
Make the prototype easy to run and, if the owner approves, deploy it.

| Item | Hackathon | Full build |
|---|---|---|
| Local run | Must: `requirements.txt`, `make data`, `make train`, `make app` | Same |
| Tests in CI | Should: GitHub Actions runs `pytest` on each push (no data needed; tests use small fixtures) | Must |
| AWS deployment | Must (D-082): Lightsail container plus a SageMaker serverless endpoint, in Terraform, as `specs/infrastructure.md` says. Nothing is applied before the owner approves that spec and reviews the plan | ECS or EKS from the same image, deployed by GitHub Actions through OIDC |
| Bedrock access | Depends on Q-001 and Q-003 | IAM role with Bedrock invoke only |

## 2. Permissions (methodology section 8)
| Action | Who decides |
|---|---|
| Recommend resources, write infrastructure code | DevOps agent |
| Create any AWS resource, spend money, open network access | Owner |
| Store credentials | Never in git; environment variables or AWS Secrets Manager |

## 3. Deliverables
`requirements.txt`, `Dockerfile`, `Makefile` (`plan`, `apply`, `restore`, `destroy`, `pipeline`, `deploy-app`), `.github/workflows/tests.yml`, Terraform in `infra/`, the bootstrap policies in `infra/bootstrap/`.

## 4. Acceptance criteria
- A fresh clone, plus the two raw files, runs `make data train app` without manual steps.
- CI passes on `main`.
- No secret appears in the repo.
- Any AWS deployment has a recorded owner approval and a cost estimate first.
