"""Single import point for ORM metadata.

Alembic and the test fixtures import this module so every table is registered on
``Base.metadata``; application code imports the models it needs directly.
"""

from ..modules.catalog.models import Dataset, DatasetResource
from ..modules.history.models import ChangeType, DataChange
from ..modules.indicators.models import (
    Indicator,
    IndicatorObservation,
    ObservationReviewStatus,
)
from ..modules.ingestion.models import (
    IngestionRun,
    IngestionRunStatus,
    IngestionRunType,
    ResourceSnapshot,
    SnapshotKind,
    SnapshotMetadata,
)
from ..modules.jurisdictions.models import Jurisdiction, JurisdictionCode, JurisdictionType
from ..modules.organizations.models import Organization
from ..modules.provenance.models import TransformationRun, TransformationStatus
from ..modules.quality.models import DataQualityCheck, QualityStatus
from ..modules.sources.models import DataSource, SourceType

__all__ = [
    "ChangeType",
    "DataChange",
    "DataQualityCheck",
    "DataSource",
    "Dataset",
    "DatasetResource",
    "Indicator",
    "IndicatorObservation",
    "IngestionRun",
    "IngestionRunStatus",
    "IngestionRunType",
    "Jurisdiction",
    "JurisdictionCode",
    "JurisdictionType",
    "ObservationReviewStatus",
    "Organization",
    "QualityStatus",
    "ResourceSnapshot",
    "SnapshotKind",
    "SnapshotMetadata",
    "SourceType",
    "TransformationRun",
    "TransformationStatus",
]
