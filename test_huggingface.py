#!/usr/bin/env python3
"""
Test script for Hugging Face integration.
Run this before full deployment to validate the implementation.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import Settings
from src.services.platform_factory import PlatformFactory
from src.utils.logger import setup_logger


def test_huggingface_client():
    """Test Hugging Face client independently."""
    print("=" * 60)
    print("Testing Hugging Face Integration")
    print("=" * 60)

    # Load settings
    try:
        print("\n1. Loading settings...")
        settings = Settings.load()

        # Temporarily override platform to huggingface for testing
        original_platform = settings.platform.active
        settings.platform.active = "huggingface"
        print(f"✓ Settings loaded (original platform: {original_platform})")
        print(f"✓ Test platform set to: {settings.platform.active}")
    except Exception as e:
        print(f"✗ Failed to load settings: {e}")
        return False

    # Create client
    try:
        print("\n2. Creating Hugging Face client...")
        client = PlatformFactory.create_client(settings)
        print(f"✓ Client created: {client.get_platform_name()}")
    except Exception as e:
        print(f"✗ Failed to create client: {e}")
        return False

    # Test authentication
    try:
        print("\n3. Testing authentication...")
        client.authenticate()
        print("✓ Authentication successful")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        return False

    # Test listing datasets
    try:
        print("\n4. Testing dataset listing (fetching top 5 trending)...")
        datasets = client.list_recent_datasets(max_size=5, page=1)
        print(f"✓ Found {len(datasets)} trending datasets")

        if len(datasets) > 0:
            print("\nDataset details:")
            for i, dataset in enumerate(datasets, 1):
                print(f"\n  Dataset {i}:")
                print(f"    - Platform: {dataset.platform}")
                print(f"    - Ref: {dataset.dataset_ref}")
                print(f"    - Title: {dataset.title}")
                print(f"    - Creator: {dataset.creator_name}")
                print(f"    - Downloads: {dataset.download_count:,}")
                print(f"    - Likes: {dataset.vote_count:,}")
                print(f"    - Last Updated: {dataset.last_updated}")
                print(f"    - URL: {dataset.url}")
                if dataset.tags:
                    print(f"    - Tags: {', '.join(dataset.tags[:5])}")
        else:
            print("⚠️  No trending datasets found (check filter settings)")

    except Exception as e:
        print(f"✗ Failed to list datasets: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test platform factory
    try:
        print("\n5. Testing platform factory...")
        max_datasets = PlatformFactory.get_max_datasets_per_poll(settings)
        print(f"✓ Max datasets per poll: {max_datasets}")
    except Exception as e:
        print(f"✗ Failed to test platform factory: {e}")
        return False

    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Set platform in config.yaml: platform.active = 'huggingface'")
    print("2. Optional: Set HF_TOKEN environment variable for private datasets")
    print("3. Restart the ingestion engine")
    print("4. Check the web dashboard at http://localhost:5000")
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        success = test_huggingface_client()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
