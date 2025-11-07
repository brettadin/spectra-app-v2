"""Service layer for the Spectra application."""

from .spectrum import Spectrum
from .units_service import UnitError, UnitsService
from .provenance_service import ProvenanceService
from .data_ingest_service import DataIngestService
from .overlay_service import OverlayService
from .math_service import MathService
from .reference_library import ReferenceLibrary
from .store import LocalStore
from .remote_data_service import RemoteDataService, RemoteRecord, RemoteDownloadResult, LocalSample
from .line_shapes import LineShapeModel, LineShapeOutcome
from .knowledge_log_service import KnowledgeLogEntry, KnowledgeLogService
from .calibration_service import CalibrationService, CalibrationConfig
from .quality_flags import QualityFlags

__all__ = [
    "Spectrum",
    "UnitError",
    "UnitsService",
    "ProvenanceService",
    "DataIngestService",
    "OverlayService",
    "MathService",
    "ReferenceLibrary",
    "LocalStore",
    "RemoteDataService",
    "RemoteRecord",
    "RemoteDownloadResult",
    "LocalSample",
    "LineShapeModel",
    "LineShapeOutcome",
    "KnowledgeLogEntry",
    "KnowledgeLogService",
    "CalibrationService",
    "CalibrationConfig",
    "QualityFlags",
]
