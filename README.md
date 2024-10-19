# Microservice-EKS-RDS-Argocd

This project consists of a microservise Phonebook application written in Python and developed using the Flask framework, setting up a VPC on AWS with Terraform, creating an RDS and EKS cluster in a private subnet, configuring the GitOps workflow using ArgoCD and Ingress Controller, and deploying the application on EKS using credentials information from AWS Secrets Manager.

## Gereksinimler

1. **AWS CLI** - AWS hizmetlerini yönetmek için kullanılır. Version: aws-cli/2.18.4
2. **Terraform** - Altyapıyı kodla yönetmek için kullanılan araç. Version: v1.9.7
3. **kubectl** - Kubernetes cluster'ını yönetmek için komut satırı aracı. Version: v1.31.0
4. **Git** - GitHub ile entegrasyon için. Version: 2.34.1

# 1. Adım:

> > > AWS'de VPC, EKS, RDS, Secret Manager, S3, DaynamoDb, CloudWatch, Ec2 servislerine erişim yetkileri olan yeni bir kullanıcı oluşturuyoruz.

> > > Oluşturduğumuz bu kullanıcının Secret Key ve Secret Access Key bilgileri ile local bilgisayarımızdan sh`aws configure` yaparak AWS servislerine CLI aracılığı ile erişim sağlıyoruz.

# 2. Adım:

> > > Python ile yazılmış ve Flask framework kullanılılarak geliştirilmiş Phonebook uygulamasına AWS SDK'yi boto3 ekleyerek uygulamanın veri tabanı için gerekli olan kimlik bilgilerini AWS Secret manager'dan çekebilmesini sağlıyoruz. Repoda eklenmiş hali var.

# 3. Adım:

> > > Uygulamayı containerize etmek için Dockerfile'ını yazıyoruz.

```sh
# Dockerfile for web server
FROM python:alpine
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
WORKDIR /app
COPY . /app
EXPOSE 80
CMD python ./app.py
```

```sh
# Dockerfile for result server
FROM python:alpine
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
WORKDIR /app
COPY . /app
EXPOSE 80
CMD python ./app.py
```

```sh
# requirements.txt
flask==2.3.3
PyMySQL==1.0.2
boto3
```

# 4. Adım:

> > > Dockerfile ile image build ediyoruz ve Dockerhub'a push ediyoruz.

```sh
docker build -t mecit35/web-server .
```

```sh
docker build -t mecit35/result-server-2 .
```

```sh
docker login
```

```sh
docker push mecit35/web-server
```

```sh
docker push mecit35/result-server-2
```

# 5. Adım:

> > > Uygulamanın k8s manifest dosyalarını hazırlıyoruz.

web-server için Deployment ve Service yaml dosyaları:

```sh
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
spec:
  replicas: 1
  selector:
    matchLabels:
      name: web-pod
  template:
    metadata:
      labels:
        name: web-pod
    spec:
      containers:
        - image: mecit35/web-server
          name: web-pod
          ports:
            - containerPort: 80
          imagePullPolicy: Always

          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"

---
apiVersion: v1
kind: Service
metadata:
  name: web-service
  labels:
    name: web-svc
spec:
  selector:
    name: web-pod
  type: NodePort
  ports:
    - port: 80
      targetPort: 80
      nodePort: 30001
```

Result-server için Deployment ve Service yaml dosyaları:

```sh
apiVersion: apps/v1
kind: Deployment
metadata:
  name: result-deployment
spec:
  replicas: 1
  selector:
    matchLabels:
      name: result
  template:
    metadata:
      labels:
        name: result
    spec:
      containers:
        - image: mecit35/result-server-2
          name: result
          ports:
            - containerPort: 80
          imagePullPolicy: Always

          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
---
apiVersion: v1
kind: Service
metadata:
  name: result-service
  labels:
    name: result-service
spec:
  selector:
    name: result
  type: NodePort
  ports:
    - port: 80
      targetPort: 80
      nodePort: 30002
```

Depolama alanı için pv ve pvc yaml dosyaları:

```sh
apiVersion: v1
kind: PersistentVolume
metadata:
  name: my-pv
  labels:
    type: local
spec:
  storageClassName: manual
  capacity:
    storage: 5Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: "/home/ubuntu/myvolume"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-pvc
spec:
  storageClassName: manual
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 4Gi
```

Podları scale edebilmek için Horizontal Pod Autoscaler yaml dosyaları:
web server için:

```sh
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-deploy-hpa
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-deploy
  minReplicas: 1
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 50
```

result server için:

```sh
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: result-service-hpa
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: result-deployment
  minReplicas: 1
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 50
```

> > > Oluşturduğumuz bu deploy kaynaklarını ArgoCd ile deploy edebilmek için bir github reposuna push etmemiz gerekiyor.

> > > Uygulamamız hazır. Uygulamanın çalışıp çalışmadığını kontrol için EC2 konsolda t2.micro bir instance ayağa kaldırıp docker kurarak ve EC2'ya gerekli olacak olan Secret manager'a erişim izni de vererek deneme yapabiliriz.

# 6. Adım:

> > > Terraform'un state dosyalarının güvenli bir şekilde saklanması, sürümlenmesi ve şifrelenmesi için S3 kullanıp, aynı zamanda kilitleme işlemi için DynamoDB table'ını kullanarak çoklu işlem sorunlarını engelliyoruz. Gizlilik, güvenlik, ve geri dönüş yapılabilirlik özellikleri ekliyoruz.

```sh
# backend-setup.tf

provider "aws" {
  region = "us-east-1"
}

# S3 Bucket Oluşturma
resource "aws_s3_bucket" "terraform_state" {
  bucket = "mecit-terraform-state" # Benzersiz bir bucket adı seçin
  force_destroy = true  # terraform destroy dediğimizde bu buckedın silinmesi için. !!DİKKAT!!

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
```
Terraform doyasını uygulamak için;
````sh
terraform init  #providers indirir
````
````sh
terraform plan #oluşcak kaynakları ve varsa hataları gösterir
````
````sh
terraform apply #kodu uygulamaya başlar, kaynaklar oluşur.
````
````sh
terraform destroy #Kaynakları sonlandırmak için.
````

# 7. Adım:

> > > Oluşturacağımız EKS'de kuracağımız Nginx İngress Controller için uygulamamızın Ingress yaml dosyasını oluşturuyoruz. Bu dosya EKS'yi oluşturduğumuz tf dosyası ile aynı dizinde ve ismi tf dosyasında belirtilecek olan "App-İngress.yaml" olmalı:

```sh
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: microservices-ingress
  namespace: default
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
    - http:
        paths:
          - path: "/"
            pathType: Prefix
            backend:
              service:
                name: web-service
                port:
                  number: 80
          - path: "/result"
            pathType: Prefix
            backend:
              service:
                name: result-service
                port:
                  number: 80
```

> > > Oluşturacağımız EKS'de kuracağımız ArgoCd için GitOps iş akışını belirttiğimiz yaml dosyasını oluşturuyoruz. Bu dosya EKS'yi oluşturduğumuz tf dosyası ile aynı dizinde ve ismi tf dosyasında belirtilecek olan "App-Deploy-Argocd.yaml" olmalı:

```sh
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: microservice-eks-rds-argocd
  namespace: argocd  # ArgoCD'nin kurulu olduğu namespace
spec:
  project: default  # ArgoCD projesi (default olarak ayarlanmış)

  source:
    repoURL: "https://github.com/Mecit-tuksoy/Microservice-EKS-RDS-Argocd.git"  # Git deposu
    targetRevision: "main"  # Takip edilecek git dalı, commit ya da tag
    path: "deploy"  # Manifest dosyalarının bulunduğu dizin

  destination:
    server: "https://kubernetes.default.svc"  # Kubernetes cluster'ı (self-managed)
    namespace: default  # Manifest dosyalarının uygulanacağı namespace

  syncPolicy:
    automated: {}  # Otomatik senkronizasyonu etkinleştirme
```

# 8. Adım:

> > > Şimdi AWS'de ayağa kaldıracağımız resourceları belirttiğimiz terraform dosyamızı oluşturmaya başlıyoruz. Bu dosyayı parça parça açıklayarak veriyorum:

```sh
terraform {
  backend "s3" {
    bucket         = "mecit-terraform-state"
    key            = "terraform/state/phonebookdb.tfstate"
    region         = "us-east-1"
    dynamodb_table = "mecit-terraform-state-lock"
    encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}
```

> > > Bu yapılandırmada, Terraform'un remote state dosyasını güvenli bir şekilde S3'te önceden oluşturduğumuz bucked'da saklamasını sağlar ve aynı anda birden fazla Terraform işleminin state dosyasını değiştirmemesi için DynamoDB kullanılarak kilitleme işlemini sağlar.
> > > AWS, Kubernetes, Helm ve Null sağlayıcıları tanımlanarak gerekli altyapı yönetimi gerçekleştirilir. Her sağlayıcı için versiyonlar belirtilmiştir, böylece bu sürümler arasında uyumluluk sağlanır.

```sh

# VPC Configuration
resource "aws_vpc" "eks_vpc" {
  cidr_block           = "172.20.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = "eks-vpc"
  }
}

# Public Subnet
resource "aws_subnet" "public_eks_subnet" {
  count 	    = 2
  vpc_id            = aws_vpc.eks_vpc.id
  cidr_block        = element(["172.20.1.0/24", "172.20.2.0/24"], count.index)
  availability_zone = element(["us-east-1a", "us-east-1b"], count.index)
  map_public_ip_on_launch = true
  tags = {
    "Name" = "eks-public-subnet-${count.index}"
    "kubernetes.io/role/elb" = "1"
  }
  depends_on = [aws_vpc.eks_vpc]
}

variable "eks_cluster_name" {
  default = "my-eks-cluster"
}

# Private Subnet
resource "aws_subnet" "private_eks_subnet" {
  count             = 2
  vpc_id            = aws_vpc.eks_vpc.id
  cidr_block        = element(["172.20.3.0/24", "172.20.4.0/24"], count.index)
  availability_zone = element(["us-east-1a", "us-east-1b"], count.index)
  map_public_ip_on_launch = false
  tags = {
    "Name" = "eks-private-subnet-${count.index}"
    "kubernetes.io/cluster/${var.eks_cluster_name}" = "owned"
    "kubernetes.io/role/internal-elb" = "1"
  }
  depends_on = [
    aws_vpc.eks_vpc
  ]
}

# Internet Gateway
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.eks_vpc.id
  tags = {
    Name = "my-eks-cluster-igw"
  }
  depends_on = [
    aws_vpc.eks_vpc
  ]
}

# Elastic IP for NAT Gateway
resource "aws_eip" "nat_eip" {
  domain = "vpc"
  tags = {
    Name = "eks-nat-eip"
  }
}

# NAT Gateway
resource "aws_nat_gateway" "nat_gw" {
  allocation_id = aws_eip.nat_eip.id
  subnet_id     = aws_subnet.public_eks_subnet[0].id
  tags = {
    Name = "eks-nat-gateway"
  }
  depends_on = [
    aws_eip.nat_eip,
    aws_subnet.public_eks_subnet,
    aws_vpc.eks_vpc
  ]
}

# Public Route Table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.eks_vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
  tags = {
    Name = "eks-public-route-table"
  }
  depends_on = [
    aws_internet_gateway.igw,
    aws_vpc.eks_vpc
  ]
}

# Public Route Table Association
resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = element(aws_subnet.public_eks_subnet[*].id, count.index)
  route_table_id = aws_route_table.public.id
  depends_on = [
    aws_internet_gateway.igw,
    aws_route_table.public,
    aws_subnet.public_eks_subnet,
    aws_vpc.eks_vpc
  ]
}

# Private Route Table
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.eks_vpc.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat_gw.id
  }
  tags = {
    Name = "eks-private-route-table"
  }
  depends_on = [
    aws_eip.nat_eip,
    aws_nat_gateway.nat_gw,
    aws_subnet.public_eks_subnet,
    aws_vpc.eks_vpc
  ]
}

# Private Route Table Association
resource "aws_route_table_association" "private" {
  count = 2  # İki özel subnet için association oluşturuyoruz
  subnet_id      = aws_subnet.private_eks_subnet[count.index].id
  route_table_id = aws_route_table.private.id
  depends_on = [
    aws_eip.nat_eip,
    aws_nat_gateway.nat_gw,
    aws_route_table.private,
    aws_subnet.private_eks_subnet,
    aws_subnet.public_eks_subnet,
    aws_vpc.eks_vpc
  ]
}
```

> > > Bu yapılandırma, AWS'de EKS için uygun bir VPC oluşturur. Public subnet'ler internete doğrudan erişebilirken, private subnet'ler NAT Gateway üzerinden internete erişir. Bu, güvenli ve ölçeklenebilir bir Kubernetes ortamı oluşturmak için gereklidir.

```sh
# Security Groups
resource "aws_security_group" "eks_cluster_sg" {
  name        = "my-eks-cluster-eks-cluster-sg"
  description = "EKS cluster security group"
  vpc_id      = aws_vpc.eks_vpc.id
  ingress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    self            = true
  }
  ingress {
    description = "Allow HTTPS traffic from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = "my-eks-cluster-eks-cluster-sg"
  }
  depends_on = [aws_vpc.eks_vpc]
}

resource "aws_security_group" "eks_node_sg" {
  name        = "my-eks-cluster-eks-node-sg"
  description = "EKS worker node security group"
  vpc_id      = aws_vpc.eks_vpc.id
  ingress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    security_groups = [aws_security_group.eks_cluster_sg.id]
  }
  ingress {
  from_port   = 443
  to_port     = 443
  protocol    = "tcp"
  security_groups = [aws_security_group.eks_cluster_sg.id]
}
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = "my-eks-cluster-eks-node-sg"
  }
  depends_on = [
    aws_vpc.eks_vpc,
    aws_security_group.eks_cluster_sg
  ]
}

resource "aws_security_group" "alb_sg" {
  name        = "alb-sg"
  description = "Security group for ALB"
  vpc_id      = aws_vpc.eks_vpc.id
  ingress {
    description = "Allow HTTPS traffic from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "Allow HTTP traffic from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "Allow HTTPS traffic from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = "alb-sg"
  }
  depends_on = [
    aws_vpc.eks_vpc
  ]
}

resource "aws_security_group" "ec2_sg" {
  name        = "rds-ec2-sg"
  description = "RDS EC2 security group"
  vpc_id      = aws_vpc.eks_vpc.id
  ingress {
    description = "Allow HTTPS traffic from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = "ec2-sg"
  }
  depends_on = [
    aws_vpc.eks_vpc
  ]
}

resource "aws_security_group" "rds_sg" {
  name        = "rds_security_group"
  description = "Allow MySQL access"
  vpc_id      = aws_vpc.eks_vpc.id
  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    security_groups = [
        aws_security_group.eks_cluster_sg.id,
        aws_security_group.eks_node_sg.id,
        aws_security_group.ec2_sg.id
        ]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = "rds_sg"
  }
  depends_on = [
    aws_vpc.eks_vpc,
    aws_security_group.eks_cluster_sg,
    aws_security_group.eks_node_sg
  ]
}
```

> > > Bu Terraform konfigürasyonunda farklı AWS bileşenleri için güvenlik grupları tanımlanmıştır. Her güvenlik grubunun amacı;

- EKS cluster'a gelen ve giden tüm trafiği kontrol etmek.
- EKS worker node'ların cluster ile iletişimini sağlamak.
- Application Load Balancer (ALB) üzerinden gelen HTTP, HTTPS ve SSH trafiğini yönetmek.
- EC2 instance'lara SSH erişimini sağlamak.
- RDS veritabanına EKS ve EC2'den MySQL (3306) trafiğini yönetmek.

```sh

resource "aws_db_subnet_group" "main" {
  name       = "main-db-subnet-group"
  subnet_ids = [
    for subnet in aws_subnet.private_eks_subnet : subnet.id  # Her bir subnet'in ID'sini alıyoruz
  ]
  tags = {
    Name = "main-db-subnet-group"
  }
  depends_on = [
    aws_vpc.eks_vpc,
    aws_subnet.private_eks_subnet
  ]
}

# RDS MySQL 5.7 Instance
resource "aws_db_instance" "mysql" {
  allocated_storage       = 20
  storage_type            = "gp3"
  engine                  = "mysql"
  engine_version          = "8.0.32"  #"5.7.44"
  instance_class          = "db.t3.micro"
  identifier              = "phonebookdb"
  username                = local.credentials.username
  password                = local.credentials.password
  parameter_group_name    = "default.mysql8.0" #"default.mysql5.7"
  db_subnet_group_name    = aws_db_subnet_group.main.id
  vpc_security_group_ids  = [aws_security_group.rds_sg.id]
  publicly_accessible     = false
  skip_final_snapshot     = true  # Final snapshot oluşturulmayacak
  tags = {
    Name = "phonebookdb"
  }
  depends_on = [
    aws_vpc.eks_vpc,
    aws_subnet.private_eks_subnet,
    aws_db_subnet_group.main
  ]
}

# AWS Secrets Manager'dan Credentials Bilgilerini Çekmek için Veri Kaynakları
data "aws_secretsmanager_secret_version" "credentials" {
  secret_id = "prod/mysql/credentials"
}

locals {
  credentials = jsondecode(data.aws_secretsmanager_secret_version.credentials.secret_string)
}

data "aws_ami" "latest_amazon_linux" {
  most_recent = true
  owners = ["137112412989"]
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

# EC2 Instance oluşturma
resource "aws_instance" "my_instance" {
  ami           = data.aws_ami.latest_amazon_linux.id
  instance_type = "t2.micro"
  subnet_id     = aws_subnet.public_eks_subnet[0].id
  security_groups = [aws_security_group.ec2_sg.id]
  tags = {
    Name = "MyEC2Instance"
  }
  key_name = "newkey"
  user_data = <<-EOF
              #!/bin/bash
              yum update -y
              yum install -y mysql
              EOF
  depends_on = [
    aws_security_group.ec2_sg,
    aws_db_instance.mysql]
}

# RDS veritabanını başlatma
resource "null_resource" "initialize_db" {
  depends_on = [
    aws_db_instance.mysql,
    aws_instance.my_instance
    ]
  provisioner "remote-exec" {
    inline = [
      "for i in {1..30}; do mysql -h ${aws_db_instance.mysql.address} -u ${local.credentials.username} -p${local.credentials.password} -e 'CREATE DATABASE IF NOT EXISTS phonebookdb;' && break || echo 'Waiting for database...' && sleep 10; done"
    ]
    connection {
      type        = "ssh"
      host        = aws_instance.my_instance.public_ip
      user        = "ec2-user"
      private_key = file("/home/mecit/.ssh/newkey.pem")
    }
  }
}

resource "null_resource" "cleanup" {
  depends_on = [null_resource.initialize_db]
  provisioner "local-exec" {
    command = "aws ec2 terminate-instances --instance-ids ${aws_instance.my_instance.id} --region us-east-1"
  }
}

# Secrets Manager Secret Version
resource "aws_secretsmanager_secret_version" "rds_endpoint_secret_version" {
  secret_id = "prod/mysql/endpoint"
  secret_string = <<EOF
{
  "host": "${aws_db_instance.mysql.address}"
}
EOF
  depends_on = [aws_db_instance.mysql]
}
```

> > > Bu Terraform konfigürasyonu ile;

- RDS veritabanının sadece private subnet'lerde çalışması sağlanır.
- MySQL 8.0 veritabanı oluşturulur.
- AWS Secrets Manager'da depolanan veritabanı kimlik bilgileri alınır ve kullanılır.
- MySQL istemcisi kurulu bir EC2 instance’ı oluşturulur ve EC2 instance’ı üzerinden RDS veritabanına bağlanarak, phonebookdb adında bir veritabanı oluşturulur. Sonra EC2 instance'ını işlem tamamlandıktan sonra otomatik olarak silinir.
- RDS veritabanı endpoint bilgisini AWS Secrets Manager’da saklanır.

```sh

# IAM Roles and Attachments
resource "aws_iam_role" "eks_role" {
  name = "eks-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
      }
    ]
  })
}
resource "aws_iam_role_policy_attachment" "eks_policy" {
  role       = aws_iam_role.eks_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  depends_on = [
    aws_iam_role.eks_role
  ]
}
resource "aws_iam_role_policy_attachment" "CloudWatch_eks_policy" {
  role       = aws_iam_role.eks_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchFullAccess"
  depends_on = [
    aws_iam_role.eks_role
  ]
}
resource "aws_iam_role_policy_attachment" "AutoScaling_eks_policy" {
  role       = aws_iam_role.eks_role.name
  policy_arn = "arn:aws:iam::aws:policy/AutoScalingFullAccess"
  depends_on = [
    aws_iam_role.eks_role
  ]
}
resource "aws_iam_role_policy_attachment" "Service_eks_policy" {
  role       = aws_iam_role.eks_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSServicePolicy"
  depends_on = [
    aws_iam_role.eks_role
  ]
}
resource "aws_iam_role_policy_attachment" "RDS_eks_policy" {
  role       = aws_iam_role.eks_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonRDSFullAccess"
  depends_on = [
    aws_iam_role.eks_role
  ]
}
resource "aws_iam_role_policy_attachment" "SecretsManager_eks_policy" {
  role       = aws_iam_role.eks_role.name
  policy_arn = "arn:aws:iam::aws:policy/SecretsManagerReadWrite"
  depends_on = [
    aws_iam_role.eks_role
  ]
}
resource "aws_iam_role" "eks_node_group_role" {
  name = "eks-node-group-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}
resource "aws_iam_role_policy_attachment" "eks_node_group_policy" {
  role       = aws_iam_role.eks_node_group_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  depends_on = [
    aws_iam_role.eks_node_group_role
  ]
}
resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  role       = aws_iam_role.eks_node_group_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  depends_on = [
    aws_iam_role.eks_node_group_role
  ]
}
resource "aws_iam_role_policy_attachment" "eks_ecr_policy" {
  role       = aws_iam_role.eks_node_group_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  depends_on = [
    aws_iam_role.eks_node_group_role
  ]
}
resource "aws_iam_role_policy_attachment" "eks_elb_policy" {
  role       = aws_iam_role.eks_node_group_role.name
  policy_arn = "arn:aws:iam::aws:policy/ElasticLoadBalancingFullAccess"
  depends_on = [
    aws_iam_role.eks_node_group_role
  ]
}
resource "aws_iam_role_policy_attachment" "CloudWatch_policy" {
  role       = aws_iam_role.eks_node_group_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchFullAccess"
  depends_on = [
    aws_iam_role.eks_node_group_role
  ]
}
resource "aws_iam_role_policy_attachment" "AutoScaling_policy" {
  role       = aws_iam_role.eks_node_group_role.name
  policy_arn = "arn:aws:iam::aws:policy/AutoScalingFullAccess"
  depends_on = [
    aws_iam_role.eks_node_group_role
  ]
}
resource "aws_iam_role_policy_attachment" "RDS_policy" {
  role       = aws_iam_role.eks_node_group_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonRDSFullAccess"
  depends_on = [
    aws_iam_role.eks_node_group_role
  ]
}
resource "aws_iam_role_policy_attachment" "SecretsManager_policy" {
  role       = aws_iam_role.eks_node_group_role.name
  policy_arn = "arn:aws:iam::aws:policy/SecretsManagerReadWrite"
  depends_on = [
    aws_iam_role.eks_node_group_role
  ]
}
```

> > > Bu Terraform kodu;

- EKS cluster'ının AWS hizmetlerine erişebilmesi için bir rol oluşturur bu role ile;
  1- AmazonEKSClusterPolicy: EKS cluster'ının genel AWS hizmetlerine erişim izni verir.
  2- CloudWatchFullAccess: CloudWatch kullanarak EKS metriklerini ve loglarını izleme yetkisi verir.
  3- AutoScalingFullAccess: EKS cluster'ının Auto Scaling işlemleri yapmasına izin verir.
  4- AmazonEKSServicePolicy: EKS servislerinin AWS kaynaklarına erişim izni sağlar.
  5- AmazonRDSFullAccess: EKS üzerinden RDS veritabanlarına tam erişim sağlar.
  6- SecretsManagerReadWrite: EKS, AWS Secrets Manager'dan şifreleri okuyup yazabilir.

- EKS node'larının (worker node'lar) AWS servislerine erişebilmesi için bir rol oluşturur bu role ile;
  1- AmazonEKSWorkerNodePolicy: EKS node'larının AWS servislerine erişim yetkisi sağlar.
  2- AmazonEKS_CNI_Policy: EKS node'larının ağ yapılandırmalarını yönetmesini sağlar.
  3- AmazonEC2ContainerRegistryReadOnly: Node'ların ECR (Elastic Container Registry) üzerindeki container imajlarına erişmesini sağlar.
  4- ElasticLoadBalancingFullAccess: EKS, Elastic Load Balancers (ELB) ile etkileşim kurabilir.
  5- CloudWatchFullAccess: Node'ların CloudWatch üzerinden metrik ve loglara erişimini sağlar.
  6- AutoScalingFullAccess: Node'ların Auto Scaling işlemlerini gerçekleştirebilmesi için gerekli yetkiyi sağlar.
  7- AmazonRDSFullAccess: Node'ların RDS veritabanlarına tam erişim izni verir.
  8- SecretsManagerReadWrite: Node'ların AWS Secrets Manager'dan şifreleri okuyup yazabilmesini sağlar.

````sh

# EKS Cluster
resource "aws_eks_cluster" "eks_cluster" {
  name     = "my-eks-cluster"
  role_arn = aws_iam_role.eks_role.arn
  vpc_config {
    subnet_ids         = aws_subnet.private_eks_subnet[*].id
    security_group_ids = [aws_security_group.eks_cluster_sg.id]
    endpoint_private_access = true
    endpoint_public_access  = true  #or false 
  }
  enabled_cluster_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler"
  ]
  depends_on = [
    aws_iam_role.eks_role,
    aws_iam_role_policy_attachment.eks_policy,
    aws_security_group.eks_cluster_sg,
    aws_subnet.private_eks_subnet,
    aws_route_table.private,
    aws_vpc.eks_vpc,
    aws_nat_gateway.nat_gw
  ]
}

# EKS Node Group
resource "aws_eks_node_group" "eks_node_group" {
  cluster_name    = aws_eks_cluster.eks_cluster.name
  node_group_name = "my-node-group"
  node_role_arn   = aws_iam_role.eks_node_group_role.arn
  subnet_ids = aws_subnet.private_eks_subnet[*].id
  scaling_config {
    desired_size = 1
    max_size     = 2
    min_size     = 1
  }
  instance_types = ["t3.medium"]
  remote_access {
    ec2_ssh_key = "newkey"  
  }
  update_config {
    max_unavailable = 1
  }
  depends_on = [
    aws_eks_cluster.eks_cluster,
    aws_iam_role_policy_attachment.eks_node_group_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_elb_policy,
    aws_iam_role_policy_attachment.eks_policy,
    aws_iam_role_policy_attachment.eks_ecr_policy,
    aws_eip.nat_eip,
    aws_iam_role.eks_role,
    aws_iam_role.eks_node_group_role,
    aws_nat_gateway.nat_gw,
    aws_security_group.eks_cluster_sg,
    aws_subnet.private_eks_subnet,
    aws_route_table.private,
    aws_vpc.eks_vpc
  ]
}

# Data Source to Retrieve ASG Name Associated with the EKS Node Group
data "aws_autoscaling_groups" "eks_node_asg" {
  filter {
    name   = "tag:eks:nodegroup-name"
    values = [aws_eks_node_group.eks_node_group.node_group_name]
  }
  filter {
    name   = "tag:eks:cluster-name"
    values = [aws_eks_cluster.eks_cluster.name]
  }
}

# Output to Verify Retrieved ASG Names (Optional)
output "eks_node_asg_names" {
  value = data.aws_autoscaling_groups.eks_node_asg.names
}

# Auto Scaling Policy for Scaling Up
resource "aws_autoscaling_policy" "scale_up" {
  name                   = "scale-up"
  autoscaling_group_name = data.aws_autoscaling_groups.eks_node_asg.names[0]
  scaling_adjustment     = 1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 300
  depends_on = [
    aws_eks_node_group.eks_node_group
  ]
}

# (Opsiyonel) Auto Scaling Policy for Scaling Down
resource "aws_autoscaling_policy" "scale_down" {
  name                   = "scale-down"
  autoscaling_group_name = data.aws_autoscaling_groups.eks_node_asg.names[0]
  scaling_adjustment     = -1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 300
  depends_on = [
    aws_eks_node_group.eks_node_group
  ]
}

# CloudWatch Metric Alarm for High CPU Utilization (Scaling Up)
resource "aws_cloudwatch_metric_alarm" "cpu_alarm_high" {
  alarm_name          = "high-cpu-alarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "120"
  statistic           = "Average"
  threshold           = "70"  # CPU kullanım eşiği (%70)
  alarm_actions       = [aws_autoscaling_policy.scale_up.arn]
  dimensions = {
    AutoScalingGroupName = data.aws_autoscaling_groups.eks_node_asg.names[0]
  }
  depends_on = [
    aws_autoscaling_policy.scale_up
  ]
}

#CloudWatch Metric Alarm for Low CPU Utilization (Scaling Down)
resource "aws_cloudwatch_metric_alarm" "cpu_alarm_low" {
  alarm_name          = "low-cpu-alarm"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "120"
  statistic           = "Average"
  threshold           = "30"  
  alarm_actions       = [aws_autoscaling_policy.scale_down.arn]
  dimensions = {
    AutoScalingGroupName = data.aws_autoscaling_groups.eks_node_asg.names[0]
  }
  depends_on = [
    aws_autoscaling_policy.scale_down
  ]
}
````

>>> Bu Terraform yapılandırmasında Amazon EKS (Elastic Kubernetes Service) ve Auto Scaling ile ilgili kaynaklar tanımlanmıştır. 
- Cluster public erişime kapalıdır.
- Node Sayısı Minimum 1, maksimum 2 node çalıştırır.
- EC2 instance'ları t3.medium tipi olacak şekilde ayarlanmıştır.
- SSH anahtarı ile EC2'lara uzaktan erişim sağlanıyor.
- EKS Node Group'a bağlı Auto Scaling Group'un (ASG) adı çekilir ve EC2 instance'ların CPU kullanımına göre otomatik ölçeklendirme yapacak politikalar oluşturuluyor.
- CloudWatch Metric Alarms ile EKS node grubunun CPU kullanımını izleyerek Auto Scaling işlemini tetikler.
CPU kullanımı %70'in üzerine çıkarsa, daha fazla node ekler.
CPU kullanımı %30'un altına düşerse, node sayısını azaltır.
  
````sh

# Data Sources for EKS Cluster
data "aws_eks_cluster" "eks_cluster" {
  name = aws_eks_cluster.eks_cluster.name
}

data "aws_eks_cluster_auth" "eks_cluster" {
  name = aws_eks_cluster.eks_cluster.name
}

provider "kubernetes" {
  host                   = data.aws_eks_cluster.eks_cluster.endpoint
  cluster_ca_certificate = base64decode(data.aws_eks_cluster.eks_cluster.certificate_authority[0].data)
  exec {
    api_version = "client.authentication.k8s.io/v1"  # v1beta1 yerine v1 kullanılıyor
    args        = ["eks", "get-token", "--cluster-name", aws_eks_cluster.eks_cluster.name]
    command     = "aws"
  }
}

provider "helm" {
  kubernetes {
    host                   = data.aws_eks_cluster.eks_cluster.endpoint
    cluster_ca_certificate = base64decode(data.aws_eks_cluster.eks_cluster.certificate_authority[0].data)
    exec {
      api_version = "client.authentication.k8s.io/v1"  # v1beta1 yerine v1 kullanılıyor
      args        = ["eks", "get-token", "--cluster-name", aws_eks_cluster.eks_cluster.name]
      command     = "aws"
    }
  }
}

# Kubernetes Namespaces
resource "kubernetes_namespace" "argocd" {
  metadata {
    name = "argocd"
  }
  depends_on = [aws_eks_node_group.eks_node_group]
}

resource "kubernetes_namespace" "ingress_nginx" {
  metadata {
    name = "ingress-nginx"
  }
  depends_on = [aws_eks_node_group.eks_node_group]
}

# Helm Release for Argo CD
resource "helm_release" "argocd" {
  name       = "argo-cd"
  namespace  = kubernetes_namespace.argocd.metadata[0].name
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  version    = "7.6.8" 
  set {
    name  = "server.service.type"
    value = "LoadBalancer"
  }
  set {
    name  = "configs.repository.credentials"
    value = ""  
  }
  set {
    name  = "controller.service.annotations.service\\.beta\\.kubernetes\\.io/aws-load-balancer-security-groups"
    value = aws_security_group.alb_sg.id
  }
  depends_on = [
    kubernetes_namespace.argocd,
    aws_security_group.alb_sg,
    aws_eks_node_group.eks_node_group
  ]  
}

resource "null_resource" "update_kubeconfig" {
  provisioner "local-exec" {
    command = "aws eks update-kubeconfig --name ${aws_eks_cluster.eks_cluster.name} --region us-east-1"
  }
  depends_on = [aws_eks_cluster.eks_cluster]
}

# Null Resource to Apply Argo CD Manifest
resource "null_resource" "apply_manifest" {
  provisioner "local-exec" {
    command = "kubectl apply -f ./App-Deploy-Argocd.yaml"
  }
  depends_on = [
    helm_release.argocd,
    null_resource.update_kubeconfig
    ]
}

# Helm Release for NGINX Ingress
resource "helm_release" "nginx_ingress" {
  name       = "nginx-ingress"
  repository = "https://kubernetes.github.io/ingress-nginx"
  chart      = "ingress-nginx"
  namespace  = kubernetes_namespace.ingress_nginx.metadata[0].name
  version    = "4.11.2"  
  set {
    name  = "controller.service.type"
    value = "LoadBalancer"
  }
  set {
    name  = "controller.service.annotations.service\\.beta\\.kubernetes\\.io/aws-load-balancer-security-groups"
    value = aws_security_group.alb_sg.id
  }
  set {
    name  = "controller.replicaCount"
    value = 2
  }

  depends_on = [
    kubernetes_namespace.ingress_nginx,
    aws_security_group.alb_sg,
    aws_eks_node_group.eks_node_group
  ]
}

# Null Resource to Apply Ingress Manifest
resource "null_resource" "apply_ingress_manifest" {
  provisioner "local-exec" {
    command = "kubectl apply -f ./App-İngress.yaml"
  }
  
  depends_on = [
    helm_release.nginx_ingress,
    null_resource.update_kubeconfig
    ]
}

# Helm Release for Metrics Server
resource "helm_release" "metrics_server" {
  name       = "metrics-server"
  repository = "https://kubernetes-sigs.github.io/metrics-server/"
  chart      = "metrics-server"
  namespace  = "kube-system"
  version    = "3.12.2" 
  timeout    = 600
  set {
    name  = "hostNetwork.enabled"
    value = "true"
  }
  set_list {
    name  = "args"
    value = ["--kubelet-preferred-address-types=InternalIP","--kubelet-insecure-tls"]
  }
  depends_on = [
    aws_eks_node_group.eks_node_group
  ]
}

# Data Source for NGINX Ingress Load Balancer
data "kubernetes_service" "nginx_ingress_lb" {
  metadata {
    name      = "nginx-ingress-ingress-nginx-controller" 
    namespace = kubernetes_namespace.ingress_nginx.metadata[0].name
  }
  depends_on = [helm_release.nginx_ingress]
}

# Outputs
output "nginx_ingress_lb_hostname" {
  value       = try(data.kubernetes_service.nginx_ingress_lb.status[0].load_balancer[0].ingress[0].hostname, "Hostname not available yet")
  description = "The LoadBalancer Hostname of the NGINX Ingress Controller."
}
````

>>> Bu Terraform kodu, AWS EKS (Elastic Kubernetes Service) üzerinde bir Kubernetes cluster'ı yapılandırarak, çeşitli Kubernetes bileşenlerinin kurulumu ve yapılandırmasını gerçekleştirir. 
- Kubernetes ve Helm sağlayıcıları, EKS cluster'ına bağlanarak kullanabilmek için yapılandırılır. AWS CLI kullanarak eks get-token ile cluster'a erişim sağlanır.
- Argo CD ve NGINX Ingress için Kubernetes namespace'leri oluşturur. Namespace'ler, uygulamaların birbirinden izole çalışmasını sağlar.
- Argo CD ile GitOps yöntemini kullanarak uygulamaların Kubernetes'e otomatik olarak dağıtılmasını sağlamak için Argo CD Helm kullanılarak kurulur.
-  Null Resource ile Cluster ile kubectl komutları aracılığıyla çalışabilmek için AWS CLI kullanarak kubeconfig dosyasını günceller. (EKS cluster'a public erişim olmalı)
-  Null_resource ile Argo CD ve Ingress için gerekli Kubernetes manifest dosyalarını kubectl apply komutu ile cluster'a uygular.
-  Helm ile NGINX Ingress Controller Kurularak dış dünyadan gelen istekleri içerdeki Kubernetes servislerine yönlendirilir. NGINX Controller, public subnet'te bir LoadBalancer ile dışarıya açılır, böylece uygulamalara internetten erişilebilir.
-  Helm ile Metrics Server Kurulur ve cluster'daki pod ve node'ların CPU ve bellek kullanım bilgilerini sağlar, özellikle autoscaling işlemleri için gereklidir.
-   NGINX Ingress LoadBalancer Bilgilerini Alınır ve Output'ta NGINX Ingress Controller'a atanan LoadBalancer'ın hostname bilgisini çıktı olarak verir. Bu hostname, uygulamalara dışarıdan erişim sağlamak için kullanılır.
  

Terraform doyasını uygulamak için;
````sh
terraform init  #providers indirir
````
````sh
terraform plan #oluşcak kaynakları ve varsa hataları gösterir
````
````sh
terraform apply #kodu uygulamaya başlar, kaynaklar oluşur.
````
````sh
terraform destroy #Kaynakları sonlandırmak için.
````
