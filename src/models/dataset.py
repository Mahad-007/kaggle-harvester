"""
Dataset data models with Pydantic validation.
Follows Single Responsibility Principle: Only defines data structures.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class DatasetFile(BaseModel):
    """Model for individual files within a dataset."""
    name: str
    size: int = Field(..., ge=0, description="File size in bytes")
    creation_date: Optional[datetime] = None

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class Dataset(BaseModel):
    """
    Model for dataset with metadata and ingestion tracking.
    Supports multiple platforms: Kaggle and Hugging Face.
    Provides type safety and validation for dataset information.
    """
    platform: str = Field(default="kaggle", description="Source platform: kaggle or huggingface")
    dataset_ref: str = Field(..., description="Dataset reference: username/dataset-name")
    title: str
    subtitle: Optional[str] = None
    creator_name: str
    creator_url: str
    total_bytes: int = Field(..., ge=0, description="Total dataset size in bytes")
    url: str
    last_updated: datetime
    download_count: int = Field(default=0, ge=0)
    vote_count: int = Field(default=0, ge=0)
    usability_rating: Optional[float] = Field(default=None, ge=0, le=1)
    license_name: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    files: List[DatasetFile] = Field(default_factory=list)

    # Ingestion-specific fields
    ingestion_timestamp: Optional[datetime] = None
    ingestion_status: Optional[str] = Field(
        default=None,
        description="Status: pending, downloading, completed, failed"
    )
    local_path: Optional[str] = None
    error_message: Optional[str] = None

    @field_validator('dataset_ref')
    @classmethod
    def validate_dataset_ref(cls, v: str) -> str:
        """Validate dataset reference format."""
        if '/' not in v:
            raise ValueError("Dataset reference must be in format 'username/dataset-name'")
        parts = v.split('/')
        if len(parts) != 2:
            raise ValueError("Dataset reference must contain exactly one '/'")
        if not all(parts):
            raise ValueError("Username and dataset name cannot be empty")
        return v

    @field_validator('creator_url')
    @classmethod
    def validate_creator_url(cls, v: str) -> str:
        """Normalize creator URL - if it's just a username, convert to full URL."""
        if not v:
            return "https://www.kaggle.com"
        if not v.startswith(('http://', 'https://')):
            # It's just a username, convert to full URL
            return f"https://www.kaggle.com/{v}"
        return v

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Normalize dataset URL."""
        if not v:
            return ""
        if not v.startswith(('http://', 'https://')):
            return f"https://www.kaggle.com/datasets/{v}"
        return v

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

    def to_dict(self) -> dict:
        """
        Convert model to dictionary with proper datetime serialization.

        Returns:
            Dictionary representation of the dataset
        """
        return self.model_dump(mode='json')

    @classmethod
    def from_kaggle_api(cls, api_dataset) -> "Dataset":
        """
        Create Dataset instance from Kaggle API response.

        Args:
            api_dataset: Dataset object from Kaggle API

        Returns:
            Dataset instance
        """
        # Extract files information if available
        files = []
        if hasattr(api_dataset, 'files') and api_dataset.files:
            for f in api_dataset.files:
                files.append(DatasetFile(
                    name=f.get('name', ''),
                    size=f.get('totalBytes', 0),
                    creation_date=f.get('creationDate')
                ))

        # Extract tags - they might be Tag objects or strings
        tags = []
        if hasattr(api_dataset, 'tags') and api_dataset.tags:
            for tag in api_dataset.tags:
                if isinstance(tag, str):
                    tags.append(tag)
                elif hasattr(tag, 'name'):
                    tags.append(tag.name)
                elif hasattr(tag, 'ref'):
                    tags.append(tag.ref)
                else:
                    tags.append(str(tag))

        return cls(
            platform="kaggle",
            dataset_ref=api_dataset.ref,
            title=api_dataset.title or "",
            subtitle=api_dataset.subtitle,
            creator_name=api_dataset.creatorName or "",
            creator_url=api_dataset.creatorUrl or "",
            total_bytes=api_dataset.totalBytes or 0,
            url=api_dataset.url or f"https://www.kaggle.com/datasets/{api_dataset.ref}",
            last_updated=api_dataset.lastUpdated or datetime.now(),
            download_count=api_dataset.downloadCount or 0,
            vote_count=api_dataset.voteCount or 0,
            usability_rating=api_dataset.usabilityRating if hasattr(api_dataset, 'usabilityRating') else None,
            license_name=api_dataset.licenseName if hasattr(api_dataset, 'licenseName') else None,
            tags=tags,
            files=files
        )

    @classmethod
    def from_huggingface_api(cls, api_dataset) -> "Dataset":
        """
        Create Dataset instance from Hugging Face API response.

        Args:
            api_dataset: DatasetInfo object from huggingface_hub

        Returns:
            Dataset instance
        """
        # HuggingFace DatasetInfo structure:
        # - id: str (e.g., "username/dataset-name")
        # - downloads: int
        # - likes: int
        # - last_modified: datetime
        # - tags: List[str]
        # - author: str
        # - card_data: dict (metadata)

        # Extract author from id if not available
        author = getattr(api_dataset, 'author', None) or api_dataset.id.split('/')[0]

        # Get license from card_data if available
        license_name = None
        if hasattr(api_dataset, 'card_data') and api_dataset.card_data:
            license_name = getattr(api_dataset.card_data, 'license', None)

        # Create readable title from dataset id
        title = api_dataset.id.split('/')[-1].replace('-', ' ').replace('_', ' ').title()

        return cls(
            platform="huggingface",
            dataset_ref=api_dataset.id,
            title=title,
            subtitle=None,
            creator_name=author,
            creator_url=f"https://huggingface.co/{author}",
            total_bytes=0,  # Not available in list API
            url=f"https://huggingface.co/datasets/{api_dataset.id}",
            last_updated=api_dataset.last_modified or datetime.now(),
            download_count=api_dataset.downloads or 0,
            vote_count=api_dataset.likes or 0,  # Map "likes" to "vote_count"
            usability_rating=None,
            license_name=license_name,
            tags=api_dataset.tags or [],
            files=[]
        )
