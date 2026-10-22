data "aws_ssm_parameter" "al2023" {
  count = var.enable_compute && var.ami_id == "" ? 1 : 0
  name  = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}
locals {
  selected_ami = var.ami_id != "" ? var.ami_id : (var.enable_compute ? data.aws_ssm_parameter.al2023[0].value : "")
}
resource "aws_iam_role" "ec2_ssm" {
  count       = var.enable_compute ? 1 : 0
  name_prefix = "finops-ssm-"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}
resource "aws_iam_role_policy" "app_read_only" {
  count = var.enable_compute ? 1 : 0
  name  = "finops-inventory-metrics"
  role  = aws_iam_role.ec2_ssm[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ec2:DescribeInstances", "ec2:DescribeVolumes", "ec2:DescribeSnapshots", "ec2:DescribeAddresses", "cloudwatch:GetMetricStatistics", "cloudwatch:GetMetricData"]
      Resource = "*"
    }]
  })
}
resource "aws_iam_role_policy_attachment" "ssm" {
  count      = var.enable_compute ? 1 : 0
  role       = aws_iam_role.ec2_ssm[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
resource "aws_iam_instance_profile" "ec2" {
  count       = var.enable_compute ? 1 : 0
  name_prefix = "finops-ec2-"
  role        = aws_iam_role.ec2_ssm[0].name
}
resource "aws_iam_role" "data_ssm" {
  count       = var.enable_compute ? 1 : 0
  name_prefix = "finops-data-ssm-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "data_ssm" {
  count      = var.enable_compute ? 1 : 0
  role       = aws_iam_role.data_ssm[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "data" {
  count       = var.enable_compute ? 1 : 0
  name_prefix = "finops-data-"
  role        = aws_iam_role.data_ssm[0].name
}

resource "aws_instance" "app" {
  count                       = var.enable_compute ? 1 : 0
  ami                         = local.selected_ami
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.app[0].id
  vpc_security_group_ids      = [aws_security_group.app[0].id]
  iam_instance_profile        = aws_iam_instance_profile.ec2[0].name
  associate_public_ip_address = false
  metadata_options { http_tokens = "required" }
  root_block_device {
    volume_size = var.root_volume_gb
    volume_type = "gp3"
    encrypted   = true
  }
  lifecycle {
    precondition {
      condition     = var.enable_network && var.enable_nat
      error_message = "Private EC2 requires network and NAT for SSM, OS packages and Docker image downloads in this lab design."
    }
  }
  tags = { Name = "finops-app", Role = "app" }
}
resource "aws_instance" "data" {
  count                       = var.enable_compute ? 1 : 0
  ami                         = local.selected_ami
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.data[0].id
  vpc_security_group_ids      = [aws_security_group.data[0].id]
  iam_instance_profile        = aws_iam_instance_profile.data[0].name
  associate_public_ip_address = false
  metadata_options { http_tokens = "required" }
  root_block_device {
    volume_size = var.root_volume_gb
    volume_type = "gp3"
    encrypted   = true
  }
  lifecycle {
    precondition {
      condition     = var.enable_network && var.enable_nat
      error_message = "Private EC2 requires network and NAT in this lab design."
    }
  }
  tags = { Name = "finops-data", Role = "data" }
}
resource "aws_ebs_volume" "postgres" {
  count             = var.enable_compute ? 1 : 0
  availability_zone = aws_subnet.data[0].availability_zone
  size              = var.data_volume_gb
  type              = "gp3"
  encrypted         = true
  tags              = { Name = "finops-postgres-data" }
}
resource "aws_volume_attachment" "postgres" {
  count                          = var.enable_compute ? 1 : 0
  device_name                    = "/dev/sdf"
  volume_id                      = aws_ebs_volume.postgres[0].id
  instance_id                    = aws_instance.data[0].id
  stop_instance_before_detaching = true
}
