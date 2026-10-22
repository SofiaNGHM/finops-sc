#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../infra"
if ! command -v terraform >/dev/null; then echo 'ERROR: terraform not installed'; exit 1; fi
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
terraform plan -input=false -var='enable_network=false' -var='enable_nat=false' -var='enable_compute=false'
echo 'No apply performed.'
