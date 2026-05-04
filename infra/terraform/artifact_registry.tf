resource "google_artifact_registry_repository" "containers" { location=var.region repository_id=var.artifact_repo format="DOCKER" depends_on=[google_project_service.apis] }
