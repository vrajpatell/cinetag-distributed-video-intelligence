variable "project_id" {
  type    = string
  default = "cinetag-distributed-video"
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "artifact_repo" {
  type    = string
  default = "cinetag-containers"
}

variable "bucket_name" {
  type    = string
  default = "cinetag-distributed-video-media"
}

variable "cloud_sql_instance" {
  type    = string
  default = "cinetag-postgres"
}

variable "db_name" {
  type    = string
  default = "cinetag"
}

variable "db_user" {
  type    = string
  default = "cinetag_app"
}

variable "redis_name" {
  type    = string
  default = "cinetag-redis"
}

variable "vpc_name" {
  type    = string
  default = "cinetag-main-vpc"
}

variable "subnet_name" {
  type    = string
  default = "cinetag-main-subnet"
}

variable "subnet_cidr" {
  type    = string
  default = "10.10.0.0/24"
}

variable "cloud_sql_tier" {
  type    = string
  default = "db-custom-1-3840"
}

variable "deletion_protection" {
  type    = bool
  default = true
}

variable "queue_backend" {
  type    = string
  default = "celery"
}

variable "pubsub_topic_name" {
  type    = string
  default = "cinetag-processing-jobs"
}

variable "pubsub_subscription_name" {
  type    = string
  default = "cinetag-processing-jobs-sub"
}

variable "pubsub_dead_letter_topic_name" {
  type    = string
  default = "cinetag-processing-jobs-dlq"
}

variable "api_image" {
  type    = string
  default = "us-central1-docker.pkg.dev/cinetag-distributed-video/cinetag-containers/cinetag-api:latest"
}

variable "worker_image" {
  type    = string
  default = "us-central1-docker.pkg.dev/cinetag-distributed-video/cinetag-containers/cinetag-worker:latest"
}

variable "frontend_image" {
  type    = string
  default = "us-central1-docker.pkg.dev/cinetag-distributed-video/cinetag-containers/cinetag-frontend:latest"
}

variable "api_ingress" {
  type        = string
  description = "Cloud Run API ingress (e.g. INGRESS_TRAFFIC_ALL or INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER)"
  default     = "INGRESS_TRAFFIC_ALL"
}

variable "auth_enabled" {
  type    = bool
  default = true
}

variable "secret_manager_enabled" {
  type    = bool
  default = true
}

variable "semantic_search_backend" {
  type    = string
  default = "auto"
}

variable "enable_cloud_cdn" {
  type    = bool
  default = false
}
