"""Dataset grouping and organization service.

Supports automatic categorization of datasets by source type, manual group management,
and persistence of group configurations.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import uuid

from .spectrum import Spectrum


class GroupType(Enum):
    """Category types for automatic grouping."""
    UPLOADED = "uploaded"          # Locally imported files
    REMOTE = "remote"              # Remote/online data sources
    SPECTRAL_LINES = "spectral_lines"  # Reference spectral lines
    DERIVED = "derived"            # Results of math operations
    CUSTOM = "custom"              # User-created custom groups


@dataclass(frozen=True)
class DatasetGroup:
    """Represents a group of related datasets.
    
    Attributes:
        id: Unique identifier for this group
        name: Display name (e.g., "Aurora Spectrometer", "Remote MAST Data")
        group_type: Categorization type for auto-grouping
        color: Hex color code for UI representation (optional)
        parent_group_id: ID of parent group for hierarchical grouping (optional)
        is_expanded: Whether group is expanded in tree view (default True)
        created_at: Timestamp of group creation
        metadata: Additional metadata (description, tags, etc.)
    """
    id: str
    name: str
    group_type: GroupType
    color: Optional[str] = None
    parent_group_id: Optional[str] = None
    is_expanded: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "id": self.id,
            "name": self.name,
            "group_type": self.group_type.value,
            "color": self.color,
            "parent_group_id": self.parent_group_id,
            "is_expanded": self.is_expanded,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DatasetGroup:
        """Reconstruct from JSON dict."""
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            group_type=GroupType(data.get("group_type", "custom")),
            color=data.get("color"),
            parent_group_id=data.get("parent_group_id"),
            is_expanded=bool(data.get("is_expanded", True)),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class GroupAssignment:
    """Tracks assignment of a spectrum to a group.
    
    Attributes:
        spectrum_id: UUID of the spectrum
        group_id: UUID of the assigned group
        assigned_at: Timestamp of assignment
    """
    spectrum_id: str
    group_id: str
    assigned_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "spectrum_id": self.spectrum_id,
            "group_id": self.group_id,
            "assigned_at": self.assigned_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GroupAssignment:
        return cls(
            spectrum_id=str(data.get("spectrum_id", "")),
            group_id=str(data.get("group_id", "")),
            assigned_at=datetime.fromisoformat(data["assigned_at"]) if "assigned_at" in data else datetime.now(),
        )


class DatasetGroupService:
    """Manages dataset grouping, auto-categorization, and persistence.
    
    Provides:
    - Create/read/update/delete groups
    - Auto-categorize datasets by source type
    - Persist group configuration to JSON
    - Move datasets between groups
    - Query datasets within groups
    """
    
    # Default groups created on initialization
    DEFAULT_GROUPS = [
        (GroupType.UPLOADED, "Uploaded Data", "#7A3E2F"),
        (GroupType.REMOTE, "Remote Data", "#2F6B4F"),
        # Note: SPECTRAL_LINES group type exists but is not auto-created
        # (NIST lines are handled separately via line collections, not as datasets)
    ]
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize the grouping service.
        
        Args:
            storage_dir: Directory for persisting group configuration (optional)
        """
        self.storage_dir = storage_dir
        self.config_file = storage_dir / "dataset_groups.json" if storage_dir else None
        
        # In-memory state
        self._groups: Dict[str, DatasetGroup] = {}
        self._assignments: Dict[str, str] = {}  # spectrum_id -> group_id
        
        # Create default groups
        self._init_default_groups()
        
        # Load persisted state if available
        if self.config_file and self.config_file.exists():
            self._load_config()
    
    def _init_default_groups(self) -> None:
        """Create default groups."""
        for group_type, name, color in self.DEFAULT_GROUPS:
            group = DatasetGroup(
                id=str(uuid.uuid4()),
                name=name,
                group_type=group_type,
                color=color,
            )
            self._groups[group.id] = group
    
    def get_default_group(self, group_type: GroupType) -> Optional[DatasetGroup]:
        """Get the default group for a given type."""
        for group in self._groups.values():
            if group.group_type == group_type and not group.parent_group_id:
                return group
        return None
    
    def create_group(self, name: str, group_type: GroupType = GroupType.CUSTOM, 
                    color: Optional[str] = None, parent_group_id: Optional[str] = None) -> str:
        """Create a new group.
        
        Args:
            name: Display name
            group_type: Category type (default CUSTOM)
            color: Hex color code (optional)
            parent_group_id: Parent group ID for hierarchical grouping (optional)
        
        Returns:
            New group ID
        """
        group_id = str(uuid.uuid4())
        group = DatasetGroup(
            id=group_id,
            name=name,
            group_type=group_type,
            color=color,
            parent_group_id=parent_group_id,
        )
        self._groups[group_id] = group
        self._save_config()
        return group_id
    
    def get_group(self, group_id: str) -> Optional[DatasetGroup]:
        """Get a group by ID."""
        return self._groups.get(group_id)
    
    def list_groups(self, group_type: Optional[GroupType] = None, 
                   parent_group_id: Optional[str] = None) -> List[DatasetGroup]:
        """List all groups, optionally filtered by type or parent.
        
        Args:
            group_type: Filter by group type (optional)
            parent_group_id: Filter by parent group (optional)
        
        Returns:
            List of matching groups
        """
        groups = list(self._groups.values())
        
        if group_type is not None:
            groups = [g for g in groups if g.group_type == group_type]
        
        if parent_group_id is not None:
            groups = [g for g in groups if g.parent_group_id == parent_group_id]
        
        # Sort by name for consistent ordering
        return sorted(groups, key=lambda g: g.name.lower())
    
    def update_group(self, group_id: str, name: Optional[str] = None, 
                    color: Optional[str] = None, is_expanded: Optional[bool] = None) -> bool:
        """Update group properties.
        
        Args:
            group_id: ID of group to update
            name: New display name (optional)
            color: New hex color (optional)
            is_expanded: New expanded state (optional)
        
        Returns:
            True if successful, False if group not found
        """
        group = self._groups.get(group_id)
        if group is None:
            return False
        
        # Use dataclass replace to create updated version
        updates = {}
        if name is not None:
            updates["name"] = name
        if color is not None:
            updates["color"] = color
        if is_expanded is not None:
            updates["is_expanded"] = is_expanded
        
        self._groups[group_id] = replace(group, **updates)
        self._save_config()
        return True
    
    def delete_group(self, group_id: str, move_datasets_to: Optional[str] = None) -> bool:
        """Delete a group and optionally move its datasets.
        
        Args:
            group_id: ID of group to delete
            move_datasets_to: ID of target group (optional). If not provided,
                            datasets are moved to a default group by type.
        
        Returns:
            True if successful, False if group not found
        """
        if group_id not in self._groups:
            return False
        
        # Find datasets in this group
        dataset_ids = [sid for sid, gid in self._assignments.items() if gid == group_id]
        
        # Move datasets
        if dataset_ids:
            if move_datasets_to:
                # Move to specified group
                for spec_id in dataset_ids:
                    self._assignments[spec_id] = move_datasets_to
            else:
                # Move to a default group by type
                group = self._groups[group_id]
                default = self.get_default_group(group.group_type)
                if default:
                    for spec_id in dataset_ids:
                        self._assignments[spec_id] = default.id
        
        # Delete the group
        del self._groups[group_id]
        self._save_config()
        return True
    
    def assign_to_group(self, spectrum_or_id: Spectrum | str, target_group_id: Optional[str] = None) -> str:
        """Assign a spectrum to a group.

        Auto-categorizes if target_group_id not provided based on spectrum metadata.

        Args:
            spectrum_or_id: The spectrum object OR spectrum ID string to assign
            target_group_id: Explicit target group ID (optional)

        Returns:
            The group ID the spectrum was assigned to
        """
        # Get spectrum ID - accept both Spectrum objects and string IDs
        if isinstance(spectrum_or_id, str):
            spectrum_id = spectrum_or_id
            spectrum = None  # We don't have the full object
        else:
            spectrum_id = spectrum_or_id.id
            spectrum = spectrum_or_id

        if target_group_id:
            # Explicit assignment
            self._assignments[spectrum_id] = target_group_id
            self._save_config()
            return target_group_id
        
        # Auto-categorize based on metadata (only if we have the full spectrum object)
        if spectrum:
            group_type = self._infer_group_type(spectrum)
            default_group = self.get_default_group(group_type)

            if default_group:
                self._assignments[spectrum_id] = default_group.id
                self._save_config()
                return default_group.id

        # Fallback to first available group
        groups = list(self._groups.values())
        if groups:
            self._assignments[spectrum_id] = groups[0].id
            self._save_config()
            return groups[0].id

        return ""
    
    def _infer_group_type(self, spectrum: Spectrum) -> GroupType:
        """Infer group type from spectrum metadata.
        
        Returns:
            GroupType.REMOTE if spectrum has remote metadata
            GroupType.DERIVED if spectrum is result of math operation
            GroupType.UPLOADED otherwise
        """
        if not isinstance(spectrum.metadata, dict):
            return GroupType.UPLOADED
        
        # Check for remote data indicators
        cache_record = spectrum.metadata.get("cache_record", {})
        if isinstance(cache_record, dict):
            source = cache_record.get("source", {})
            if isinstance(source, dict):
                remote = source.get("remote", {})
                if isinstance(remote, dict) and remote:
                    return GroupType.REMOTE
        
        # Check for derived data indicators
        if spectrum.parents:  # Has parent spectra
            return GroupType.DERIVED
        
        # Check metadata hints
        if spectrum.metadata.get("is_derived"):
            return GroupType.DERIVED
        
        return GroupType.UPLOADED
    
    def move_dataset(self, spectrum_id: str, target_group_id: str) -> bool:
        """Move a dataset to a different group.
        
        Args:
            spectrum_id: ID of spectrum to move
            target_group_id: ID of target group
        
        Returns:
            True if successful
        """
        if target_group_id not in self._groups:
            return False
        
        self._assignments[spectrum_id] = target_group_id
        self._save_config()
        return True
    
    def get_group_for_dataset(self, spectrum_id: str) -> Optional[DatasetGroup]:
        """Get the group a dataset is assigned to.
        
        Args:
            spectrum_id: ID of the spectrum
        
        Returns:
            The assigned group, or None if not assigned
        """
        group_id = self._assignments.get(spectrum_id)
        if group_id:
            return self._groups.get(group_id)
        return None
    
    def get_datasets_in_group(self, group_id: str) -> List[str]:
        """Get list of spectrum IDs in a group.
        
        Args:
            group_id: ID of the group
        
        Returns:
            List of spectrum IDs
        """
        return [
            spec_id for spec_id, gid in self._assignments.items()
            if gid == group_id
        ]
    
    def get_dataset_count_by_group(self) -> Dict[str, int]:
        """Get count of datasets in each group.
        
        Returns:
            Dict mapping group_id -> dataset_count
        """
        counts: Dict[str, int] = {}
        for group_id in self._groups.keys():
            counts[group_id] = len(self.get_datasets_in_group(group_id))
        return counts
    
    def clear_assignments(self) -> None:
        """Clear all dataset assignments (useful when clearing all datasets)."""
        self._assignments.clear()
        self._save_config()
    
    def _save_config(self) -> None:
        """Persist configuration to JSON."""
        if not self.config_file:
            return
        
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            config = {
                "groups": {gid: g.to_dict() for gid, g in self._groups.items()},
                "assignments": self._assignments,
                "version": "1.0",
                "saved_at": datetime.now().isoformat(),
            }
            
            with self.config_file.open("w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception:
            # Non-fatal: grouping without persistence still works
            pass
    
    def _load_config(self) -> None:
        """Load configuration from JSON."""
        if not self.config_file or not self.config_file.exists():
            return
        
        try:
            with self.config_file.open("r", encoding="utf-8") as f:
                config = json.load(f)
            
            # Load groups (overwriting defaults)
            self._groups.clear()
            for group_id, gdata in config.get("groups", {}).items():
                try:
                    group = DatasetGroup.from_dict(gdata)
                    self._groups[group.id] = group
                except Exception:
                    continue
            
            # Load assignments
            self._assignments = dict(config.get("assignments", {}))
        except Exception:
            # On error, keep defaults
            pass
