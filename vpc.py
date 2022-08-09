import pulumi_aws as aws

vpc = aws.ec2.Vpc(
    "eks-vpc",
    cidr_block="10.100.0.0/16",
    instance_tenancy="default",
    enable_dns_hostnames=True,
    enable_dns_support=True,
    tags={
        "Name": "pulumi-eks-vpc",
    },
)

igw = aws.ec2.InternetGateway(
    "vpc-ig",
    vpc_id=vpc.id,
    tags={
        "Name": "pulumi-vpc-ig",
    },
)

eks_route_table = aws.ec2.RouteTable(
    "vpc-route-table",
    vpc_id=vpc.id,
    routes=[
        aws.ec2.RouteTableRouteArgs(
            cidr_block="0.0.0.0/0",
            gateway_id=igw.id,
        )
    ],
    tags={
        "Name": "pulumi-vpc-rt",
    },
)

zones = aws.get_availability_zones(
    exclude_names=["us-east-1e"]
)  # for some reason this AZ doesn't have capacity right now
subnet_ids = []

for zone in zones.names:
    vpc_subnet = aws.ec2.Subnet(
        f"vpc-subnet-{zone}",
        assign_ipv6_address_on_creation=False,
        vpc_id=vpc.id,
        map_public_ip_on_launch=True,
        cidr_block=f"10.100.{len(subnet_ids)}.0/24",
        availability_zone=zone,
        tags={
            "Name": f"pulumi-sn-{zone}",
        },
    )
    aws.ec2.RouteTableAssociation(
        f"vpc-route-table-assoc-{zone}",
        route_table_id=eks_route_table.id,
        subnet_id=vpc_subnet.id,
    )
    subnet_ids.append(vpc_subnet.id)

## Security Group

eks_security_group = aws.ec2.SecurityGroup(
    "eks-cluster-sg",
    vpc_id=vpc.id,
    description="Allow all HTTP(s) traffic to EKS Cluster",
    tags={
        "Name": "pulumi-cluster-sg",
    },
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            cidr_blocks=["0.0.0.0/0"],
            from_port=443,
            to_port=443,
            protocol="tcp",
            description="Allow pods to communicate with the cluster API Server.",
        ),
        aws.ec2.SecurityGroupIngressArgs(
            cidr_blocks=["0.0.0.0/0"],
            from_port=80,
            to_port=80,
            protocol="tcp",
            description="Allow internet access to pods",
        ),
    ],
)
