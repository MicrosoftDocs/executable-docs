---
title: Comprehensive Guide to Using Inspektor Gadget in Kubernetes
description: This Exec Doc provides a detailed walkthrough of a shell script that demonstrates various operations with the Inspektor Gadget in a Kubernetes environment. It explains each functional block, how the gadget plugin is installed, deployed, and used to run examples, export metrics, and verify configurations.
ms.topic: article
ms.date: 03/19/2025
author: yourgithubusername
ms.author: yourmsalias
ms.custom: innovation-engine, kubernetes, gadget, monitoring
---

# Detailed Walkthrough: Inspektor Gadget Shell Script

This document provides a step-by-step explanation of the provided shell script. The script demonstrates several operations related to the Inspektor Gadget in a Kubernetes environment. Each section below explains the purpose and the functionality of the code blocks that follow. The commands remain unchanged; only the documentation around them has been added for clarity.

---

## Connecting to Your AKS Cluster

Before running any commands, ensure that your local environment is connected to the desired AKS (Azure Kubernetes Service) cluster. Use the following command to retrieve the cluster credentials and configure `kubectl` to interact with the cluster:

```bash
# Retrieve AKS cluster credentials:
az aks get-credentials --resource-group "myAKSResourceGroupabcf37" --name "myAKSClusterabcf37"
```

After executing this command, `kubectl` will be configured to communicate with the specified AKS cluster.

---

## Viewing AKS Cluster Nodes

In this section, the script lists the nodes of the current AKS (Azure Kubernetes Service) cluster using the Kubernetes CLI (`kubectl`). This allows you to verify that your cluster is up and running and view the status of the nodes.

```bash
# Show AKS cluster:

kubectl get nodes
```

After executing this block, the output will display the current nodes in the cluster along with their status, roles, and version information.

---

## Installing the Inspektor Gadget Plugin

This section installs the Inspektor Gadget plugin using `kubectl krew`. The gadget plugin extends kubectl with additional functionalities, enabling more effective monitoring and tracing within the cluster.

```bash
# Install kubectl plugin:

kubectl krew install gadget
```

Once installed, the gadget plugin is available for subsequent commands in the script.

---

## Verifying Gadget Plugin Version

Here, the script verifies the version and server status of the gadget plugin. It checks that the plugin is correctly installed and provides details about its client and server versions. The expected output is a client version (e.g., vX.Y.Z) and a note that the server version is not available.

```bash
# Verify version and server status:

kubectl gadget version
# Expected output:
# Client version: vX.Y.Z
# Server version: not available
```

This output helps determine that the gadget plugin is operational on your local client. You may compare the shown version with the expected output.

---

## Deploying Inspektor Gadget and Re-Verification

In this section, the script deploys the Inspektor Gadget in the Kubernetes environment. The command includes options to enable the OpenTelemetry (OTEL) metrics listener on the specified address (0.0.0.0:2223). After deploying, the version command is run again to verify that the gadget deployment is correctly configured, even though the server version remains "not available".

```bash
# Deploy Inspektor Gadget:

kubectl gadget deploy --otel-metrics-listen --otel-metrics-listen-address 0.0.0.0:2223

# Verify version and server status:

kubectl gadget version
# Expected output:
# Client version: vX.Y.Z
# Server version: not available
```

This deployment sets up the gadget to collect the required metrics, and the follow-up version check confirms that the plugin is still active.

---

## Demonstrating Gadget Usage with trace_exec

This section illustrates different methods to run the gadget plugin using the `trace_exec` example. The commands include:

1. Running the gadget with a specific trace_exec version.
2. Creating a test pod running Ubuntu in an interactive session, which is automatically removed after exit.
3. Running the gadget with JSON formatted output.
4. Running the gadget with filtering to display only processes with the command matching "bash".

These examples show various ways to leverage the gadget for tracing executions in the cluster.

```bash
# Run simple example with trace_exec with a 10-second timeout to prevent indefinite execution:
timeout 5s kubectl gadget run trace_exec || true

kubectl delete pod demo-pod 

# Create a background pod that will generate events for us to trace:
kubectl run demo-pod --image=ubuntu -- /bin/bash -c "for i in {1..11}; do echo Running commands...; ls -la /; sleep 1; done"

# Wait briefly for the pod to start generating events
sleep 5

# Run gadget with JSON output and timeout
timeout 5s kubectl gadget run trace_exec --output jsonpretty || true

# Run gadget with filtering and timeout
timeout 5s kubectl gadget run trace_exec --all-namespaces --filter proc.comm=bash || echo "Attachment timed out, continuing with demo"
```

Each command demonstrates a different facet of the gadget's capabilities, from initiating traces to filtering outputs based on process names.

---

## Creating Metrics Configuration for Alerting

In this part of the script, a metrics configuration file is edited. The file (alert-bad-process.yaml) is intended to define rules to generate a metric based on certain events in the cluster. The metric, in this context, is used to track shell executions.

```bash
# Generate a metric based on these events:

cat alert-bad-process.yaml
```

---

## Exporting Metrics and Managing Gadget Lifecycle

This section deploys the gadget manifest using the YAML file created in the previous section. The command includes several annotations to instruct the gadget to collect metrics. The process is detached so that it runs in the background. Subsequently, the script lists the running gadget instances.

```bash
# Clean up any existing instance of the same name
kubectl gadget delete alert-bad-process 

# Run gadget manifest to export metrics:
kubectl gadget run -f alert-bad-process.yaml --annotate exec:metrics.collect=true,exec:metrics.implicit-counter.name=shell_executions,exec.k8s.namespace:metrics.type=key,exec.k8s.podname:metrics.type=key,exec.k8s.containername:metrics.type=key --detach
```

These commands ensure that metrics are being collected as defined in the YAML manifest and verify that the gadget is running correctly in headless mode.

---

## Verifying Prometheus Configuration for Metrics Collection

This section checks the managed Prometheus configuration to ensure that it is set up to scrape metrics from the OTEL listener endpoint exposed on each Inspektor Gadget pod. The first command retrieves the relevant configmap, and the second command displays its full YAML definition with a pager for detailed inspection. Review the output to confirm that the configuration contains the expected annotation for pod-based scraping related to the gadget.

```bash
# Configure managed Prometheus to collect data from the OTEL listener endpoint we expose on each IG pod?
# Documentation: https://learn.microsoft.com/en-us/azure/azure-monitor/containers/prometheus-metrics-scrape-configuration?tabs=CRDConfig%2CCRDScrapeConfig%2CConfigFileScrapeConfigBasicAuth%2CConfigFileScrapeConfigTLSAuth#configmaps

kubectl get configmaps -n kube-system ama-metrics-settings-configmap

# It should contain: pod-annotation-based-scraping: podannotationnamespaceregex = "gadget"
kubectl get configmaps -n kube-system ama-metrics-settings-configmap -o yaml | grep -A 5 "pod-annotation-based-scraping"
```

---

## Monitoring, Alerting, and Cleanup

In the final part of the script, the focus shifts to monitoring and alerting:

1. It provides guidance for viewing the `shell_executions_total` metric in the Grafana dashboard.
2. It suggests creating a Prometheus group alert with a rule that triggers when `shell_executions_total` exceeds 0.
3. Finally, the script undeploys the Inspektor Gadget to clean up resources.

```bash
# Show shell_executions_total metric in Grafana dashboard: shell_executions_total
# Documentation: https://learn.microsoft.com/en-us/azure/managed-grafana/overview

# Create a prometheus group alert with the rule "shell_executions_total > 0"
# Documentation: https://learn.microsoft.com/en-us/azure/azure-monitor/essentials/prometheus-rule-groups

# Undeploy IG
kubectl gadget undeploy
```

These steps ensure that your metrics are visually accessible via Grafana and that alerts are configured for proactive monitoring. The final undeploy command removes the deployed gadget from the cluster, wrapping up the execution workflow.