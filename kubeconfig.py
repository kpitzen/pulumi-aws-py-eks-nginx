import json

import pulumi
import pulumi_aws as aws


def get_kubeconfig(eks_cluster: aws.eks.Cluster):
    kubeconfig = pulumi.Output.all(
        eks_cluster.endpoint,
        eks_cluster.certificate_authority.apply(lambda x: x.data),
        eks_cluster.name,
    ).apply(
        lambda args: json.dumps(
            {
                "apiVersion": "v1",
                "clusters": [
                    {
                        "cluster": {
                            "server": args[0],
                            "certificate-authority-data": args[1],
                        },
                        "name": "kubernetes",
                    }
                ],
                "contexts": [
                    {"context": {"cluster": "kubernetes", "user": "aws"}, "name": "aws"}
                ],
                "current-context": "aws",
                "kind": "Config",
                "users": [
                    {
                        "name": "aws",
                        "user": {
                            "token": aws.eks.get_cluster_auth(args[2]).token,
                        },
                    },
                ],
            }
        )
    )
    return kubeconfig
