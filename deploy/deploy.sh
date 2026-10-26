#!/bin/bash
# Deploy stage: starts an image that is already in ECR on the stack's server through SSM. Builds nothing.
# Usage: deploy/deploy.sh [TAG]. Without TAG it deploys the image tagged "dev" (the newest build of main).
# The server gets docker-compose.prod.yaml and the Caddyfile from the image's own commit.
# Run from the repository root with `make deploy` or `make deploy TAG=<tag>`.
set -euo pipefail
STACK=${STACK:-artmneme}

output() {
  aws cloudformation describe-stacks --stack-name "$STACK" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}
repository=$(output RepositoryUri)
instance=$(output InstanceId)
url=$(output AppUrl)

tag=${1:-}
if [ -z "$tag" ]; then
  # The timestamped tag of the image that "dev" points to.
  tag=$(aws ecr describe-images --repository-name "${repository#*/}" --image-ids imageTag=dev \
    --query 'imageDetails[0].imageTags' --output text | tr '\t' '\n' | grep -E '^[0-9]{8}-[0-9]{6}-[0-9a-f]{7}$' | head -1)
fi
[[ "$tag" =~ ^[0-9]{8}-[0-9]{6}-([0-9a-f]{7})$ ]] || { echo "Not an image tag of the form YYYYMMDD-HHMMSS-shortsha: '$tag'"; exit 1; }
commit=${BASH_REMATCH[1]}
aws ecr describe-images --repository-name "${repository#*/}" --image-ids imageTag="$tag" > /dev/null

compose=$(git show "$commit:deploy/docker-compose.prod.yaml" | base64 -w0)
caddy=$(git show "$commit:deploy/Caddyfile" | base64 -w0)
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
