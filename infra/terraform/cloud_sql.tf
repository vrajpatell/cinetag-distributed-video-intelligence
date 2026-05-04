resource "random_password" "db" { length=24 special=true }
resource "google_sql_database_instance" "postgres" { name=var.cloud_sql_instance region=var.region database_version="POSTGRES_15" settings { tier="db-f1-micro" backup_configuration {enabled=true} ip_configuration {ipv4_enabled=true} } }
resource "google_sql_database" "db" { name=var.db_name instance=google_sql_database_instance.postgres.name }
resource "google_sql_user" "app" { name=var.db_user instance=google_sql_database_instance.postgres.name password=random_password.db.result }
