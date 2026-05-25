# Terraform Best Practices Guide

A comprehensive guide based on real-world implementation experience with Terraform, covering project structure, state management, module design, security, testing, and deployment patterns — with AWS as the primary provider.

## Table of Contents

1. [Project Structure](#project-structure)
2. [Environment Configuration](#environment-configuration)
3. [State Management](#state-management)
4. [Module Design](#module-design)
5. [Variables and Outputs](#variables-and-outputs)
6. [Resource Naming and Tagging](#resource-naming-and-tagging)
7. [Security Considerations](#security-considerations)
8. [Error Handling and Lifecycle](#error-handling-and-lifecycle)
9. [Testing Strategies](#testing-strategies)
10. [CI/CD Integration](#cicd-integration)
11. [Deployment Guidelines](#deployment-guidelines)
12. [Common Pitfalls and Solutions](#common-pitfalls-and-solutions)

---

## Project Structure

### Recommended Directory Layout

```
infrastructure/
├── environments/
│   ├── dev/
│   │   ├── main.tf             # Dev environment root
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── terraform.tfvars    # Dev-specific values
│   │   └── backend.tf          # Dev state backend config
│   ├── staging/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── terraform.tfvars
│   │   └── backend.tf
│   └── prod/
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       ├── terraform.tfvars
│       └── backend.tf
├── modules/
│   ├── networking/             # VPC, subnets, security groups
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── README.md
│   ├── compute/                # EC2, ECS, Lambda
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── database/               # RDS, DynamoDB
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── storage/                # S3, EFS
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── global/                     # Account-wide resources (IAM, Route53)
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── scripts/
│   ├── init.sh                 # Bootstrap state backend
│   └── plan-all.sh             # Plan all environments
└── .terraform.lock.hcl         # Provider version lock file
```

### Key Principles

- **Environments as directories**: Separate state per environment, not workspaces
- **Modules for reuse**: Extract anything used in 2+ places into a module
- **Global vs regional**: Keep account-wide resources (IAM roles, Route53 zones) in `global/`
- **Lock provider versions**: Always commit `.terraform.lock.hcl`
- **One root module per environment**: Prevents accidental cross-environment changes

---

## Environment Configuration

### Separate Directories, Not Workspaces

Avoid Terraform workspaces for environment separation. Use separate directories instead.

**Why:** Workspaces share a single backend config and make it easy to accidentally `apply` to the wrong environment.

```hcl
# ✅ environments/prod/backend.tf
terraform {
  backend "s3" {
    bucket         = "myorg-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "ap-southeast-1"
    dynamodb_table = "myorg-terraform-locks"
    encrypt        = true
  }
}

# ✅ environments/dev/backend.tf
terraform {
  backend "s3" {
    bucket         = "myorg-terraform-state"
    key            = "dev/terraform.tfstate"
    region         = "ap-southeast-1"
    dynamodb_table = "myorg-terraform-locks"
    encrypt        = true
  }
}
```

### tfvars Per Environment

```hcl
# environments/prod/terraform.tfvars
environment    = "prod"
aws_region     = "ap-southeast-1"
instance_type  = "t3.large"
min_capacity   = 3
max_capacity   = 10
enable_deletion_protection = true

# environments/dev/terraform.tfvars
environment    = "dev"
aws_region     = "ap-southeast-1"
instance_type  = "t3.micro"
min_capacity   = 1
max_capacity   = 2
enable_deletion_protection = false
```

### Standard Provider Configuration (This Project)

This project currently targets the **Dev environment**. When promoted to **Prod**, it will run through Jenkins — the provider block is written to be compatible with both, requiring zero changes when Jenkins picks it up.

#### Dev (local) — use as-is

```hcl
# main.tf
provider "aws" {
  region  = var.region
  profile = var.aws_profile   # "shareddev01" locally, empty string in Jenkins

  assume_role {
    role_arn = "arn:aws:iam::221048274280:role/TerraformDeployments"
  }

  default_tags {
    tags = {
      Appname     = "OPS-DM"
      Environment = var.environment
      Owner       = "ITOPS"
    }
  }
}
```

```hcl
# variables.tf — add this variable
variable "aws_profile" {
  description = "AWS CLI profile for local dev. Set to empty string in CI/CD (Jenkins uses IAM role on the agent)."
  type        = string
  default     = "shareddev01"
}
```

```hcl
# terraform.tfvars (dev)
region      = "ap-southeast-1"
environment = "dev"
aws_profile = "shareddev01"
```

#### Prod via Jenkins — same provider block, different tfvars

Jenkins agents run with an IAM role attached — no CLI profile needed. Jenkins passes `aws_profile = ""` which tells the AWS provider to skip profile lookup and use the instance role instead. The `assume_role` block is still evaluated and still grants `TerraformDeployments` permissions.

```hcl
# terraform.tfvars (prod — used by Jenkins)
region      = "ap-southeast-1"
environment = "prod"
aws_profile = ""    # Jenkins IAM role handles auth, no profile needed
```

No changes to `main.tf` or the provider block when moving to prod — only `tfvars` changes.

---

#### Why `assume_role`

The `shareddev01` profile (dev) and the Jenkins IAM role (prod) both have limited base permissions by design. Assuming `TerraformDeployments` grants the elevated permissions needed to provision AWS services (Lambda, DynamoDB, S3, SQS, etc.). Your credentials never hold broad permissions directly — reducing blast radius if keys or roles are ever compromised.

Without this block, most `terraform apply` calls will fail with `AccessDenied`.

#### Why `default_tags`

The `default_tags` block automatically stamps **every** resource Terraform creates — no need to add tags per-resource. This is the mechanism leadership uses to track AWS spend by team in Cost Explorer:

| Tag | Value | Purpose |
|---|---|---|
| `Appname` | `OPS-DM` | Groups all spend under the OPS-DM team for cost allocation |
| `Environment` | `var.environment` | Separates dev vs prod spend |
| `Owner` | `ITOPS` | Identifies owning team for billing and escalation |

If these tags are missing, spend appears as unallocated in finance dashboards. Never skip `default_tags`.

> **Note:** The `role_arn` uses a double colon (`::`) before the account ID — IAM ARNs have no region segment. Ensure `~/.aws/credentials` has a `[shareddev01]` profile before running `terraform init` locally.

### Provider Version Pinning

Pin provider versions tightly:

```hcl
# environments/prod/main.tf
terraform {
  required_version = ">= 1.6.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.30"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "terraform"
      Project     = var.project_name
    }
  }
}
```

---

## State Management

### Bootstrap the State Backend First

The S3 bucket and DynamoDB table for state must exist before running `terraform init`. Create them once manually or with a bootstrap script:

```bash
# scripts/init.sh
#!/bin/bash
BUCKET="myorg-terraform-state"
TABLE="myorg-terraform-locks"
REGION="ap-southeast-1"

aws s3api create-bucket \
  --bucket "$BUCKET" \
  --region "$REGION" \
  --create-bucket-configuration LocationConstraint="$REGION"

aws s3api put-bucket-versioning \
  --bucket "$BUCKET" \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket "$BUCKET" \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}
    }]
  }'

aws s3api put-public-access-block \
  --bucket "$BUCKET" \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

aws dynamodb create-table \
  --table-name "$TABLE" \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region "$REGION"
```

### State File Security

```hcl
# Ensure state bucket blocks all public access
resource "aws_s3_bucket_public_access_block" "state" {
  bucket = aws_s3_bucket.state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning for state history and recovery
resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration {
    status = "Enabled"
  }
}
```

### Remote State Data Sources

Reference outputs from other state files instead of hardcoding values:

```hcl
# Read networking outputs from another state file
data "terraform_remote_state" "networking" {
  backend = "s3"
  config = {
    bucket = "myorg-terraform-state"
    key    = "${var.environment}/networking/terraform.tfstate"
    region = "ap-southeast-1"
  }
}

resource "aws_instance" "app" {
  subnet_id = data.terraform_remote_state.networking.outputs.private_subnet_ids[0]
  # ...
}
```

---

## Module Design

### Module Interface Contract

Every module must have a clear `variables.tf` and `outputs.tf`:

```hcl
# modules/networking/variables.tf
variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging, or prod."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of AZs to deploy subnets into"
  type        = list(string)
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (one per AZ)"
  type        = list(string)
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (one per AZ)"
  type        = list(string)
}
```

```hcl
# modules/networking/outputs.tf
output "vpc_id" {
  description = "ID of the created VPC"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = aws_subnet.public[*].id
}

output "default_security_group_id" {
  description = "Default security group ID for the VPC"
  value       = aws_vpc.main.default_security_group_id
}
```

### Module Versioning

Pin modules to a specific version or commit:

```hcl
# ✅ Pinned to a version tag
module "networking" {
  source  = "git::https://github.com/myorg/terraform-modules.git//networking?ref=v1.3.0"

  environment          = var.environment
  vpc_cidr             = "10.0.0.0/16"
  availability_zones   = ["ap-southeast-1a", "ap-southeast-1b"]
  private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnet_cidrs  = ["10.0.101.0/24", "10.0.102.0/24"]
}

# ✅ Local module reference (for monorepo)
module "networking" {
  source = "../../modules/networking"

  environment          = var.environment
  vpc_cidr             = "10.0.0.0/16"
  availability_zones   = data.aws_availability_zones.available.names
  private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnet_cidrs  = ["10.0.101.0/24", "10.0.102.0/24"]
}
```

### Module Composition Example

```hcl
# environments/prod/main.tf
module "networking" {
  source = "../../modules/networking"

  environment          = var.environment
  vpc_cidr             = var.vpc_cidr
  availability_zones   = data.aws_availability_zones.available.names
  private_subnet_cidrs = var.private_subnet_cidrs
  public_subnet_cidrs  = var.public_subnet_cidrs
}

module "database" {
  source = "../../modules/database"

  environment        = var.environment
  vpc_id             = module.networking.vpc_id
  subnet_ids         = module.networking.private_subnet_ids
  instance_class     = var.db_instance_class
  deletion_protection = var.enable_deletion_protection
}

module "compute" {
  source = "../../modules/compute"

  environment      = var.environment
  vpc_id           = module.networking.vpc_id
  subnet_ids       = module.networking.private_subnet_ids
  db_endpoint      = module.database.endpoint
  db_secret_arn    = module.database.secret_arn
}
```

---

## Variables and Outputs

### Variable Typing and Validation

Always use specific types and validate where possible:

```hcl
variable "instance_type" {
  description = "EC2 instance type for the application servers"
  type        = string
  default     = "t3.micro"

  validation {
    condition     = can(regex("^(t3|t3a|m5|m5a|c5|r5)\\.", var.instance_type))
    error_message = "instance_type must be from t3, t3a, m5, m5a, c5, or r5 family."
  }
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the application"
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for cidr in var.allowed_cidr_blocks :
      can(cidrhost(cidr, 0))
    ])
    error_message = "All values in allowed_cidr_blocks must be valid CIDR notation."
  }
}

variable "retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.retention_days)
    error_message = "retention_days must be a valid CloudWatch retention period."
  }
}
```

### Locals for Computed Values

Use `locals` to avoid repetition and derive values:

```hcl
locals {
  # Name prefix used across all resources
  name_prefix = "${var.project_name}-${var.environment}"

  # Common tags merged with resource-specific tags
  common_tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    CostCenter  = var.cost_center
  }

  # Determine if this is a production-grade deployment
  is_production = var.environment == "prod"

  # Compute AZ count dynamically
  az_count = length(var.availability_zones)

  # Build a map of subnet ID to AZ for easy lookups
  subnet_az_map = {
    for idx, subnet in aws_subnet.private :
    subnet.id => subnet.availability_zone
  }
}

resource "aws_cloudwatch_log_group" "app" {
  name              = "/aws/${local.name_prefix}/application"
  retention_in_days = local.is_production ? 90 : 7
  tags              = local.common_tags
}
```

### Sensitive Variable Handling

```hcl
variable "db_password" {
  description = "Master password for the RDS instance"
  type        = string
  sensitive   = true  # Prevents value from appearing in logs and plan output
}

# ✅ Better: Let AWS generate and manage secrets
resource "aws_secretsmanager_secret" "db" {
  name        = "${local.name_prefix}/db/credentials"
  description = "RDS master credentials"
  tags        = local.common_tags
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db.result
  })
}

resource "random_password" "db" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}
```

---

## Resource Naming and Tagging

### Consistent Naming Convention

```hcl
locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# Pattern: {project}-{environment}-{resource-type}-{descriptor}
resource "aws_s3_bucket" "logs" {
  bucket = "${local.name_prefix}-logs-${data.aws_caller_identity.current.account_id}"
}

resource "aws_security_group" "app" {
  name        = "${local.name_prefix}-sg-app"
  description = "Security group for application servers"
  vpc_id      = var.vpc_id
}

resource "aws_iam_role" "lambda_exec" {
  name = "${local.name_prefix}-role-lambda-exec"
}
```

### Mandatory Tagging Strategy

```hcl
# Use provider-level default_tags so every resource gets these
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      Project     = var.project_name
      ManagedBy   = "terraform"
      Repository  = "github.com/myorg/infrastructure"
    }
  }
}

# Resource-specific additional tags
resource "aws_instance" "app" {
  # ...
  tags = {
    Name      = "${local.name_prefix}-app-server"
    Role      = "application"
    Component = "backend"
  }
}
```

---

## Security Considerations

### Least Privilege IAM

Never use `*` actions or resources unless absolutely necessary:

```hcl
# ✅ Least privilege — only what the Lambda needs
resource "aws_iam_policy" "lambda_s3_read" {
  name        = "${local.name_prefix}-policy-lambda-s3-read"
  description = "Allows Lambda to read from the logs bucket only"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.logs.arn,
          "${aws_s3_bucket.logs.arn}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/${local.name_prefix}/*"
      }
    ]
  })
}

# ❌ Never do this
resource "aws_iam_policy" "bad" {
  policy = jsonencode({
    Statement = [{
      Effect   = "Allow"
      Action   = "*"
      Resource = "*"
    }]
  })
}
```

### Encryption at Rest and in Transit

```hcl
# S3 bucket with encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.main.arn
    }
    bucket_key_enabled = true  # Reduces KMS API calls and cost
  }
}

# RDS with encryption
resource "aws_db_instance" "main" {
  identifier        = "${local.name_prefix}-db"
  engine            = "postgres"
  engine_version    = "15.4"
  instance_class    = var.db_instance_class
  storage_encrypted = true
  kms_key_id        = aws_kms_key.main.arn

  # Force SSL connections
  parameter_group_name = aws_db_parameter_group.main.name
}

resource "aws_db_parameter_group" "main" {
  name   = "${local.name_prefix}-pg"
  family = "postgres15"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }
}
```

### Security Group Rules — Explicit Deny by Default

```hcl
resource "aws_security_group" "app" {
  name        = "${local.name_prefix}-sg-app"
  description = "Application server security group"
  vpc_id      = var.vpc_id

  # No inline ingress/egress — use separate rules for clarity and auditability
  tags = merge(local.common_tags, { Name = "${local.name_prefix}-sg-app" })
}

resource "aws_security_group_rule" "app_ingress_https" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb.id
  security_group_id        = aws_security_group.app.id
  description              = "HTTPS from ALB only"
}

resource "aws_security_group_rule" "app_egress_https" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.app.id
  description       = "Outbound HTTPS for AWS API calls"
}

# Explicit deny all other egress (no default allow-all egress)
```

---

## Error Handling and Lifecycle

### Lifecycle Rules

```hcl
resource "aws_s3_bucket" "assets" {
  bucket = "${local.name_prefix}-assets"

  lifecycle {
    # Prevent accidental deletion of the bucket
    prevent_destroy = true
  }
}

resource "aws_instance" "app" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = var.instance_type

  lifecycle {
    # Replace instance when AMI changes, rather than in-place update
    create_before_destroy = true

    # Ignore changes to AMI (controlled by separate AMI rotation process)
    ignore_changes = [ami, user_data]
  }
}
```

### Depends On for Implicit Dependencies

```hcl
resource "aws_iam_role_policy_attachment" "lambda" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.lambda_s3.arn
}

resource "aws_lambda_function" "processor" {
  function_name = "${local.name_prefix}-processor"
  role          = aws_iam_role.lambda.arn
  # ...

  # Lambda needs the policy attached before it can be invoked
  # Terraform doesn't know about this implicit dependency
  depends_on = [aws_iam_role_policy_attachment.lambda]
}
```

### Timeouts for Long-Running Resources

```hcl
resource "aws_db_instance" "main" {
  # ...

  timeouts {
    create = "60m"
    update = "60m"
    delete = "60m"
  }
}

resource "aws_ecs_service" "app" {
  # ...

  timeouts {
    create = "20m"
    delete = "20m"
  }
}
```

---

## Testing Strategies

### Terraform Validate and Format

Always run in CI before plan:

```bash
# Format check
terraform fmt -check -recursive

# Validate syntax and references
terraform validate

# Security scan
tfsec .
# or
checkov -d .
```

### Native Terraform Tests (v1.6+)

```hcl
# modules/networking/tests/networking.tftest.hcl
variables {
  environment          = "test"
  vpc_cidr             = "10.99.0.0/16"
  availability_zones   = ["ap-southeast-1a", "ap-southeast-1b"]
  private_subnet_cidrs = ["10.99.1.0/24", "10.99.2.0/24"]
  public_subnet_cidrs  = ["10.99.101.0/24", "10.99.102.0/24"]
}

run "vpc_is_created" {
  command = plan

  assert {
    condition     = aws_vpc.main.cidr_block == "10.99.0.0/16"
    error_message = "VPC CIDR block does not match expected value"
  }
}

run "correct_subnet_count" {
  command = plan

  assert {
    condition     = length(aws_subnet.private) == 2
    error_message = "Expected 2 private subnets, got ${length(aws_subnet.private)}"
  }

  assert {
    condition     = length(aws_subnet.public) == 2
    error_message = "Expected 2 public subnets, got ${length(aws_subnet.public)}"
  }
}
```

Run tests:
```bash
terraform test
```

### Terratest for Integration Tests

```go
// test/networking_test.go
package test

import (
    "testing"
    "github.com/gruntwork-io/terratest/modules/terraform"
    "github.com/gruntwork-io/terratest/modules/aws"
    "github.com/stretchr/testify/assert"
)

func TestNetworkingModule(t *testing.T) {
    t.Parallel()

    terraformOptions := &terraform.Options{
        TerraformDir: "../modules/networking",
        Vars: map[string]interface{}{
            "environment":          "test",
            "vpc_cidr":             "10.99.0.0/16",
            "availability_zones":   []string{"ap-southeast-1a", "ap-southeast-1b"},
            "private_subnet_cidrs": []string{"10.99.1.0/24", "10.99.2.0/24"},
            "public_subnet_cidrs":  []string{"10.99.101.0/24", "10.99.102.0/24"},
        },
    }

    defer terraform.Destroy(t, terraformOptions)
    terraform.InitAndApply(t, terraformOptions)

    vpcID := terraform.Output(t, terraformOptions, "vpc_id")
    assert.NotEmpty(t, vpcID)

    vpc := aws.GetVpcById(t, vpcID, "ap-southeast-1")
    assert.Equal(t, "10.99.0.0/16", vpc.CidrBlock)
}
```

---

## CI/CD Integration

### Jenkins Pipeline (Prod — Primary CI/CD)

When Dev is validated and ready to promote, Jenkins handles the prod deployment. The pipeline has an explicit **human approval gate** before apply — no accidental prod changes.

#### Prerequisites on the Jenkins side

1. Jenkins agent node must have an IAM role attached with permission to call `sts:AssumeRole` on `arn:aws:iam::221048274280:role/TerraformDeployments`
2. Terraform installed on the agent (or use the Terraform Jenkins plugin)
3. A Jenkins credential of type **Secret text** named `TF_STATE_BUCKET` storing the S3 backend bucket name

#### Jenkinsfile

```groovy
// Jenkinsfile — place at repo root
pipeline {
    agent { label 'terraform' }  // Jenkins node with Terraform + AWS CLI installed

    environment {
        TF_VERSION   = '1.7.0'
        AWS_REGION   = 'ap-southeast-1'
        TF_DIR       = 'infrastructure/environments/prod'
        // aws_profile = "" tells the provider to use the Jenkins IAM role
        TF_VAR_aws_profile  = ''
        TF_VAR_environment  = 'prod'
        TF_VAR_region       = "${AWS_REGION}"
    }

    options {
        timeout(time: 60, unit: 'MINUTES')
        disableConcurrentBuilds()   // Prevent parallel applies on same state
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Terraform Init') {
            steps {
                dir("${TF_DIR}") {
                    sh 'terraform init -input=false'
                }
            }
        }

        stage('Format & Validate') {
            steps {
                sh 'terraform fmt -check -recursive infrastructure/'
                dir("${TF_DIR}") {
                    sh 'terraform validate'
                }
            }
        }

        stage('Security Scan') {
            steps {
                sh 'tfsec infrastructure/ --no-colour'
            }
        }

        stage('Terraform Plan') {
            steps {
                dir("${TF_DIR}") {
                    sh '''
                        terraform plan \
                          -var-file=terraform.tfvars \
                          -out=tfplan \
                          -no-color \
                          2>&1 | tee plan.txt
                    '''
                    // Archive plan output for review before approval
                    archiveArtifacts artifacts: 'plan.txt', fingerprint: true
                }
            }
            post {
                always {
                    // Post plan summary to build description
                    script {
                        def plan = readFile("${TF_DIR}/plan.txt")
                        currentBuild.description = plan.tokenize('\n').last()
                    }
                }
            }
        }

        stage('Approval') {
            // Pause here — a human must review the plan and approve
            when {
                branch 'main'
            }
            steps {
                script {
                    def planSummary = readFile("${TF_DIR}/plan.txt")
                    input(
                        message: 'Review the Terraform plan above. Approve to apply to PROD?',
                        ok: 'Apply to Prod',
                        submitter: 'itops-leads,devops-team',  // Only these groups can approve
                        parameters: [
                            text(
                                name: 'PLAN_SUMMARY',
                                defaultValue: planSummary.tokenize('\n').last(),
                                description: 'Plan summary (read-only confirmation)'
                            )
                        ]
                    )
                }
            }
        }

        stage('Terraform Apply') {
            when {
                branch 'main'
            }
            steps {
                dir("${TF_DIR}") {
                    sh 'terraform apply -input=false tfplan'
                }
            }
        }

    }

    post {
        success {
            echo "Prod deployment complete. Resources tagged Appname=OPS-DM, Environment=prod."
        }
        failure {
            echo "Pipeline failed. Check plan.txt artifact for details."
            // Add Slack/email notification here
        }
        always {
            // Clean workspace to avoid stale state between runs
            cleanWs()
        }
    }
}
```

#### Pipeline Flow

```
Checkout → Init → Format/Validate → Security Scan → Plan → [APPROVAL GATE] → Apply
                                                              ↑
                                              itops-leads must click "Apply to Prod"
                                              after reviewing the plan.txt artifact
```

#### Key Jenkins Behaviours

| Setting | Why |
|---|---|
| `disableConcurrentBuilds()` | Prevents two Jenkins runs from locking the same state file simultaneously |
| `TF_VAR_aws_profile = ''` | Overrides the `shareddev01` default — Jenkins uses IAM role instead |
| `input()` with `submitter` | Only named groups can approve prod apply — prevents accidental deploys |
| `archiveArtifacts plan.txt` | Approver can read the full plan before clicking approve |
| `cleanWs()` | Wipes workspace after each run so stale `.terraform/` dirs don't cause issues |

---

### GitHub Actions Workflow

```yaml
# .github/workflows/terraform.yml
name: Terraform

on:
  push:
    branches: [main]
    paths: ["infrastructure/**"]
  pull_request:
    paths: ["infrastructure/**"]

env:
  TF_VERSION: "1.7.0"
  AWS_REGION: "ap-southeast-1"

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - name: Terraform Format Check
        run: terraform fmt -check -recursive infrastructure/

      - name: Terraform Validate (dev)
        working-directory: infrastructure/environments/dev
        run: |
          terraform init -backend=false
          terraform validate

      - name: tfsec Security Scan
        uses: aquasecurity/tfsec-action@v1.0.0
        with:
          working_directory: infrastructure/

  plan:
    needs: validate
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    permissions:
      id-token: write
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/github-actions-terraform
          aws-region: ${{ env.AWS_REGION }}

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - name: Terraform Plan (dev)
        id: plan
        working-directory: infrastructure/environments/dev
        run: |
          terraform init
          terraform plan -no-color -out=tfplan 2>&1 | tee plan.txt

      - name: Post Plan to PR
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const plan = fs.readFileSync('infrastructure/environments/dev/plan.txt', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Terraform Plan (dev)\n\`\`\`\n${plan.slice(-65000)}\n\`\`\``
            });

  apply:
    needs: validate
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    environment: production
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/github-actions-terraform
          aws-region: ${{ env.AWS_REGION }}

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - name: Terraform Apply (prod)
        working-directory: infrastructure/environments/prod
        run: |
          terraform init
          terraform apply -auto-approve
```

### OIDC-Based Authentication (No Long-Lived Keys)

```hcl
# global/github-actions.tf
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

resource "aws_iam_role" "github_actions_terraform" {
  name = "github-actions-terraform"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          # Only allow from your specific repo and main branch
          "token.actions.githubusercontent.com:sub" = "repo:myorg/infrastructure:ref:refs/heads/main"
        }
      }
    }]
  })
}
```

---

## Deployment Guidelines

### Plan Before Apply — Always

```bash
# Never apply without reviewing the plan first
terraform plan -out=tfplan
terraform show tfplan         # Review what will change
terraform apply tfplan        # Apply only the reviewed plan
```

### Targeted Apply for Emergencies

Use `-target` sparingly — it can leave state inconsistent:

```bash
# ✅ Acceptable in emergencies (broken dependency, failed partial apply)
terraform apply -target=aws_security_group.app

# ❌ Never use -target as a workflow shortcut to "skip" resources
```

### Drift Detection

Schedule regular drift checks in CI:

```bash
# Detect drift between state and real infrastructure
terraform plan -detailed-exitcode
# Exit code 0 = no changes, 1 = error, 2 = changes detected
```

### Import Existing Resources

```bash
# Import a manually created resource into state
terraform import aws_s3_bucket.logs myorg-prod-logs-123456789012

# Then run plan to verify the config matches the imported resource
terraform plan
```

### Destroy Safely

```bash
# Always plan destroy first
terraform plan -destroy

# Use targeted destroy to remove specific resources
terraform destroy -target=module.staging

# For resources with prevent_destroy, you must remove that block first
```

---

## Common Pitfalls and Solutions

### 1. `count` vs `for_each` — Use `for_each` for Maps

**Problem**: `count` creates indexed resources. Removing item at index 0 destroys and recreates everything after it.

**Solution**: Use `for_each` with maps for stable resource identity:

```hcl
# ❌ count — fragile, index-based
resource "aws_subnet" "private" {
  count             = length(var.private_subnet_cidrs)
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]
}

# ✅ for_each — stable, key-based identity
resource "aws_subnet" "private" {
  for_each = {
    for idx, cidr in var.private_subnet_cidrs :
    var.availability_zones[idx] => cidr
  }

  cidr_block        = each.value
  availability_zone = each.key
}
```

### 2. Hardcoded Account IDs and Region

**Problem**: Hardcoded values break when deploying to another account or region.

**Solution**: Use data sources:

```hcl
# ✅ Dynamic
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_iam_policy" "example" {
  policy = jsonencode({
    Statement = [{
      Resource = "arn:aws:s3:::${data.aws_caller_identity.current.account_id}-logs/*"
    }]
  })
}
```

### 3. Secrets in tfvars or State

**Problem**: Passwords in tfvars get committed. All values in tfvars end up in state.

**Solution**: Use AWS Secrets Manager and never pass secrets as variables:

```hcl
# ✅ Generate in Terraform, store in Secrets Manager
resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id     = aws_secretsmanager_secret.db.id
  secret_string = random_password.db.result
}

resource "aws_db_instance" "main" {
  password = random_password.db.result  # Only lives in state (encrypted)
}
```

### 4. Missing `depends_on` for Policy Attachments

**Problem**: Lambda or EC2 resources created before IAM policies are attached — causes runtime permission errors.

**Solution**: Explicit depends_on:

```hcl
resource "aws_lambda_function" "processor" {
  depends_on = [
    aws_iam_role_policy_attachment.lambda_exec,
    aws_cloudwatch_log_group.lambda,   # Log group must exist before Lambda
  ]
}
```

### 5. Not Locking Provider Versions

**Problem**: `~> 4.0` allows `4.x` which can break with provider updates.

**Solution**: Lock to minor version and commit the lock file:

```hcl
# ✅ Locked to patch-level changes only
required_providers {
  aws = {
    source  = "hashicorp/aws"
    version = "~> 5.30"   # Allows 5.30.x but not 5.31
  }
}
```

```bash
# Always commit this file
git add .terraform.lock.hcl
```

### 6. Large Monolithic State Files

**Problem**: One state file for everything means every plan/apply locks everyone out.

**Solution**: Split state by component with remote state data sources:

```
environments/prod/
├── networking/     # VPC, subnets, SGs — changes rarely
├── data/           # RDS, DynamoDB, S3 — changes occasionally
└── compute/        # Lambda, ECS, EC2 — changes frequently
```

---

## Conclusion

Terraform at scale requires discipline around state isolation, module boundaries, and security. Key takeaways:

- **Separate directories per environment** — not workspaces
- **Bootstrap state backend** before anything else
- **Pin all provider and module versions** and commit the lock file
- **Use `for_each` over `count`** for anything that could be removed from a list
- **Least-privilege IAM always** — never `*` actions or resources
- **No secrets in tfvars or variables** — use Secrets Manager
- **Always plan before apply** — never `terraform apply` directly
- **Split state by change frequency** — networking changes rarely, compute changes often
- **Use OIDC for CI/CD** — no long-lived access keys
- **Test modules** with `terraform test` or Terratest before deploying

Refer to the [Terraform documentation](https://developer.hashicorp.com/terraform) and [AWS provider docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs) for the latest API changes.
