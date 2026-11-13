terraform {
  required_version = ">= 1.17.2, < 2.0.0"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "4.7.0"
    }
  }
}

provider "docker" {}

variable "image_id" {
  type        = string
  description = "Locally built, reviewed image ID (docker inspect --format={{.Id}} dci:0.1.0rc1). No registry push."
  validation {
    condition     = can(regex("^sha256:[a-f0-9]{64}$", var.image_id))
    error_message = "Supply the immutable local Docker image ID."
  }
}

variable "config_directory" {
  type        = string
  description = "Absolute external directory containing config.json and auth.json, readable by UID10001. Contents are not placed in Terraform state."
  validation {
    condition     = startswith(var.config_directory, "/")
    error_message = "Use an absolute Linux host path."
  }
}

variable "models_directory" {
  type        = string
  description = "Absolute external model directory, read-only in containers. Baseline may use an empty directory."
  validation {
    condition     = startswith(var.models_directory, "/")
    error_message = "Use an absolute Linux host path."
  }
}

variable "worker_count" {
  type    = number
  default = 2
  validation {
    condition     = var.worker_count >= 1 && var.worker_count <= 4 && floor(var.worker_count) == var.worker_count
    error_message = "This single-host reference supports one to four bounded CPU workers."
  }
}

resource "docker_network" "review" {
  name     = "dci-tf-review"
  internal = true
}

resource "docker_volume" "data" {
  name = "dci-tf-data"
  lifecycle {
    prevent_destroy = true
  }
}

locals {
  commands = merge({ api = ["serve", "--host", "0.0.0.0", "--port", "8000", "--config", "/etc/dci/config.json"] },
  { for i in range(var.worker_count) : "worker-${i}" => ["worker", "--config", "/etc/dci/config.json"] })
}

resource "docker_container" "service" {
  for_each      = local.commands
  name          = "dci-tf-${each.key}"
  image         = var.image_id
  command       = each.value
  user          = "10001:10001"
  read_only     = true
  init          = true
  restart       = "unless-stopped"
  stop_timeout  = each.key == "api" ? 30 : 240
  memory        = each.key == "api" ? 512 : 1200
  memory_swap   = each.key == "api" ? 512 : 1200
  cpus          = each.key == "api" ? "1" : "2"
  network_mode  = each.key == "api" ? "bridge" : "none"
  security_opts = ["no-new-privileges:true"]
  tmpfs         = { "/tmp" = "rw,noexec,nosuid,size=268435456" }
  log_driver    = "json-file"
  log_opts      = { "max-size" = "10m", "max-file" = "3" }
  capabilities {
    drop = ["ALL"]
  }
  dynamic "networks_advanced" {
    for_each = each.key == "api" ? [1] : []
    content {
      name = docker_network.review.id
    }
  }
  dynamic "ports" {
    for_each = each.key == "api" ? [1] : []
    content {
      internal = 8000
      external = 8000
      ip       = "127.0.0.1"
    }
  }
  volumes {
    volume_name    = docker_volume.data.name
    container_path = "/var/lib/dci"
  }
  volumes {
    host_path      = var.config_directory
    container_path = "/etc/dci"
    read_only      = true
  }
  volumes {
    host_path      = var.models_directory
    container_path = "/models"
    read_only      = true
  }
  ulimit {
    name = "nofile"
    soft = 1024
    hard = 1024
  }
}

output "review_url" {
  value = "http://127.0.0.1:8000"
}
