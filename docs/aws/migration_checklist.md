# AWS Migration Checklist (No Vercel/Railway)

## 1) Backend container
- Build image from `backend/Dockerfile`.
- Push image to ECR.
- Deploy service on ECS Fargate behind ALB.

## 2) Networking
- Create VPC with public/private subnets.
- Run ECS tasks in private subnets.
- Use NAT Gateway with Elastic IP for fixed egress.
- Keep the Elastic IP list for Snowflake allowlist.

## 3) App database
- Provision RDS PostgreSQL.
- Set `DATABASE_URL` in runtime secrets.

## 4) Secrets and environment
- Store Snowflake and database secrets in AWS Secrets Manager.
- Inject env vars into ECS task definition:
  - `DATABASE_URL`
  - `SNOWFLAKE_USER`
  - `SNOWFLAKE_ACCOUNT`
  - `SNOWFLAKE_DATABASE`
  - `SNOWFLAKE_SCHEMA`
  - `SNOWFLAKE_WAREHOUSE`
  - `SNOWFLAKE_ROLE`
  - `SNOWFLAKE_AUTH_METHOD`
  - `SNOWFLAKE_TOKEN` or `SNOWFLAKE_PASSWORD`

## 5) Snowflake
- Execute `docs/aws/snowflake_setup_aws.sql`.
- Add NAT Elastic IP(s) to `ALLOWED_IP_LIST` in `NETWORK POLICY`.
- Apply policy to service user.

## 6) Frontend hosting
- Deploy frontend to S3 + CloudFront (or Amplify Hosting).
- Configure `NEXT_PUBLIC_API_URL` with backend public API domain.

## 7) Validation
- Backend health: `GET /`
- Snowflake health: `GET /api/health/snowflake`
- Business path: `POST /api/synapse/ask`
- Frontend E2E test against production domain.
