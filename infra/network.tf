resource "aws_vpc" "finops" {
  count                = var.enable_network ? 1 : 0
  cidr_block           = "10.20.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = { Name = "finops-vpc" }
}
resource "aws_subnet" "public_a" {
  count                   = var.enable_network ? 1 : 0
  vpc_id                  = aws_vpc.finops[0].id
  cidr_block              = "10.20.1.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = false
  tags                    = { Name = "finops-public-a" }
}
resource "aws_subnet" "public_b" {
  count                   = var.enable_network ? 1 : 0
  vpc_id                  = aws_vpc.finops[0].id
  cidr_block              = "10.20.2.0/24"
  availability_zone       = "${var.aws_region}b"
  map_public_ip_on_launch = false
  tags                    = { Name = "finops-public-b" }
}
resource "aws_subnet" "app" {
  count             = var.enable_network ? 1 : 0
  vpc_id            = aws_vpc.finops[0].id
  cidr_block        = "10.20.11.0/24"
  availability_zone = "${var.aws_region}a"
  tags              = { Name = "finops-private-app" }
}
resource "aws_subnet" "data" {
  count             = var.enable_network ? 1 : 0
  vpc_id            = aws_vpc.finops[0].id
  cidr_block        = "10.20.21.0/24"
  availability_zone = "${var.aws_region}a"
  tags              = { Name = "finops-private-data" }
}
resource "aws_internet_gateway" "igw" {
  count  = var.enable_network ? 1 : 0
  vpc_id = aws_vpc.finops[0].id
  tags   = { Name = "finops-igw" }
}
resource "aws_route_table" "public" {
  count  = var.enable_network ? 1 : 0
  vpc_id = aws_vpc.finops[0].id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw[0].id
  }
  tags = { Name = "finops-public-rt" }
}
resource "aws_route_table_association" "public_a" {
  count          = var.enable_network ? 1 : 0
  subnet_id      = aws_subnet.public_a[0].id
  route_table_id = aws_route_table.public[0].id
}
resource "aws_route_table_association" "public_b" {
  count          = var.enable_network ? 1 : 0
  subnet_id      = aws_subnet.public_b[0].id
  route_table_id = aws_route_table.public[0].id
}
resource "aws_eip" "nat" {
  count      = var.enable_network && var.enable_nat ? 1 : 0
  domain     = "vpc"
  depends_on = [aws_internet_gateway.igw]
  tags       = { Name = "finops-nat-eip" }
}
resource "aws_nat_gateway" "nat" {
  count         = var.enable_network && var.enable_nat ? 1 : 0
  subnet_id     = aws_subnet.public_a[0].id
  allocation_id = aws_eip.nat[0].id
  tags          = { Name = "finops-nat" }
}
resource "aws_route_table" "private" {
  count  = var.enable_network ? 1 : 0
  vpc_id = aws_vpc.finops[0].id
  tags   = { Name = "finops-private-rt" }
}
resource "aws_route" "private_egress" {
  count                  = var.enable_network && var.enable_nat ? 1 : 0
  route_table_id         = aws_route_table.private[0].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.nat[0].id
}
resource "aws_route_table_association" "app" {
  count          = var.enable_network ? 1 : 0
  subnet_id      = aws_subnet.app[0].id
  route_table_id = aws_route_table.private[0].id
}
resource "aws_route_table_association" "data" {
  count          = var.enable_network ? 1 : 0
  subnet_id      = aws_subnet.data[0].id
  route_table_id = aws_route_table.private[0].id
}
