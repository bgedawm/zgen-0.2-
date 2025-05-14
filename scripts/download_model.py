#!/usr/bin/env python3
"""
Download LLM Model Script
------------------------
This script downloads the necessary LLM model files for the Local Scout AI Agent.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Initialize logging
from utils.logger import setup_logging

# Load environment variables
load_dotenv()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Download LLM Models")
    parser.add_argument(
        "--model", 
        type=str, 
        default=os.getenv("LLM_MODEL", "llama2"),
        help="Model to download (llama2, orca-mini, etc.)"
    )
    parser.add_argument(
        "--path", 
        type=str, 
        default=os.getenv("LLM_MODEL_PATH", "./models"),
        help="Path to save the model"
    )
    parser.add_argument(
        "--embedding-model", 
        type=str, 
        default=os.getenv("LLM_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        help="Embedding model to download"
    )
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Force download even if model exists"
    )
    
    return parser.parse_args()


def download_model(model_name, save_path, force=False):
    """Download the specified model."""
    logger = logging.getLogger(__name__)
    
    # Ensure the models directory exists
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    # Check if model already exists
    if os.path.exists(save_path) and not force:
        logger.info(f"Model {model_name} already exists at {save_path}")
        return True
    
    logger.info(f"Downloading {model_name} to {save_path}...")
    
    try:
        # Import huggingface_hub for downloading
        from huggingface_hub import hf_hub_download
        
        # Map model names to Hugging Face repos and filenames
        model_map = {
            "llama2": {
                "repo": "TheBloke/Llama-2-7B-Chat-GGUF",
                "filename": "llama-2-7b-chat.q4_K_M.gguf"
            },
            "orca-mini": {
                "repo": "TheBloke/orca_mini_3B-GGUF",
                "filename": "orca-mini-3b.q4_K_M.gguf"
            },
            "mistral": {
                "repo": "TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
                "filename": "mistral-7b-instruct-v0.2.q4_K_M.gguf" 
            }
        }
        
        if model_name in model_map:
            repo_id = model_map[model_name]["repo"]
            filename = model_map[model_name]["filename"]
        else:
            logger.error(f"Unknown model: {model_name}")
            return False
        
        # Download the model
        hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=os.path.dirname(save_path),
            local_dir_use_symlinks=False
        )
        
        # Rename if needed
        downloaded_path = os.path.join(os.path.dirname(save_path), filename)
        if downloaded_path != save_path:
            os.rename(downloaded_path, save_path)
        
        logger.info(f"Successfully downloaded {model_name} to {save_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error downloading {model_name}: {str(e)}")
        return False


def download_embedding_model(model_name, force=False):
    """Download the embedding model from sentence-transformers."""
    logger = logging.getLogger(__name__)
    
    try:
        from sentence_transformers import SentenceTransformer
        
        logger.info(f"Downloading embedding model {model_name}...")
        
        # This will download the model if it's not already downloaded
        _ = SentenceTransformer(model_name)
        
        logger.info(f"Successfully downloaded embedding model {model_name}")
        return True
    
    except Exception as e:
        logger.error(f"Error downloading embedding model {model_name}: {str(e)}")
        return False


def main():
    """Main entry point for the script."""
    args = parse_args()
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting model download process...")
    
    # Download the LLM model
    model_success = download_model(
        args.model, 
        args.path, 
        args.force
    )
    
    # Download the embedding model
    embedding_success = download_embedding_model(
        args.embedding_model, 
        args.force
    )
    
    if model_success and embedding_success:
        logger.info("All models downloaded successfully!")
        return 0
    else:
        logger.error("Failed to download some models. Check the logs for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())