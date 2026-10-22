output "vpc_id" { value = try(aws_vpc.finops[0].id, null) }
output "app_instance_id" { value = try(aws_instance.app[0].id, null) }
output "data_instance_id" { value = try(aws_instance.data[0].id, null) }
output "postgres_ebs_id" { value = try(aws_ebs_volume.postgres[0].id, null) }
output "nat_gateway_id" { value = try(aws_nat_gateway.nat[0].id, null) }
output "app_private_ip" { value = try(aws_instance.app[0].private_ip, null) }
output "data_private_ip" { value = try(aws_instance.data[0].private_ip, null) }
