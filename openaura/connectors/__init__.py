"""Connector package — adapters from external APIs to typed SignalSets."""

from openaura.connectors.azuredevops import AzureDevOpsConnector
from openaura.connectors.base import Connector, ConnectorError
from openaura.connectors.github import GitHubConnector

__all__ = ["AzureDevOpsConnector", "Connector", "ConnectorError", "GitHubConnector"]
