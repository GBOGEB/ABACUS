lsq"""
DMAIC V3 - Docker Infrastructure Manager
Manages Docker containers, ports, and service lifecycle

ITERATION 4 - CDCII/CICD Integration
Version: 3.3.0
Date: 2025-01-26
Purpose: Docker orchestration for DMAIC V3 services
"""

import docker
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ServiceType(Enum):
    """Types of services in DMAIC V3 infrastructure"""
    LISTENING = "listening"              # Always open, listening for requests
    MONITORING = "monitoring"            # Always open, monitoring system health
    QUALITY_ASSURANCE = "qa"             # Always open, quality checks
    DEBUGGING = "debugging"              # On-demand, debugging support
    BACKGROUND_CHECKS = "background"     # Slow background processes
    RECURSIVE_HOOKS = "recursive"        # Recursive pipeline hooks
    REPORTING = "reporting"              # Report generation
    RECONCILING = "reconciling"          # Data reconciliation
    HOUSEKEEPING = "housekeeping"        # Maintenance tasks
    TURN_BASED = "turn_based"            # Turn-based execution


@dataclass
class ServiceConfig:
    """Configuration for a DMAIC service"""
    name: str
    service_type: ServiceType
    image: str
    ports: Dict[str, int]  # {internal_port: external_port}
    environment: Dict[str, str]
    volumes: Dict[str, Dict[str, str]]
    always_running: bool
    restart_policy: str = "unless-stopped"
    health_check: Optional[Dict] = None


class PortManager:
    """
    Manages port allocation for DMAIC V3 services
    
    Port Ranges:
    - 8000-8099: API services (listening)
    - 8100-8199: Monitoring services
    - 8200-8299: Quality assurance services
    - 8300-8399: Debugging services
    - 8400-8499: Background services
    - 8500-8599: Reporting services
    - 8600-8699: Housekeeping services
    """
    
    PORT_RANGES = {
        ServiceType.LISTENING: (8000, 8099),
        ServiceType.MONITORING: (8100, 8199),
        ServiceType.QUALITY_ASSURANCE: (8200, 8299),
        ServiceType.DEBUGGING: (8300, 8399),
        ServiceType.BACKGROUND_CHECKS: (8400, 8499),
        ServiceType.REPORTING: (8500, 8599),
        ServiceType.HOUSEKEEPING: (8600, 8699),
        ServiceType.RECURSIVE_HOOKS: (8700, 8799),
        ServiceType.RECONCILING: (8800, 8899),
        ServiceType.TURN_BASED: (8900, 8999)
    }
    
    def __init__(self):
        self.allocated_ports: Dict[str, int] = {}
        self.port_usage: Dict[int, str] = {}
    
    def allocate_port(self, service_name: str, service_type: ServiceType) -> int:
        """Allocate a port for a service"""
        if service_name in self.allocated_ports:
            return self.allocated_ports[service_name]
        
        start, end = self.PORT_RANGES[service_type]
        for port in range(start, end + 1):
            if port not in self.port_usage:
                self.allocated_ports[service_name] = port
                self.port_usage[port] = service_name
                return port
        
        raise RuntimeError(f"No available ports for service type {service_type}")
    
    def release_port(self, service_name: str):
        """Release a port allocation"""
        if service_name in self.allocated_ports:
            port = self.allocated_ports[service_name]
            del self.allocated_ports[service_name]
            del self.port_usage[port]
    
    def get_port(self, service_name: str) -> Optional[int]:
        """Get allocated port for a service"""
        return self.allocated_ports.get(service_name)


class DockerInfrastructureManager:
    """
    Manages Docker infrastructure for DMAIC V3
    
    Responsibilities:
    - Container lifecycle management
    - Port allocation and management
    - Service health monitoring
    - Resource cleanup
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        try:
            self.client = docker.from_env()
            self.docker_available = True
        except Exception as e:
            self.logger.warning(f"Docker not available: {e}")
            self.docker_available = False
            self.client = None
        
        self.port_manager = PortManager()
        self.services: Dict[str, ServiceConfig] = {}
        self.containers: Dict[str, docker.models.containers.Container] = {}
    
    def register_service(self, config: ServiceConfig):
        """Register a service configuration"""
        self.services[config.name] = config
        
        # Allocate ports
        for internal_port, external_port in config.ports.items():
            if external_port == 0:  # Auto-allocate
                external_port = self.port_manager.allocate_port(
                    f"{config.name}:{internal_port}",
                    config.service_type
                )
                config.ports[internal_port] = external_port
    
    def start_service(self, service_name: str) -> bool:
        """Start a Docker service"""
        if not self.docker_available:
            self.logger.warning("Docker not available, cannot start service")
            return False
        
        if service_name not in self.services:
            self.logger.error(f"Service {service_name} not registered")
            return False
        
        config = self.services[service_name]
        
        try:
            # Check if container already exists
            existing = self.client.containers.list(
                all=True,
                filters={"name": config.name}
            )
            
            if existing:
                container = existing[0]
                if container.status != "running":
                    container.start()
                self.containers[service_name] = container
                self.logger.info(f"Started existing container: {service_name}")
                return True
            
            # Create new container
            port_bindings = {
                f"{internal}/tcp": external
                for internal, external in config.ports.items()
            }
            
            container = self.client.containers.run(
                config.image,
                name=config.name,
                ports=port_bindings,
                environment=config.environment,
                volumes=config.volumes,
                detach=True,
                restart_policy={"Name": config.restart_policy}
            )
            
            self.containers[service_name] = container
            self.logger.info(f"Started new container: {service_name}")
            
            # Wait for health check
            if config.health_check:
                self._wait_for_health(container, config.health_check)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start service {service_name}: {e}")
            return False
    
    def stop_service(self, service_name: str, remove: bool = False):
        """Stop a Docker service"""
        if service_name not in self.containers:
            return
        
        try:
            container = self.containers[service_name]
            container.stop()
            
            if remove:
                container.remove()
                del self.containers[service_name]
            
            self.logger.info(f"Stopped service: {service_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to stop service {service_name}: {e}")
    
    def get_service_status(self, service_name: str) -> Optional[str]:
        """Get status of a service"""
        if service_name not in self.containers:
            return None
        
        try:
            container = self.containers[service_name]
            container.reload()
            return container.status
        except Exception as e:
            self.logger.error(f"Failed to get status for {service_name}: {e}")
            return None
    
    def get_service_logs(self, service_name: str, tail: int = 100) -> str:
        """Get logs from a service"""
        if service_name not in self.containers:
            return ""
        
        try:
            container = self.containers[service_name]
            return container.logs(tail=tail).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Failed to get logs for {service_name}: {e}")
            return ""
    
    def cleanup_all(self):
        """Stop and remove all managed containers"""
        for service_name in list(self.containers.keys()):
            self.stop_service(service_name, remove=True)
        
        self.containers.clear()
        self.logger.info("Cleaned up all containers")
    
    def _wait_for_health(self, container, health_check: Dict, timeout: int = 30):
        """Wait for container to become healthy"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            container.reload()
            
            if container.status == "running":
                # Check health if specified
                if "test" in health_check:
                    health = container.attrs.get("State", {}).get("Health", {})
                    if health.get("Status") == "healthy":
                        return True
                else:
                    return True
            
            time.sleep(1)
        
        raise TimeoutError(f"Container {container.name} did not become healthy")


# Predefined service configurations
DMAIC_SERVICES = {
    "dmaic_api": ServiceConfig(
        name="dmaic_api",
        service_type=ServiceType.LISTENING,
        image="dmaic_v3:latest",
        ports={"8000": 0},  # Auto-allocate
        environment={"DMAIC_MODE": "api"},
        volumes={},
        always_running=True
    ),
    "dmaic_monitor": ServiceConfig(
        name="dmaic_monitor",
        service_type=ServiceType.MONITORING,
        image="dmaic_v3:latest",
        ports={"8100": 0},
        environment={"DMAIC_MODE": "monitor"},
        volumes={},
        always_running=True
    ),
    "dmaic_qa": ServiceConfig(
        name="dmaic_qa",
        service_type=ServiceType.QUALITY_ASSURANCE,
        image="dmaic_v3:latest",
        ports={"8200": 0},
        environment={"DMAIC_MODE": "qa"},
        volumes={},
        always_running=True
    ),
    "dmaic_debugger": ServiceConfig(
        name="dmaic_debugger",
        service_type=ServiceType.DEBUGGING,
        image="dmaic_v3:latest",
        ports={"8300": 0},
        environment={"DMAIC_MODE": "debug"},
        volumes={},
        always_running=False
    ),
    "dmaic_background": ServiceConfig(
        name="dmaic_background",
        service_type=ServiceType.BACKGROUND_CHECKS,
        image="dmaic_v3:latest",
        ports={"8400": 0},
        environment={"DMAIC_MODE": "background"},
        volumes={},
        always_running=True
    ),
    "dmaic_reporter": ServiceConfig(
        name="dmaic_reporter",
        service_type=ServiceType.REPORTING,
        image="dmaic_v3:latest",
        ports={"8500": 0},
        environment={"DMAIC_MODE": "reporting"},
        volumes={},
        always_running=False
    ),
    "dmaic_reconciler": ServiceConfig(
        name="dmaic_reconciler",
        service_type=ServiceType.RECONCILING,
        image="dmaic_v3:latest",
        ports={"8800": 0},
        environment={"DMAIC_MODE": "reconcile"},
        volumes={},
        always_running=True
    ),
    "dmaic_housekeeping": ServiceConfig(
        name="dmaic_housekeeping",
        service_type=ServiceType.HOUSEKEEPING,
        image="dmaic_v3:latest",
        ports={"8600": 0},
        environment={"DMAIC_MODE": "housekeeping"},
        volumes={},
        always_running=True
    )
}


def create_infrastructure_manager() -> DockerInfrastructureManager:
    """Factory function to create infrastructure manager"""
    manager = DockerInfrastructureManager()
    
    # Register all predefined services
    for service_config in DMAIC_SERVICES.values():
        manager.register_service(service_config)
    
    return manager
