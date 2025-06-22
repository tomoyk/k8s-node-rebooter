#!/usr/bin/env python3
"""
Kubernetes Node Reboot Script

This script detects NotReady nodes in a Kubernetes cluster and reboots
the corresponding VMs on VMware ESXi hosts.
"""

import json
import logging
import os
import sys
from typing import Dict, List, Optional

import paramiko
from kubernetes import client, config
from tenacity import retry, stop_after_attempt, wait_fixed


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class NodeRebooter:
    """Handles detection and reboot of NotReady Kubernetes nodes."""

    def __init__(self, kubeconfig_path: str, node_vm_map_path: str, ssh_key_path: str):
        """
        Initialize the NodeRebooter.

        Args:
            kubeconfig_path: Path to the kubeconfig file
            node_vm_map_path: Path to the node to VM mapping JSON file
            ssh_key_path: Path to the SSH private key for ESXi access
        """
        self.kubeconfig_path = kubeconfig_path
        self.node_vm_map_path = node_vm_map_path
        self.ssh_key_path = ssh_key_path
        self.node_vm_map = self._load_node_vm_map()

        # Load Kubernetes configuration
        try:
            config.load_kube_config(config_file=kubeconfig_path)
            self.k8s_client = client.CoreV1Api()
            logger.info("Kubernetes client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            raise

    def _load_node_vm_map(self) -> Dict:
        """Load the node to VM mapping from JSON file."""
        try:
            with open(self.node_vm_map_path, "r") as f:
                node_vm_map = json.load(f)
            logger.info(f"Loaded node-VM mapping for {len(node_vm_map)} nodes")
            return node_vm_map
        except Exception as e:
            logger.error(f"Failed to load node-VM mapping: {e}")
            raise

    def get_notready_nodes(self) -> List[str]:
        """
        Get list of NotReady nodes from Kubernetes cluster.

        Returns:
            List of node names that are in NotReady state
        """
        try:
            nodes = self.k8s_client.list_node()
            notready_nodes = []

            for node in nodes.items:
                node_name = node.metadata.name
                conditions = node.status.conditions

                # Check if node is NotReady
                for condition in conditions:
                    if condition.type == "Ready" and condition.status == "False":
                        notready_nodes.append(node_name)
                        logger.info(f"Found NotReady node: {node_name}")
                        break

            logger.info(f"Total NotReady nodes found: {len(notready_nodes)}")
            return notready_nodes

        except Exception as e:
            logger.error(f"Failed to get nodes from Kubernetes: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(10))
    def reboot_vm_on_esxi(self, esxi_host: str, vmid: str) -> bool:
        """
        Reboot a VM on ESXi host using SSH.

        Args:
            esxi_host: ESXi host IP address
            vmid: VM ID to reboot

        Returns:
            True if reboot command was successful
        """
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            # Load private key
            private_key = paramiko.RSAKey.from_private_key_file(self.ssh_key_path)

            # Connect to ESXi host
            logger.info(f"Connecting to ESXi host: {esxi_host}")
            ssh_client.connect(
                hostname=esxi_host, username="root", pkey=private_key, timeout=30
            )

            # Execute reboot command
            command = f"vim-cmd vmsvc/power.reset {vmid}"
            logger.info(f"Executing command on {esxi_host}: {command}")

            stdin, stdout, stderr = ssh_client.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()

            if exit_code == 0:
                logger.info(f"Successfully rebooted VM {vmid} on {esxi_host}")
                return True
            else:
                error_output = stderr.read().decode().strip()
                logger.error(
                    f"Failed to reboot VM {vmid} on {esxi_host}. Exit code: {exit_code}, Error: {error_output}"
                )
                raise Exception(f"VM reboot failed with exit code {exit_code}")

        except Exception as e:
            logger.error(f"Error rebooting VM {vmid} on {esxi_host}: {e}")
            raise
        finally:
            ssh_client.close()

    def reboot_notready_nodes(self, notready_nodes: List[str]) -> None:
        """
        Reboot VMs corresponding to NotReady nodes.

        Args:
            notready_nodes: List of NotReady node names
        """
        rebooted_count = 0

        for node_name in notready_nodes:
            if node_name not in self.node_vm_map:
                logger.warning(f"No VM mapping found for node: {node_name}")
                continue

            vm_info = self.node_vm_map[node_name]
            esxi_host = vm_info["esxi_host"]
            vmid = vm_info["vmid"]

            logger.info(
                f"Attempting to reboot VM for node {node_name} (ESXi: {esxi_host}, VMID: {vmid})"
            )

            try:
                success = self.reboot_vm_on_esxi(esxi_host, vmid)
                if success:
                    rebooted_count += 1
                    logger.info(f"Successfully initiated reboot for node: {node_name}")
                else:
                    logger.error(f"Failed to reboot VM for node: {node_name}")

            except Exception as e:
                logger.error(f"Failed to reboot VM for node {node_name}: {e}")

        logger.info(
            f"Reboot process completed. Successfully rebooted {rebooted_count} out of {len(notready_nodes)} nodes"
        )


def main():
    """Main function to execute the node reboot process."""
    # Configuration paths
    kubeconfig_path = "/kube/config"
    node_vm_map_path = "/config/node_vm_map.json"
    ssh_key_path = "/secrets/id_rsa"

    # Validate required files exist
    required_files = [kubeconfig_path, node_vm_map_path, ssh_key_path]
    for file_path in required_files:
        if not os.path.exists(file_path):
            logger.error(f"Required file not found: {file_path}")
            sys.exit(1)

    try:
        # Initialize NodeRebooter
        rebooter = NodeRebooter(kubeconfig_path, node_vm_map_path, ssh_key_path)

        # Get NotReady nodes
        notready_nodes = rebooter.get_notready_nodes()

        if not notready_nodes:
            logger.info("No NotReady nodes found. Exiting.")
            return

        # Reboot NotReady nodes
        rebooter.reboot_notready_nodes(notready_nodes)

        logger.info("Node reboot process completed successfully")

    except Exception as e:
        logger.error(f"Fatal error during node reboot process: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
