#!/bin/bash
# Build stage: builds the image from the current commit, pushes it to the stack's ECR repository
# as <YYYYMMDD-HHMMSS>-<short commit> (UTC build time), and moves the tag "dev" to it.
# Run from the repository root with `make build`; CI runs it after all tests pass on main.
set -euo pipefail
STACK=${STACK:-artmneme}

git diff --quiet HEAD || { echo "Commit your changes first: the image tag names the commit."; exit 1; }
repository=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='RepositoryUri'].OutputValue" --output text)
tag=$(date -u +%Y%m%d-%H%M%S)-$(git rev-parse HEAD | cut -c1-7)

docker build --build-arg APP_VERSION="$tag" -t "$repository:$tag" .
aws ecr get-login-password | docker login --username AWS --password-stdin "${repository%%/*}"
docker push "$repository:$tag"

# "dev" always names the newest image built from main: the one that "Deploy to prod" promotes.
manifest=$(aws ecr batch-get-image --repository-name "${repository#*/}" --image-ids imageTag="$tag" \
  --query 'images[0].imageManifest' --output text)
# put-image refuses only when "dev" already points to this exact image; then check that it does.
aws ecr put-image --repository-name "${repository#*/}" --image-tag dev --image-manifest "$manifest" > /dev/null 2>&1 ||
  aws ecr describe-images --repository-name "${repository#*/}" --image-ids imageTag=dev > /dev/null
echo "Built $repository:$tag (tagged dev)"
