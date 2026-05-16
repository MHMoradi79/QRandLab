# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any, List, Dict
import uuid


class FileExt(str, Enum):
    """Supported file extensions for input files."""
    BIN = ".bin"
    DAT = ".dat"
    TXT = ".txt"


class FileType(str, Enum):
    """Supported file types for data interpretation."""
    BINARY = "binary"
    STRING01 = "string01"
    HEX = "hex"
    UINT8 = "uint8"
    UINT16 = "uint16"
    UINT32 = "uint32"
    UINT64 = "uint64"


@dataclass
class FileItem:
    """Metadata for a single file in multi-file handling."""
    id: str = ""
    file_path: str = ""
    file_dir: str = ""
    file_name: str = ""
    file_ext: Optional[FileExt] = None
    file_type: Optional[FileType] = None
    file_size: Optional[int] = None
    
    def __post_init__(self):
        """Generate unique ID if not provided."""
        if not self.id:
            self.id = str(uuid.uuid4())[:8]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for easy serialization."""
        return {
            'id': self.id,
            'file_path': self.file_path,
            'file_dir': self.file_dir,
            'file_name': self.file_name,
            'file_ext': self.file_ext.value if self.file_ext else None,
            'file_type': self.file_type.value if self.file_type else None,
            'file_size': self.file_size
        }


@dataclass
class InputFileMeta:
    """Mutable metadata container for an imported input file used across cores.
    
    Note: This is kept for backward compatibility with other tabs.
    For multi-file operations, use FileItem and file_items list.
    """
    file_path: str = ""
    file_dir: str = ""
    file_name: str = ""
    file_ext: Optional[FileExt] = None
    file_type: Optional[FileType] = None
    file_size: Optional[int] = None
    
    # Multi-file storage
    file_items: List[FileItem] = field(default_factory=list)
    
    def get_file_by_id(self, file_id: str) -> Optional[FileItem]:
        """Get a file item by its ID."""
        for item in self.file_items:
            if item.id == file_id:
                return item
        return None
    
    def get_file_item(self, file_id: str) -> Optional[FileItem]:
        """Alias for get_file_by_id for compatibility."""
        return self.get_file_by_id(file_id)
    
    def add_file_item(self, item: FileItem) -> None:
        """Add a file item to the collection."""
        self.file_items.append(item)
    
    def remove_file_item(self, file_id: str) -> bool:
        """Remove a file item by ID. Returns True if removed."""
        for i, item in enumerate(self.file_items):
            if item.id == file_id:
                self.file_items.pop(i)
                return True
        return False
    
    def clear_file_items(self) -> None:
        """Clear all file items."""
        self.file_items.clear()
    
    def get_file_count(self) -> int:
        """Get number of files loaded."""
        return len(self.file_items)


@dataclass
class ReadSampleResult:
    """Result of reading a data sample from a file."""
    title: str
    data: bytes  # Raw bytes; GUI handles formatting


@dataclass
class OperationStatus:
    """Status of an operation, including success and payload."""
    ok: bool
    message: Optional[str] = None
    payload: Optional[Any] = None
