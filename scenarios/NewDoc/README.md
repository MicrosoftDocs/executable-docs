---
Tags:
- cw.Azure
- cw.Azure Linux Escalation
- cw.Azure-Linux-PerformanceAnalysis
- cw.Azure-Linux-PerformanceAnalysis-howto
- cw.Linux
- cw.Virtual Machine
---

[**Tags**](/Tags): [Azure](/Tags/Azure) [Azure Linux Escalation](/Tags/Azure-Linux-Escalation) [Azure-Linux-PerformanceAnalysis](/Tags/Azure%2DLinux%2DPerformanceAnalysis) [Azure-Linux-PerformanceAnalysis-howto](/Tags/Azure%2DLinux%2DPerformanceAnalysis%2Dhowto) [Linux](/Tags/Linux) [Virtual Machine](/Tags/Virtual-Machine) 
 
[[_TOC_]]

# Problem

How to quickly obtain performance metrics from a Linux System.

# Solution

There are several commands that can be used to obtain performance counters on Linux. Commands such as `vmstat` and `uptime`, provide general system metrics such as CPU usage, System Memory, and System load.
Most of the commands are already installed by default with others being readily available in default repositories.
The commands can be separated into:

* CPU
* Memory
* Disk I/O
* Processes

> Note: Some of these commands need to be run as `root` to be able to gather all relevant details.

> Note: Some commands are part of the `sysstat` package which might not be installed by default. The package can be easily installed with `sudo apt install sysstat`, `dnf install sysstat` or `zypper install sysstat`.

```bash
az vm run-command invoke --resource-group "myVMResourceGroup2a481b" --name "myVM2a481b" --command-id RunShellScript --scripts "sudo apt-get update && sudo apt-get install -y sysstat"
```

## CPU

### mpstat

The `mpstat` utility is part of the `sysstat` package, it displays per CPU utilization and averages, this is helpful to quickly identify CPU usage. `mpstat` provides an overview of CPU utilization across the available CPUs, helping identify usage balance and if a single CPU is heavily loaded.

The full command is:

```bash
az vm run-command invoke --resource-group "myVMResourceGroup2a481b" --name "myVM2a481b" --command-id RunShellScript --scripts 'mpstat -P ALL 1 2'
```

The options and arguments are:

* `-P`: Indicates the processor to display statistics, the ALL argument indicates to display statistics for all the online CPUs in the system.
* `1`: The first numeric argument indicates how often to refresh the display in seconds.
* `2`: The second numeric argument indicates how many times the data will refresh.

The number of times the `mpstat` command displays data can be changed by increasing the second numeric argument to accommodate for longer data collection times. Ideally 3 or 5 seconds should suffice, for systems with increased core counts 2 seconds can be used to reduce the amount of data displayed.
From the output:

```output
Linux 5.14.0-362.8.1.el9_3.x86_64 (alma9)       02/21/24        _x86_64_        (8 CPU)

16:55:50     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
16:55:51     all   69.09    0.00   30.16    0.00    0.38    0.38    0.00    0.00    0.00    0.00
16:55:51       0   77.23    0.00   21.78    0.00    0.99    0.00    0.00    0.00    0.00    0.00
16:55:51       1   97.03    0.00    0.99    0.00    0.99    0.99    0.00    0.00    0.00    0.00
16:55:51       2   11.11    0.00   88.89    0.00    0.00    0.00    0.00    0.00    0.00    0.00
16:55:51       3   11.00    0.00   88.00    0.00    0.00    1.00    0.00    0.00    0.00    0.00
16:55:51       4   83.84    0.00   16.16    0.00    0.00    0.00    0.00    0.00    0.00    0.00
16:55:51       5   76.00    0.00   23.00    0.00    1.00    0.00    0.00    0.00    0.00    0.00
16:55:51       6   96.00    0.00    3.00    0.00    0.00    1.00    0.00    0.00    0.00    0.00
16:55:51       7  100.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00
[...]

Average:     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
Average:     all   74.02    0.00   25.52    0.00    0.25    0.21    0.00    0.00    0.00    0.00
Average:       0   63.00    0.00   36.67    0.00    0.33    0.00    0.00    0.00    0.00    0.00
Average:       1   97.33    0.00    1.67    0.00    0.33    0.67    0.00    0.00    0.00    0.00
Average:       2   42.33    0.00   57.33    0.00    0.33    0.00    0.00    0.00    0.00    0.00
Average:       3   34.33    0.00   65.00    0.00    0.33    0.33    0.00    0.00    0.00    0.00
Average:       4   88.63    0.00   11.04    0.00    0.00    0.33    0.00    0.00    0.00    0.00
Average:       5   71.33    0.00   28.33    0.00    0.33    0.00    0.00    0.00    0.00    0.00
Average:       6   95.65    0.00    4.01    0.00    0.00    0.33    0.00    0.00    0.00    0.00
Average:       7   99.67    0.00    0.00    0.00    0.33    0.00    0.00    0.00    0.00    0.00
```

There are a couple of important things to note, the first line displays useful information:

* Kernel and release: `5.14.0-362.8.1.el9_3.x86_64`
* Hostname: `alma9`
* Date: `02/21/24`
* Architecture: `_x86_64_`
* Total amount of CPUs (this will be useful to interpret the output from other commands): `(8 CPU)`

Then the metrics for the CPUs are displayed, to explain each of the columns:

* `Time`: The time the sample was collected
* `CPU`: The CPU numeric identifier, the ALL identifier is an average for all the CPUs.
* `%usr`: The percentage of CPU utilization for user space, normally user applications.
* `%nice`: The percentage of CPU utilization for user space processes with a nice (priority) value.
* `%sys`: The percentage of CPU utilization for kernel space processes.
* `%iowait`: The percentage of CPU time spent idle waiting for outstanding I/O.
* `%irq`: The percentage of CPU time spent serving hardware interrupts.
* `%soft`: The percentage of CPU time spent serving software interrupts.
* `%steal`: The percentage of CPU time spent serving other virtual machines (not applicable to Azure due to no overprovisioning of CPU).
* `%guest`: The percentage of CPU time spent serving virtual CPUs (not applicable to Azure, only applicable to bare metal systems running virtual machines).
* `%gnice`: The percentage of CPU time spent serving virtual CPUs with a nice value (not applicable to Azure, only applicable to bare metal systems running virtual machines).
* `%idle`: The percentage of CPU time spent idle and without waiting for I/O requests.

#### Things to look out for

These are some details to keep in mind when reviewing the output for `mpstat`:
* Verify that all CPUs are properly loaded and not a single CPU is serving all the load. This could indicate a single threaded application.
* Look for a healthy balance between `%usr` and `%sys` as this would indicate more time spent on the actual workload than serving kernel processes.
* Look for `%iowait` percentages as high values could indicate a system that is constantly waiting for I/O requests.
* High `%soft` usage could indicate high network traffic.
