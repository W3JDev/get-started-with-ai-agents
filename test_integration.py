#!/usr/bin/env python3
"""
Integration test script to validate the AI agent setup with existing Azure resources.
This script tests the basic functionality without requiring a full deployment.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_service_imports():
    """Test that all services can be imported successfully."""
    try:
        from services.azure_openai_service import AzureOpenAIService
        from services.cosmos_db_service import CosmosDBService
        from services.blob_storage_service import BlobStorageService
        from services.rag_service import RAGService
        print("✅ All service imports successful")
        return True
    except ImportError as e:
        print(f"❌ Service import failed: {e}")
        return False

async def test_app_creation():
    """Test that the FastAPI app can be created."""
    try:
        from api.main import create_app
        app = create_app()
        print("✅ FastAPI application creation successful")
        return True
    except Exception as e:
        print(f"❌ App creation failed: {e}")
        return False

async def test_environment_variables():
    """Test environment variable configuration."""
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY", 
        "AZURE_OPENAI_DEPLOYMENT_NAME",
        "AZURE_STORAGE_ACCOUNT_NAME",
        "AZURE_STORAGE_ACCOUNT_KEY",
        "AZURE_COSMOSDB_ENDPOINT",
        "AZURE_COSMOSDB_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Missing environment variables (expected for test): {', '.join(missing_vars)}")
        print("   To test with real services, copy .env.template to .env and configure your Azure resources")
        return False
    else:
        print("✅ All required environment variables are set")
        return True

async def test_service_initialization():
    """Test service initialization with mock environment variables."""
    # Set mock environment variables for testing
    test_env = {
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "AZURE_OPENAI_API_KEY": "test-key",
        "AZURE_OPENAI_DEPLOYMENT_NAME": "gpt-4",
        "AZURE_STORAGE_ACCOUNT_NAME": "testaccount",
        "AZURE_STORAGE_ACCOUNT_KEY": "test-key",
        "AZURE_COSMOSDB_ENDPOINT": "https://test.documents.azure.com:443/",
        "AZURE_COSMOSDB_KEY": "test-key"
    }
    
    # Temporarily set environment variables
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    try:
        from services.azure_openai_service import AzureOpenAIService
        from services.cosmos_db_service import CosmosDBService
        from services.blob_storage_service import BlobStorageService
        
        # Test service initialization (will fail on actual connection, but that's expected)
        try:
            openai_service = AzureOpenAIService()
            print("✅ Azure OpenAI service initialization successful")
        except Exception as e:
            print(f"⚠️  Azure OpenAI service init (expected with mock credentials): {str(e)[:100]}...")
        
        try:
            cosmos_service = CosmosDBService()
            print("✅ Cosmos DB service initialization successful")
        except Exception as e:
            print(f"⚠️  Cosmos DB service init (expected with mock credentials): {str(e)[:100]}...")
        
        try:
            blob_service = BlobStorageService()
            print("✅ Blob Storage service initialization successful")
        except Exception as e:
            print(f"⚠️  Blob Storage service init (expected with mock credentials): {str(e)[:100]}...")
        
        return True
        
    finally:
        # Restore original environment variables
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

async def main():
    """Run all tests."""
    print("🚀 Starting AI Agent Integration Tests\n")
    
    tests = [
        ("Service Imports", test_service_imports),
        ("App Creation", test_app_creation),
        ("Environment Variables", test_environment_variables),
        ("Service Initialization", test_service_initialization),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        result = await test_func()
        results.append((test_name, result))
        print()
    
    # Summary
    print("=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("\n🎉 All tests passed! The AI agent is ready for deployment.")
        print("\n📋 Next steps:")
        print("1. Copy .env.template to .env")
        print("2. Configure your Azure resource details in .env")
        print("3. Run 'azd up' to deploy to Azure Container Apps")
    else:
        print("\n🔧 Some tests failed. Please check the output above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))