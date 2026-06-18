#!/bin/bash

set -euo pipefail

QUEUE_NAME="hospital-event-queue"
BUCKET_NAME="hospital-events"

echo "=== Initializing Localstack resources ==="

echo "Creating SQS queue: ${QUEUE_NAME}"
awslocal sqs create-queue --queue-name "${QUEUE_NAME}" >/dev/null
echo "SQS queue ready"

if awslocal s3api head-bucket --bucket "${BUCKET_NAME}" 2>/dev/null; then
  echo "S3 bucket already exists: ${BUCKET_NAME}"
else
  echo "Creating S3 bucket: ${BUCKET_NAME}"
  awslocal s3 mb "s3://${BUCKET_NAME}" >/dev/null
fi

echo "=== Localstack initialization complete ==="
