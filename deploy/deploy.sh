#!/bin/bash
# Builds the image, pushes it to the stack's ECR repository, and starts it on the server through SSM.
# Run from the repository root with `make deploy`, after `make deploy-stack`.
set -euo pipefail
STACK=${STACK:-artmneme}

output() {
  aws cloudformation describe-stacks --stack-name "$STACK" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}
repository=$(output RepositoryUri)
instance=$(output InstanceId)
url=$(output AppUrl)
tag=$(git rev-parse --short HEAD)$(git diff --quiet HEAD || echo -dirty)

docker build -t "$repository:$tag" .
aws ecr get-login-password | docker login --username AWS --password-stdin "${repository%%/*}"
docker push "$repository:$tag"

# The server gets the compose file and Caddyfile from this repository, so both always match it.
compose=$(base64 -w0 deploy/docker-compose.prod.yaml)
caddy=$(base64 -w0 deploy/Caddyfile)
command_id=$(aws ssm send-command --instance-ids "$instance" --document-name AWS-RunShellScript \
  --comment "ArtMneme $tag" --query Command.CommandId --output text --parameters "{\"commands\": [
    \"cd /opt/artmneme\",
    \"echo $compose | base64 -d > docker-compose.prod.yaml\",
    \"echo $caddy | base64 -d > Caddyfile\",
    \"echo $repository:$tag > image\",
    \"./start.sh\"]}")

while true; do
  status=$(aws ssm get-command-invocation --command-id "$command_id" --instance-id "$instance" \
    --query Status --output text 2>/dev/null || echo Pending)
  case "$status" in Pending|InProgress|Delayed) sleep 3 ;; *) break ;; esac
done
aws ssm get-command-invocation --command-id "$command_id" --instance-id "$instance" \
  --query '[StandardOutputContent, StandardErrorContent]' --output text
[ "$status" = Success ] || { echo "Deploy failed on the server: $status"; exit 1; }
echo "Deployed $tag to $url"
