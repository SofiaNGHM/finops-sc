resource "aws_security_group" "app" {
  count       = var.enable_network ? 1 : 0
  name_prefix = "finops-app-"
  description = "APP: no public inbound; outbound for installation and SSM"
  vpc_id      = aws_vpc.finops[0].id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "finops-app-sg" }
}
resource "aws_security_group" "data" {
  count       = var.enable_network ? 1 : 0
  name_prefix = "finops-data-"
  description = "DATA: PostgreSQL only from APP SG"
  vpc_id      = aws_vpc.finops[0].id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app[0].id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "finops-data-sg" }
}
