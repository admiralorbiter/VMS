#!/usr/bin/env python3
"""
Script to generate and set up encryption key for Google Sheets feature.
"""

import os

from cryptography.fernet import Fernet
from dotenv import load_dotenv


def generate_encryption_key():
    """Generate a new Fernet encryption key"""
    return Fernet.generate_key()


def setup_encryption_key():
    """Set up the encryption key in environment and .env file"""

    # Load existing .env file if it exists
    load_dotenv()

    # Check if ENCRYPTION_KEY already exists
    existing_key = os.environ.get("ENCRYPTION_KEY")

    if existing_key:
        print(f"ENCRYPTION_KEY already exists: {existing_key[:20]}...")
        print("If you want to generate a new key, delete the existing one first.")
        return existing_key

    # Generate new key
    new_key = generate_encryption_key()
    key_string = new_key.decode()

    print(f"Generated new encryption key: {key_string}")

    # Add to .env file
    env_file_path = ".env"

    # Check if .env file exists
    if os.path.exists(env_file_path):
        # Read existing content
        with open(env_file_path, "r") as f:
            content = f.read()

        # Check if ENCRYPTION_KEY already exists in file
        if "ENCRYPTION_KEY=" in content:
            print("ENCRYPTION_KEY already exists in .env file. Please update it manually.")
            return None

        # Append to existing file
        with open(env_file_path, "a") as f:
            f.write(f"\n# Encryption key for Google Sheets\nENCRYPTION_KEY={key_string}\n")
    else:
        # Create new .env file
        with open(env_file_path, "w") as f:
            f.write(f"# Environment variables for VMS\n")
            f.write(f"# Encryption key for Google Sheets\nENCRYPTION_KEY={key_string}\n")

    print(f"Added ENCRYPTION_KEY to {env_file_path}")
    print("IMPORTANT: Restart your application for the changes to take effect.")

    return key_string


def test_encryption():
    """Test the encryption/decryption functionality"""
    key = os.environ.get("ENCRYPTION_KEY")
    if not key:
        print("No ENCRYPTION_KEY found in environment")
        return False

    try:
        f = Fernet(key.encode() if isinstance(key, str) else key)
        test_data = "test_sheet_id_12345"
        encrypted = f.encrypt(test_data.encode())
        decrypted = f.decrypt(encrypted).decode()

        if decrypted == test_data:
            print("✓ Encryption/decryption test passed!")
            return True
        else:
            print("✗ Encryption/decryption test failed!")
            return False
    except Exception as e:
        print(f"✗ Encryption test error: {e}")
        return False


if __name__ == "__main__":
    print("Setting up encryption key for Google Sheets feature...")
    print("=" * 50)

    # Set up the key
    key = setup_encryption_key()

    if key:
        # Reload environment variables
        load_dotenv()

        # Test the encryption
        print("\nTesting encryption functionality...")
        test_encryption()

        print("\nSetup complete! You can now use the Google Sheets feature.")
        print("Remember to restart your Flask application.")
    else:
        print("\nSetup incomplete. Please check the messages above.")
