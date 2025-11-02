"""
Setup script for CI environments.
Handles optional dependencies gracefully.
"""
import sys
import subprocess

def install_optional(package, import_name=None):
    """Try to install optional package."""
    if import_name is None:
        import_name = package.split('>=')[0].split('==')[0]
    
    try:
        __import__(import_name)
        print(f"✓ {import_name} already available")
        return True
    except ImportError:
        print(f"⚠ Trying to install {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✓ {package} installed successfully")
            return True
        except subprocess.CalledProcessError:
            print(f"✗ {package} installation failed (optional, continuing...)")
            return False

if __name__ == "__main__":
    print("Setting up CI environment...")
    
    # Core (required)
    required = [
        ("pandas>=2.0.0", "pandas"),
        ("numpy>=1.24.0", "numpy"),
        ("pytest>=7.4.0", "pytest"),
        ("pytest-cov>=4.1.0", "pytest_cov"),
        ("pytest-mock>=3.11.1", "pytest_mock"),
    ]
    
    # Optional
    optional = [
        ("scipy>=1.10.0", "scipy"),
        ("matplotlib>=3.7.0", "matplotlib"),
        ("plotly>=5.14.0", "plotly"),
        ("dash>=2.14.0", "dash"),
        ("discord.py>=2.3.0", "discord"),
        ("ccxt>=4.0.0", "ccxt"),
    ]
    
    print("\nInstalling required packages...")
    for package, import_name in required:
        install_optional(package, import_name)
    
    print("\nInstalling optional packages...")
    for package, import_name in optional:
        install_optional(package, import_name)
    
    print("\n✓ Setup complete!")

