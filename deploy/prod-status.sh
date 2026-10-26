#!/bin/bash
# Read-only view of prod for the on-call engineer: the fault switch, the health check, the running image and the
# last app log lines.
# Usage: deploy/prod-status.sh [LINES] (default 100). Changes nothing. Uses the AWS profile artmneme-deploy
# unless AWS_PROFILE is set.
set -euo pipefail
export AWS_PROFILE=${AWS_PROFILE:-artmneme-deploy}
STACK=${STACK:-artmneme}
lines=${1:-100}
[[ "$lines" =~ ^[0-9]+$ ]] || { echo "Usage: deploy/prod-status.sh [LINES]"; exit 1; }

output() {
  aws cloudformation describe-stacks --stack-name "$STACK" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}
instance=$(output InstanceId)
url=$(output AppUrl)

echo "Fault switch: $(aws ssm get-parameter --name /artmneme/artmneme-fault --query Parameter.Value --output text 2>/dev/null || echo off)"
echo "Health: $(curl -s --max-time 10 "$url/api/health" || echo unreachable)"

command_id=$(aws ssm send-command --instance-ids "$instance" --document-name AWS-RunShellScript \
  --comment "ArtMneme prod status" --query Command.CommandId --output text --parameters "{\"commands\": [
    \"cd /opt/artmneme\",
    \"echo Image: \$(cat image)\",
    \"docker compose -f docker-compose.prod.yaml --env-file .env logs --no-color --tail $lines app\"]}")
while true; do
  status=$(aws ssm get-command-invocation --command-id "$command_id" --instance-id "$instance" \
    --query Status --output text 2>/dev/null || echo Pending)
  case "$status" in Pending|InProgress|Delayed) sleep 3 ;; *) break ;; esac
done
aws ssm get-command-invocation --command-id "$command_id" --instance-id "$instance" \
  --query '[StandardOutputContent, StandardErrorContent]' --output text
