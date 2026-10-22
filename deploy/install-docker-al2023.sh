#!/usr/bin/env bash
# Ejecutar manualmente en APP y DATA solo después de autorizar el despliegue.
# Requiere Amazon Linux 2023 y salida HTTPS temporal (por ejemplo, NAT).
set -euo pipefail

if [[ $(id -u) -ne 0 ]]; then
  echo "Ejecutar como root: sudo bash deploy/install-docker-al2023.sh" >&2
  exit 1
fi

source /etc/os-release
if [[ ${ID:-} != amzn || ${VERSION_ID:-} != 2023* ]]; then
  echo "Este instalador solo admite Amazon Linux 2023." >&2
  exit 1
fi

if [[ $(uname -m) != x86_64 ]]; then
  echo "La versión fijada del complemento requiere arquitectura x86_64." >&2
  exit 1
fi

dnf install -y docker curl
systemctl enable --now docker

compose_version=v5.6.0
plugin_dir=/usr/local/lib/docker/cli-plugins
plugin_path="$plugin_dir/docker-compose"
download=$(mktemp)
trap 'rm -f "$download"' EXIT
curl --fail --location --show-error --silent --retry 3 \
  "https://github.com/docker/compose/releases/download/${compose_version}/docker-compose-linux-x86_64" \
  --output "$download"
install -d -m 0755 "$plugin_dir"
install -m 0755 "$download" "$plugin_path"

docker version
docker compose version
echo "Docker instalado. Los contenedores no se han iniciado."
