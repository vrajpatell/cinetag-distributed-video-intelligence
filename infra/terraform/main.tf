# Terraform root module entry point.
#
# Resource definitions are split across files by concern:
# - providers and required provider versions
# - project service enablement
# - data plane infrastructure
# - Cloud Run services and jobs
# - IAM, secrets, monitoring, and outputs
