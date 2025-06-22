# Kubernetes Node Reboot Script

A Python script that detects NotReady nodes in a Kubernetes cluster from outside the cluster and automatically reboots the corresponding VMs on VMware ESXi hosts.

## Overview

This script provides the following functionality:

- Monitor node status in a Kubernetes cluster
- Detect nodes in NotReady state
- Force reboot corresponding VMs on VMware ESXi hosts via SSH
- Retry functionality using tenacity (maximum 3 attempts, 10-second intervals)

## Requirements

- Python 3.8+
- Kubernetes Python client
- Paramiko (for SSH connections)
- Tenacity (for retry functionality)

## File Structure

```
k8s_node_rebooter/
├── restart_notready.py      # Main script
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker image definition
├── config/
│   └── node_vm_map.json    # Node-VM mapping configuration
├── k8s/
│   ├── cronjob.yaml        # CronJob manifest
│   └── configmap.yaml      # ConfigMap manifest
└── README.md               # This file
```

## Configuration

### 1. Node-VM Mapping Configuration

Define the mapping between node names and ESXi hosts/VMIDs in `config/node_vm_map.json`:

```json
{
  "worker-node1": {
    "esxi_host": "192.168.1.101",
    "vmid": "42"
  },
  "worker-node2": {
    "esxi_host": "192.168.1.102",
    "vmid": "43"
  }
}
```

### 2. Required Files

The following files are required when running the script:

- `/kube/config` - Kubernetes cluster kubeconfig
- `/config/node_vm_map.json` - Node-VM mapping configuration
- `/secrets/id_rsa` - SSH private key for ESXi hosts

## Usage

### Local Execution

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Place required files:
```bash
# Place kubeconfig
cp your-kubeconfig /kube/config

# Place node-VM mapping configuration
cp config/node_vm_map.json /config/

# Place SSH private key
cp your-ssh-key /secrets/id_rsa
chmod 400 /secrets/id_rsa
```

3. Run the script:
```bash
python3 restart_notready.py
```

### Docker Execution

1. Build Docker image:
```bash
docker build -t node-rebooter .
```

2. Run container:
```bash
docker run -v /path/to/kubeconfig:/kube/config \
           -v /path/to/node_vm_map.json:/config/node_vm_map.json \
           -v /path/to/ssh-key:/secrets/id_rsa \
           node-rebooter
```

### Kubernetes CronJob Execution

1. Create required Kubernetes resources:

```bash
# Create ConfigMap
kubectl apply -f k8s/configmap.yaml

# Create Secrets (kubeconfig and SSH key)
kubectl create secret generic kubeconfig-secret \
  --from-file=config=/path/to/your-kubeconfig

kubectl create secret generic esxi-ssh-key \
  --from-file=id_rsa=/path/to/your-ssh-key

# Deploy CronJob
kubectl apply -f k8s/cronjob.yaml
```

2. Verify CronJob operation:
```bash
kubectl get cronjobs
kubectl get jobs
kubectl logs job/node-rebooter-<timestamp>
```

## Log Output

The script outputs logs to stdout in the following format:

```
2024-01-01 12:00:00,000 - INFO - Kubernetes client initialized successfully
2024-01-01 12:00:00,100 - INFO - Loaded node-VM mapping for 3 nodes
2024-01-01 12:00:00,200 - INFO - Found NotReady node: worker-node1
2024-01-01 12:00:00,300 - INFO - Total NotReady nodes found: 1
2024-01-01 12:00:00,400 - INFO - Attempting to reboot VM for node worker-node1 (ESXi: 192.168.1.101, VMID: 42)
2024-01-01 12:00:00,500 - INFO - Connecting to ESXi host: 192.168.1.101
2024-01-01 12:00:00,600 - INFO - Executing command on 192.168.1.101: vim-cmd vmsvc/power.reset 42
2024-01-01 12:00:00,700 - INFO - Successfully rebooted VM 42 on 192.168.1.101
2024-01-01 12:00:00,800 - INFO - Successfully initiated reboot for node: worker-node1
2024-01-01 12:00:00,900 - INFO - Reboot process completed. Successfully rebooted 1 out of 1 nodes
```

## Security Considerations

- Protect SSH private keys with appropriate permissions (400)
- Protect kubeconfig files with appropriate permissions
- Consider using more secure authentication methods in production environments

## Troubleshooting

### Common Issues

1. **SSH Connection Errors**
   - Verify ESXi host IP address and SSH key are correct
   - Ensure SSH is enabled on ESXi hosts

2. **Kubernetes Connection Errors**
   - Verify kubeconfig file is correct
   - Check network connectivity to the cluster

3. **VMID Not Found**
   - Verify node-VM mapping configuration is correct
   - Ensure VMID exists on ESXi host

### Debugging

To view detailed logs:

```bash
kubectl logs job/node-rebooter-<timestamp> -f
```

## Features

### Retry Mechanism
- Uses tenacity library for robust retry logic
- Maximum 3 attempts with 10-second intervals
- Handles temporary network issues and SSH connection failures

### Error Handling
- Comprehensive error handling for all operations
- Detailed error messages for troubleshooting
- Graceful failure handling

### Monitoring
- Real-time node status monitoring
- Detailed logging of all operations
- Success/failure statistics

## Architecture

The script follows a modular design:

1. **NodeRebooter Class**: Main orchestrator for the reboot process
2. **Kubernetes Client**: Handles cluster communication
3. **SSH Client**: Manages ESXi host connections
4. **Configuration Manager**: Handles node-VM mapping

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License. 