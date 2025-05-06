---
title: Validate the resiliency of the Valkey cluster on Azure Kubernetes Service (AKS) with Locust.
description: In this article, you learn how to test a Valkey cluster on Azure Kubernetes Service (AKS) using Locust.
ms.topic: how-to
ms.custom: azure-kubernetes-service
ms.date: 10/15/2024
author: schaffererin
ms.author: schaffererin
---

# Validate the resiliency of the Valkey cluster on Azure Kubernetes Service (AKS)

This article shows how to validate the resiliency of the Valkey cluster on Azure Kubernetes Service (AKS).

> [!NOTE]
> This article contains references to the term *master*, which is a term that Microsoft no longer uses. When the term is removed from the Valkey software, we’ll remove it from this article.

## Build and run a sample client application for Valkey

The following steps show how to build a sample client application for Valkey and push the Docker image of the application to Azure Container Registry (ACR).

The sample client application uses the [Locust load testing framework](https://docs.locust.io/en/stable/) to simulate a workload on the Valkey cluster.

1. Create the *Dockerfile* and *requirements.txt* and place them in a new directory using the following commands:

    ```bash
    mkdir valkey-client
    cd valkey-client

    cat > Dockerfile <<EOF
    FROM python:3.10-slim-bullseye
    COPY requirements.txt .
    COPY locustfile.py .
    RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt
    EOF

    cat > requirements.txt <<EOF
    valkey
    locust
    EOF
    ```

2. Create the `locustfile.py` file with the following content:

    ```bash
    cat > locustfile.py <<EOF
    import time
    from locust import between, task, User, events,tag, constant_throughput
    from valkey import ValkeyCluster
    from random import randint

    class ValkeyLocust(User):
        wait_time = constant_throughput(50)
        host = "valkey-cluster.valkey.svc.cluster.local"
        def __init__(self, *args, **kwargs):
            super(ValkeyLocust, self).__init__(*args, **kwargs)
            self.client = ValkeyClient(host=self.host)
        def on_stop(self):
            self.client.close()
        @task
        @tag("set")
        def set_value(self):
            self.client.set_value("set_value")
        @task
        @tag("get")
        def get_value(self):
            self.client.get_value("get_value")

    class ValkeyClient(object):
        def __init__(self, host, *args, **kwargs):
            super().__init__(*args, **kwargs)
            with open("/etc/valkey-password/valkey-password-file.conf", "r") as f:
                self.password = f.readlines()[0].split(" ")[1].strip()
            self.host = host
            self.vc = ValkeyCluster(host=self.host,
                                    port=6379,
                                    password=self.password,
                                    username="default",
                                    cluster_error_retry_attempts=0,
                                    socket_timeout=2,
                                    keepalive=1
                                    )

        def set_value(self, key, command='SET'):
            start_time = time.perf_counter()
            try:
                result = self.vc.set(randint(0, 1000), randint(0, 1000))
                if not result:
                    result = ''
                length = len(str(result))
                total_time = (time.perf_counter()- start_time) * 1000
                events.request.fire(
                    request_type=command,
                    name=key,
                    response_time=total_time,
                    response_length=length,
                )
            except Exception as e:
                total_time = (time.perf_counter()- start_time) * 1000
                events.request.fire(
                    request_type=command,
                    name=key,
                    response_time=total_time,
                    response_length=0,
                    exception=e
                )
                result = ''
            return result
        def get_value(self, key, command='GET'):
            start_time = time.perf_counter()
            try:
                result = self.vc.get(randint(0, 1000))
                if not result:
                    result = ''
                length = len(str(result))
                total_time = (time.perf_counter()- start_time) * 1000
                events.request.fire(
                    request_type=command,
                    name=key,
                    response_time=total_time,
                    response_length=length,
                )
            except Exception as e:
                total_time = (time.perf_counter()- start_time) * 1000
                events.request.fire(
                    request_type=command,
                    name=key,
                    response_time=total_time,
                    response_length=0,
                    exception=e
                )
                result = ''
            return result
    EOF
    ```

    This python code implements a Locust User class that connects to the Valkey cluster and performs a *set and get* operation. You can [expand this class to implement more complex operations][writing-a-locustfile].

3. Build the Docker image and upload it to ACR using the [`az acr build`](/cli/azure/acr#az-acr-build) command.

    ```azurecli-interactive
    az acr build --image valkey-client --registry ${MY_ACR_REGISTRY} .
    ```

## Test the Valkey cluster on Azure Kubernetes Service (AKS)

1. Create a `Pod` that uses the Valkey client image built in the previous step using the `kubectl apply` command. The pod spec contains the Secret Store CSI volume with the Valkey password the client uses to connect to the Valkey cluster.

    ```bash
    kubectl apply -f - <<EOF
    ---
    kind: Pod
    apiVersion: v1
    metadata:
      name: valkey-client
      namespace: valkey
    spec:
        affinity:
          nodeAffinity:
            requiredDuringSchedulingIgnoredDuringExecution:
              nodeSelectorTerms:
              - matchExpressions:
                - key: agentpool
                  operator: In
                  values:
                  - nodepool1
        containers:
        - name: valkey-client
          image: ${MY_ACR_REGISTRY}.azurecr.io/valkey-client
          command: ["locust", "--processes", "4"]
          volumeMounts:
            - name: valkey-password
              mountPath: "/etc/valkey-password"
        volumes:
        - name: valkey-password
          csi:
            driver: secrets-store.csi.k8s.io
            readOnly: true
            volumeAttributes:
              secretProviderClass: "valkey-password"
    EOF
    ```

2. Port forward the port 8089 to access the Locust web interface on your local machine using the `kubectl port-forward` command.

    ```bash
     kubectl port-forward -n valkey valkey-client 8089:8089
    ```

3. Access the Locust web interface at `http://localhost:8089` and start the test. You can adjust the number of users and the spawn rate to simulate a workload on the Valkey cluster. The following graph uses 100 users and a 10 spawn rate:

    :::image type="content" source="media/valkey-stateful-workload/locust.png" alt-text="Screenshot of a web page showing the Locust test dashboard.":::


4. Simulate an outage by deleting the `StatefulSet` using the `kubectl delete` command with the [`--cascade=orphan`](https://kubernetes.io/docs/tasks/run-application/delete-stateful-set/) flag. The goal is to be able to delete a single Pod without the StatefulSet immediately recreating the deleted Pod.

    ```bash
    kubectl delete statefulset valkey-masters --cascade=orphan
    ```

5. Delete the `valkey-masters-0` Pod using the `kubectl delete pod` command.

    ```bash
    kubectl delete pod valkey-masters-0
    ```

6. Check the list of Pods using the `kubectl get pods` command.

    ```bash
    kubectl get pods
    ```

    The output should indicate that the Pod `valkey-masters-0` was deleted:

    ```output
    NAME                READY   STATUS    RESTARTS   AGE
    valkey-client       1/1     Running   0          6m34s
    valkey-masters-1    1/1     Running   0          16m
    valkey-masters-2    1/1     Running   0          16m
    valkey-replicas-0   1/1     Running   0          16m
    valkey-replicas-1   1/1     Running   0          16m
    valkey-replicas-2   1/1     Running   0          16m
    ```

7. Get the logs of the `valkey-replicas-0` Pod using the `kubectl logs valkey-replicas-0` command.

    ```bash
    kubectl logs valkey-replicas-0
    ```

    In the output, we observe that the complete event lasts for about 18 seconds:

    ```
    1:S 05 Nov 2024 12:18:53.961 * Connection with primary lost.
    1:S 05 Nov 2024 12:18:53.961 * Caching the disconnected primary state.
    1:S 05 Nov 2024 12:18:53.961 * Reconnecting to PRIMARY 10.224.0.250:6379
    1:S 05 Nov 2024 12:18:53.961 * PRIMARY <-> REPLICA sync started
    1:S 05 Nov 2024 12:18:53.964 # Error condition on socket for SYNC: Connection refused
    1:S 05 Nov 2024 12:18:54.910 * Connecting to PRIMARY 10.224.0.250:6379
    1:S 05 Nov 2024 12:18:54.910 * PRIMARY <-> REPLICA sync started
    1:S 05 Nov 2024 12:18:54.912 # Error condition on socket for SYNC: Connection refused
    1:S 05 Nov 2024 12:18:55.920 * Connecting to PRIMARY 10.224.0.250:6379
    [..CUT..]
    1:S 05 Nov 2024 12:19:10.056 * Connecting to PRIMARY 10.224.0.250:6379
    1:S 05 Nov 2024 12:19:10.057 * PRIMARY <-> REPLICA sync started
    1:S 05 Nov 2024 12:19:10.058 # Error condition on socket for SYNC: Connection refused
    1:S 05 Nov 2024 12:19:10.709 * Node c44d4b682b6fb9b37033d3e30574873545266d67 () reported node 9e7c43890613cc3ad4006a9cdc0b5e5fc5b6d44e     () as not reachable.
    1:S 05 Nov 2024 12:19:10.864 * NODE 9e7c43890613cc3ad4006a9cdc0b5e5fc5b6d44e () possibly failing.
    1:S 05 Nov 2024 12:19:11.066 * 10000 changes in 60 seconds. Saving...
    1:S 05 Nov 2024 12:19:11.068 * Background saving started by pid 29
    1:S 05 Nov 2024 12:19:11.068 * Connecting to PRIMARY 10.224.0.250:6379
    1:S 05 Nov 2024 12:19:11.068 * PRIMARY <-> REPLICA sync started
    1:S 05 Nov 2024 12:19:11.069 # Error condition on socket for SYNC: Connection refused
    29:C 05 Nov 2024 12:19:11.090 * DB saved on disk
    29:C 05 Nov 2024 12:19:11.090 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
    1:S 05 Nov 2024 12:19:11.169 * Background saving terminated with success
    1:S 05 Nov 2024 12:19:11.884 * FAIL message received from ba36d5167ee6016c01296a4a0127716f8edf8290 () about     9e7c43890613cc3ad4006a9cdc0b5e5fc5b6d44e ()
    1:S 05 Nov 2024 12:19:11.884 # Cluster state changed: fail
    1:S 05 Nov 2024 12:19:11.974 * Start of election delayed for 510 milliseconds (rank #0, offset 7225807).
    1:S 05 Nov 2024 12:19:11.976 * Node d43f370a417d299b78bd1983792469fe5c39dcdf () reported node 9e7c43890613cc3ad4006a9cdc0b5e5fc5b6d44e     () as not reachable.
    1:S 05 Nov 2024 12:19:12.076 * Connecting to PRIMARY 10.224.0.250:6379
    1:S 05 Nov 2024 12:19:12.076 * PRIMARY <-> REPLICA sync started
    1:S 05 Nov 2024 12:19:12.076 * Currently unable to failover: Waiting the delay before I can start a new failover.
    1:S 05 Nov 2024 12:19:12.078 # Error condition on socket for SYNC: Connection refused
    1:S 05 Nov 2024 12:19:12.581 * Starting a failover election for epoch 15.
    1:S 05 Nov 2024 12:19:12.616 * Currently unable to failover: Waiting for votes, but majority still not reached.
    1:S 05 Nov 2024 12:19:12.616 * Needed quorum: 2. Number of votes received so far: 1
    1:S 05 Nov 2024 12:19:12.616 * Failover election won: I'm the new primary.
    1:S 05 Nov 2024 12:19:12.616 * configEpoch set to 15 after successful failover
    1:M 05 Nov 2024 12:19:12.616 * Discarding previously cached primary state.
    1:M 05 Nov 2024 12:19:12.616 * Setting secondary replication ID to c0b5b2df8a43b19a4d43d8f8b272a07139e0ca34, valid up to offset:     7225808. New replication ID is 029fcfbae0e3e4a1dccd73066043deba6140c699
    1:M 05 Nov 2024 12:19:12.616 * Cluster state changed: ok
    ```

    During this time window of 18 seconds, we observe that writes to the shard that belongs to the deleted Pod are failing, and the Valkey cluster is electing a new primary. The request latency spikes to 60 ms during this time window.

    :::image type="content" source="media/valkey-stateful-workload/percentile.png" alt-text="Screenshot of a graph showing the 95th percentile of request latencies spiking to 60 ms.":::

    After the new primary is elected, the Valkey cluster continues to serve requests with a latency of around 2 ms.

## Next steps

In this article, you learned how to build a test application with Locust and how to simulate a failure of a Valkey primary Pod. You observed that the Valkey cluster could recover from the failure and continue to serve requests with a short spike in latency.

To learn more about stateful workloads using Azure Kubernetes Service (AKS), see the following articles:

* [Deploy a MongoDB cluster on Azure Kubernetes Service (AKS)](./mongodb-overview.md)
* [Deploy a highly available PostgreSQL database on AKS with Azure CLI](./postgresql-ha-overview.md)


> [!div class="nextstepaction"]
> [Validate Valkey resiliency during an AKS node pool upgrade][upgrade-valkey-aks-nodepool]

## Contributors

*Microsoft maintains this article. The following contributors originally wrote it:*

* Nelly Kiboi | Service Engineer
* Saverio Proto | Principal Customer Experience Engineer

<!-- Internal links -->
[upgrade-valkey-aks-nodepool]: ./upgrade-valkey-aks-nodepool.md

<!-- EXTERNAL LINKS -->
[writing-a-locustfile]: https://docs.locust.io/en/stable/writing-a-locustfile.html

