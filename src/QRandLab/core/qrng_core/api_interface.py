# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""API Interface for web-based quantum random number generators."""

from __future__ import annotations

import threading
import requests
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

from ..observer import Event
from ..types import OperationStatus


class BaseAPIProvider(ABC):
    """Abstract base class for QRNG API providers."""
    
    @abstractmethod
    def fetch_data(self, length: int, **kwargs) -> OperationStatus:
        """Fetch random data from the API provider."""
        raise NotImplementedError("Subclasses must implement fetch_data method")
    
    @abstractmethod
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the API provider."""
        raise NotImplementedError("Subclasses must implement get_provider_info method")


class ANUProvider(BaseAPIProvider):
    """ANU Quantum Random Numbers API provider."""
    
    def __init__(self):
        self.api_url = "https://api.quantumnumbers.anu.edu.au"
        self.max_length = 1024
    
    def fetch_data(self, length: int, data_type: str = "uint8", 
                  block_size: int = 0, api_key: str = "") -> OperationStatus:
        """Fetch data from ANU QRNG API."""
        try:
            # Validate inputs
            if not isinstance(length, int) or length <= 0:
                return OperationStatus(ok=False, message="Length must be a positive integer")
            if length > self.max_length:
                return OperationStatus(ok=False, message=f"Length must be <= {self.max_length}")

            params = {"length": length, "type": data_type}
            if isinstance(block_size, int) and block_size > 0:
                params["size"] = block_size

            headers = {}
            if api_key:
                headers["x-api-key"] = api_key

            response = requests.get(self.api_url, params=params, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return OperationStatus(
                    ok=False, 
                    message=f"HTTP Error {response.status_code}: {response.reason}"
                )
            
            data = response.json()
            if not data.get("success"):
                return OperationStatus(ok=False, message="API returned failure")
            
            fetched_data = data.get("data", [])
            return OperationStatus(
                ok=True,
                message="ANU QRNG data fetched successfully",
                payload={
                    "provider": "anu",
                    "data": fetched_data,
                    "length": len(fetched_data),
                    "data_type": data_type
                }
            )
            
        except requests.RequestException as e:
            return OperationStatus(ok=False, message=f"Request error: {e}")
        except Exception as e:
            return OperationStatus(ok=False, message=f"Unexpected error: {e}")
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get ANU provider information."""
        return {
            "name": "ANU Quantum Random Numbers",
            "url": self.api_url,
            "max_length": self.max_length,
            "data_types": ["uint8", "uint16", "hex16"],
            "requires_key": True,
            "description": "True quantum randomness from photon arrival times"
        }


class RandomOrgProvider(BaseAPIProvider):
    """Random.org API provider."""
    
    def __init__(self):
        self.api_url = "https://api.random.org/json-rpc/2/invoke"
        self.max_length = 10000
    
    def fetch_data(self, length: int, data_type: str = "uint8", 
                  api_key: str = "", **kwargs) -> OperationStatus:
        """Fetch data from Random.org API."""
        try:
            if not api_key:
                return OperationStatus(ok=False, message="Random.org requires an API key")
            
            if not isinstance(length, int) or length <= 0:
                return OperationStatus(ok=False, message="Length must be a positive integer")
            if length > self.max_length:
                return OperationStatus(ok=False, message=f"Length must be <= {self.max_length}")

            # Prepare JSON-RPC request
            if data_type == "uint8":
                method = "generateIntegers"
                params = {
                    "apiKey": api_key,
                    "n": length,
                    "min": 0,
                    "max": 255,
                    "replacement": True
                }
            else:
                return OperationStatus(ok=False, message=f"Unsupported data type: {data_type}")

            payload = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": 1
            }

            response = requests.post(
                self.api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if response.status_code != 200:
                return OperationStatus(
                    ok=False,
                    message=f"HTTP Error {response.status_code}: {response.reason}"
                )
            
            data = response.json()
            if "error" in data:
                return OperationStatus(ok=False, message=f"API error: {data['error']}")
            
            fetched_data = data.get("result", {}).get("random", {}).get("data", [])
            return OperationStatus(
                ok=True,
                message="Random.org data fetched successfully",
                payload={
                    "provider": "random_org",
                    "data": fetched_data,
                    "length": len(fetched_data),
                    "data_type": data_type
                }
            )
            
        except requests.RequestException as e:
            return OperationStatus(ok=False, message=f"Request error: {e}")
        except Exception as e:
            return OperationStatus(ok=False, message=f"Unexpected error: {e}")
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get Random.org provider information."""
        return {
            "name": "Random.org",
            "url": self.api_url,
            "max_length": self.max_length,
            "data_types": ["uint8"],
            "requires_key": True,
            "description": "True randomness from atmospheric noise"
        }


class HotBitsProvider(BaseAPIProvider):
    """HotBits (Fourmilab) API provider."""
    
    def __init__(self):
        self.api_url = "https://www.fourmilab.ch/cgi-bin/uncgi/Hotbits"
        self.max_length = 759
    
    def fetch_data(self, length: int, data_type: str = "uint8", **kwargs) -> OperationStatus:
        """Fetch data from HotBits API."""
        try:
            if not isinstance(length, int) or length <= 0:
                return OperationStatus(ok=False, message="Length must be a positive integer")
            if length > self.max_length:
                return OperationStatus(ok=False, message=f"Length must be <= {self.max_length}")

            # HotBits works in bytes, convert if needed
            if data_type == "uint8":
                num_bytes = length
            else:
                return OperationStatus(ok=False, message=f"Unsupported data type: {data_type}")

            params = {
                "nbytes": num_bytes,
                "fmt": "json"
            }

            response = requests.get(self.api_url, params=params, timeout=30)  # HotBits can be slow
            
            if response.status_code != 200:
                return OperationStatus(
                    ok=False,
                    message=f"HTTP Error {response.status_code}: {response.reason}"
                )
            
            # HotBits returns raw bytes, convert to list of integers
            raw_data = response.content
            fetched_data = list(raw_data[:length])
            
            return OperationStatus(
                ok=True,
                message="HotBits data fetched successfully",
                payload={
                    "provider": "hotbits",
                    "data": fetched_data,
                    "length": len(fetched_data),
                    "data_type": data_type
                }
            )
            
        except requests.RequestException as e:
            return OperationStatus(ok=False, message=f"Request error: {e}")
        except Exception as e:
            return OperationStatus(ok=False, message=f"Unexpected error: {e}")
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get HotBits provider information."""
        return {
            "name": "HotBits (Fourmilab)",
            "url": self.api_url,
            "max_length": self.max_length,
            "data_types": ["uint8"],
            "requires_key": False,
            "description": "True randomness from radioactive decay"
        }


class APIInterface:
    """Interface for API-based quantum random number generators."""

    def __init__(self) -> None:
        self.on_api_data = Event()  # Data ready for upper layers
        self.on_api_error = Event()  # Error occurred
        
        self._api_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Initialize providers
        self.providers = {
            "anu": ANUProvider(),
            "random_org": RandomOrgProvider(),
            "hotbits": HotBitsProvider()
        }

    def fetch_data(self, provider: str, length: int, **kwargs) -> OperationStatus:
        """Fetch random data from specified API provider.
        
        Args:
            provider: Provider name ("anu", "random_org", "hotbits")
            length: Number of random values to fetch
            **kwargs: Provider-specific parameters
            
        Returns:
            OperationStatus indicating success/failure
        """
        if self._api_thread and self._api_thread.is_alive():
            return OperationStatus(ok=False, message="API fetch already in progress")

        if provider not in self.providers:
            return OperationStatus(ok=False, message=f"Unknown provider: {provider}")

        # Clear stop event before starting
        self._stop_event.clear()

        def worker():
            try:
                provider_instance = self.providers[provider]
                result = provider_instance.fetch_data(length, **kwargs)
                
                # Only notify if not stopped
                if not self._stop_event.is_set():
                    if result.ok:
                        self.on_api_data.notify(status=result)
                    else:
                        self.on_api_error.notify(status=result)
                    
            except Exception as e:
                if not self._stop_event.is_set():
                    status = OperationStatus(ok=False, message=f"API fetch error: {e}")
                    self.on_api_error.notify(status=status)

        self._api_thread = threading.Thread(target=worker, daemon=True)
        self._api_thread.start()
        return OperationStatus(ok=True, message=f"{provider} API fetch started")
    
    def stop_fetch(self) -> OperationStatus:
        """Stop current API fetch operation."""
        if not self.is_running():
            return OperationStatus(ok=False, message="No API fetch in progress")
        
        self._stop_event.set()
        return OperationStatus(ok=True, message="API fetch stop requested")

    def get_available_providers(self) -> List[Dict[str, Any]]:
        """Get list of available API providers.
        
        Returns:
            List of provider information dictionaries
        """
        providers_info = []
        for name, provider in self.providers.items():
            info = provider.get_provider_info()
            info["key"] = name
            providers_info.append(info)
        return providers_info

    def add_provider(self, name: str, provider: BaseAPIProvider) -> OperationStatus:
        """Add a custom API provider.
        
        Args:
            name: Provider name/key
            provider: Provider instance implementing BaseAPIProvider
            
        Returns:
            OperationStatus indicating success/failure
        """
        try:
            if name in self.providers:
                return OperationStatus(ok=False, message=f"Provider '{name}' already exists")
            
            if not isinstance(provider, BaseAPIProvider):
                return OperationStatus(ok=False, message="Provider must inherit from BaseAPIProvider")
            
            self.providers[name] = provider
            return OperationStatus(ok=True, message=f"Provider '{name}' added successfully")
            
        except Exception as e:
            return OperationStatus(ok=False, message=f"Error adding provider: {e}")

    def remove_provider(self, name: str) -> OperationStatus:
        """Remove an API provider.
        
        Args:
            name: Provider name/key to remove
            
        Returns:
            OperationStatus indicating success/failure
        """
        try:
            if name not in self.providers:
                return OperationStatus(ok=False, message=f"Provider '{name}' not found")
            
            del self.providers[name]
            return OperationStatus(ok=True, message=f"Provider '{name}' removed successfully")
            
        except Exception as e:
            return OperationStatus(ok=False, message=f"Error removing provider: {e}")

    def is_running(self) -> bool:
        """Check if API fetch is currently running."""
        return self._api_thread is not None and self._api_thread.is_alive()
