"""A minimal EKS cluster with deployed k8s service"""

import json

import pulumi
import pulumi_aws as aws
import pulumi_kubernetes as k8s

import kubeconfig
import vpc

app_labels = {"app": "nginx"}

cluster_role = aws.iam.Role(
    "cluster-role",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "eks.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
    ),
)

cluster_policy = aws.iam.RolePolicyAttachment(
    "my-cluster-AmazonEKSClusterPolicy",
    policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
    role=cluster_role.name,
)

resource_controller = aws.iam.RolePolicyAttachment(
    "my-cluster-AmazonEKSVPCResourceController",
    policy_arn="arn:aws:iam::aws:policy/AmazonEKSVPCResourceController",
    role=cluster_role.name,
)

node_group_role = aws.iam.Role(
    "ec2-nodegroup-iam-role",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Principal": {"Service": "ec2.amazonaws.com"},
                    "Effect": "Allow",
                    "Sid": "",
                }
            ],
        }
    ),
)

aws.iam.RolePolicyAttachment(
    "eks-workernode-policy-attachment",
    role=node_group_role.id,
    policy_arn="arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
)


aws.iam.RolePolicyAttachment(
    "eks-cni-policy-attachment",
    role=node_group_role.id,
    policy_arn="arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
)

aws.iam.RolePolicyAttachment(
    "ec2-container-ro-policy-attachment",
    role=node_group_role.id,
    policy_arn="arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
)

my_cluster = aws.eks.Cluster(
    "my-cluster",
    role_arn=cluster_role.arn,
    vpc_config=aws.eks.ClusterVpcConfigArgs(subnet_ids=vpc.subnet_ids),
)

my_node_group = eks_node_group = aws.eks.NodeGroup(
    "eks-node-group",
    cluster_name=my_cluster.name,
    node_group_name="pulumi-eks-nodegroup",
    node_role_arn=node_group_role.arn,
    subnet_ids=vpc.subnet_ids,
    tags={
        "Name": "pulumi-cluster-nodeGroup",
    },
    scaling_config=aws.eks.NodeGroupScalingConfigArgs(
        desired_size=2,
        max_size=2,
        min_size=1,
    ),
)

kubeconfig_value = kubeconfig.get_kubeconfig(my_cluster)

provider = k8s.Provider(
    "k8s-provider",
    args=k8s.ProviderArgs(kubeconfig=kubeconfig_value),
    opts=pulumi.ResourceOptions(depends_on=[my_node_group]),
)

deployment = k8s.apps.v1.Deployment(
    "nginx",
    spec=k8s.apps.v1.DeploymentSpecArgs(
        selector=k8s.meta.v1.LabelSelectorArgs(match_labels=app_labels),
        replicas=1,
        template=k8s.core.v1.PodTemplateSpecArgs(
            metadata=k8s.meta.v1.ObjectMetaArgs(labels=app_labels),
            spec=k8s.core.v1.PodSpecArgs(
                containers=[
                    k8s.core.v1.ContainerArgs(
                        name="web-server",
                        image="nginx",
                        ports=[k8s.core.v1.ContainerPortArgs(container_port=80)],
                    )
                ]
            ),
        ),
    ),
    opts=pulumi.ResourceOptions(provider=provider),
)

service = k8s.core.v1.Service(
    "app-service",
    metadata=k8s.meta.v1.ObjectMetaArgs(labels=app_labels),
    spec=k8s.core.v1.ServiceSpecArgs(
        ports=[k8s.core.v1.ServicePortArgs(port=80, target_port=80)],
        selector=app_labels,
        type="LoadBalancer",
    ),
    opts=pulumi.ResourceOptions(provider=provider, depends_on=[deployment]),
)

pulumi.export(
    "service-endpoint",
    service.status.apply(lambda status: status.load_balancer.ingress[0].hostname),
)
