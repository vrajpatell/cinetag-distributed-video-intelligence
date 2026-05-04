variable "project_id" {type=string default="cinetag-distributed-video"}
variable "region" {type=string default="us-central1"}
variable "artifact_repo" {type=string default="cinetag-containers"}
variable "bucket_name" {type=string default="cinetag-distributed-video-media"}
variable "cloud_sql_instance" {type=string default="cinetag-postgres"}
variable "db_name" {type=string default="cinetag"}
variable "db_user" {type=string default="cinetag_app"}
variable "redis_name" {type=string default="cinetag-redis"}
