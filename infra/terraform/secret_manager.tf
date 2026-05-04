resource "google_secret_manager_secret" "database_password" { secret_id="DATABASE_PASSWORD" replication { auto {} } }
resource "google_secret_manager_secret_version" "database_password" { secret=google_secret_manager_secret.database_password.id secret_data=random_password.db.result }
