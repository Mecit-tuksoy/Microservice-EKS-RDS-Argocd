# backend-setup.tf

provider "aws" {
  region = "us-east-1" # Bölgenizi belirtin
}

# S3 Bucket Oluşturma
resource "aws_s3_bucket" "terraform_state" {
  bucket = "mecit-terraform-state" # Benzersiz bir bucket adı seçin
  force_destroy = true

  tags = {
    Name        = "Terraform State Bucket"
    Environment = "Production"
  }
 }

# S3 Bucket Public Access Block Ayarı
resource "aws_s3_bucket_public_access_block" "terraform_state_block" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}


# S3 Bucket Versioning Ayarı
resource "aws_s3_bucket_versioning" "terraform_state_versioning" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket Server-Side Encryption Ayarı
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state_encryption" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# DynamoDB Table Oluşturma (State Kilitleme için)
resource "aws_dynamodb_table" "terraform_locks" {
  name         = "mecit-terraform-state-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name        = "Terraform State Lock Table"
    Environment = "Production"
  }
}
