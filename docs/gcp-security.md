# GCP Security Guide

This document outlines practical security controls for running CineTag on GCP.

## 1) Threat model summary

Primary risks:

- Unauthorized access to media assets in Cloud Storage
- Secret leakage (database credentials, LLM keys)
- Abuse of signed-upload flow
- Over-privileged service accounts
- Untrusted content ingestion and processing

## 2) Identity and access management

- Use **dedicated service accounts** for API, worker, and frontend services.
- Grant least-privilege IAM roles only.
- Avoid broad project-level editor/owner bindings for runtime identities.
- Restrict human access with role-based groups and break-glass patterns.

## 3) Secrets and key management

- Store sensitive config in **Secret Manager**.
- Inject secrets at runtime; do not bake into images.
- Rotate external API keys and DB credentials on a schedule.
- Enable secret access audit logging and alert on unusual access patterns.

## 4) Network and service boundaries

- Keep API public only if needed; worker should be non-public.
- Prefer private networking where possible for SQL/Redis.
- Limit CORS to explicit frontend origins.
- Use HTTPS everywhere (Cloud Run managed TLS by default).

## 5) Storage security (Cloud Storage)

- Block public bucket access.
- Use signed URLs with short TTL for upload operations.
- Constrain allowed MIME types and file size at API init.
- Apply lifecycle rules for stale pending uploads.
- Consider malware/content scanning before downstream usage in production.

## 6) Application-layer controls

- Validate all API payloads with strict schemas.
- Enforce idempotency and stage transition integrity.
- Record immutable audit trails for tag review and publish actions.
- Sanitize/validate any user-editable fields shown in UI.

## 7) Supply-chain and build security

- Build images in Cloud Build with reproducible pipeline config.
- Pin base image versions where feasible.
- Scan images for vulnerabilities before promotion.
- Keep dependency updates on a regular cadence.

## 8) Monitoring and detection

- Alert on auth failures, unusual secret access, and sudden 401/403 spikes.
- Monitor signed-URL generation and upload error anomalies.
- Track worker stage failure spikes that may indicate malformed/hostile media.

## 9) Security hardening checklist

- [ ] Least-privilege service accounts in place.
- [ ] Secret Manager used for all sensitive runtime values.
- [ ] Bucket public access disabled.
- [ ] CORS origins restricted.
- [ ] Runtime images scanned.
- [ ] Alert policies configured for auth/secret anomalies.
- [ ] Regular key/credential rotation process documented.

## 10) Compliance-minded extensions (optional)

For enterprise contexts, add:

- CMEK-backed encryption controls.
- VPC Service Controls.
- Data retention/erasure workflows.
- PII redaction in transcripts and logs.
