#!/bin/bash
# The alert trigger's switch on prod: `deploy/fault.sh on` makes every artwork creation fail on purpose,
# `deploy/fault.sh off` ends it. It sets SSM /artmneme/artmneme-fault and restarts the app through SSM
# (the server's start script reads SSM again). Needs a deploy that includes ARTMNEME_FAULT in the compose file.
set -euo pipefail
STACK=${STACK:-artmneme}
case "${1:-}" in
  on) aws ssm put-parameter --type String --overwrite --name /artmneme/artmneme-fault --value artwork-creation > /dev/null ;;
  off) aws ssm delete-parameter --name /artmneme/artmneme-fault 2> /dev/null || true ;;
  *) echo "Usage: deploy/fault.sh on|off"; exit 1 ;;
esac
instance=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='InstanceId'].OutputValue" --output text)
command_id=$(aws ssm send-command --instance-ids "$instance" --document-name AWS-RunShellScript \
  --comment "ArtMneme fault switch $1" --query Command.CommandId --output text \
  --parameters '{"commands": ["cd /opt/artmneme && ./start.sh"]}')
while true; do
  status=$(aws ssm get-command-invocation --command-id "$command_id" --instance-id "$instance" \
    --query Status --output text 2>/dev/null || echo Pending)
  case "$status" in Pending|InProgress|Delayed) sleep 3 ;; *) break ;; esac
done
[ "$status" = Success ] || { echo "Restart failed on the server: $status"; exit 1; }
echo "Fault switch $1 on $STACK."
