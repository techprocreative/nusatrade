"""Build script for creating Windows executable."""

import os
import subprocess
import sys
from pathlib import Path


def build():
    """Build Windows executable using PyInstaller."""
    print("Building ForexAI Connector for Windows...")

    # Paths
    script_dir = Path(__file__).parent
    src_dir = script_dir / "src"
    main_script = src_dir / "main.py"
    resources_dir = script_dir / "resources"
    icon_path = resources_dir / "icon.ico"

    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=ForexAI-Connector",
        "--onefile",
        "--console",  # Changed from --windowed for debugging
        "--clean",
        f"--distpath={script_dir / 'dist'}",
        f"--workpath={script_dir / 'build'}",
        f"--specpath={script_dir}",
        f"--paths={src_dir}",  # Add src to search paths
    ]

    # Add icon if exists
    if icon_path.exists():
        cmd.append(f"--icon={icon_path}")

    # Add hidden imports for MT5 and PyQt6
    # PyQt6 requires explicit imports for all submodules
    hidden_imports = [
        # MetaTrader5
        "MetaTrader5",
        "numpy",  # Required by MetaTrader5
        # PyQt6 - Core modules
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtWidgets", 
        "PyQt6.QtGui",
        "PyQt6.sip",
        # PyQt6 - Additional required modules
        "PyQt6.QtNetwork",
        "PyQt6.QtSvg",
        "PyQt6.QtSvgWidgets",
        # Networking
        "websockets",
        "websockets.client",
        "websockets.exceptions",
        "ssl",
        "asyncio",
        # Data validation
        "pydantic",
        "pydantic.fields",
        # Crypto
        "cryptography",
        "cryptography.fernet",
        # HTTP
        "requests",
        "tenacity",
        # Standard library
        "json",
        "logging",
        "dataclasses",
        "typing",
    ]
    for imp in hidden_imports:
        cmd.append(f"--hidden-import={imp}")

    # Collect all files for packages that need binaries/data
    collect_all_packages = ["PyQt6"]
    for pkg in collect_all_packages:
        cmd.append(f"--collect-all={pkg}")

    # Add data files
    if resources_dir.exists():
        cmd.append(f"--add-data={resources_dir};resources")

    # Main script
    cmd.append(str(main_script))

    print(f"Running: {' '.join(cmd)}")

    # Run PyInstaller
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("\n✅ Build successful!")
        print(f"Executable: {script_dir / 'dist' / 'ForexAI-Connector.exe'}")
    else:
        print("\n❌ Build failed!")
        print(result.stderr)
        sys.exit(1)


def clean():
    """Clean build artifacts."""
    import shutil

    script_dir = Path(__file__).parent
    dirs_to_clean = ["build", "dist", "__pycache__"]

    for dir_name in dirs_to_clean:
        dir_path = script_dir / dir_name
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"Removed: {dir_path}")

    # Remove spec file
    spec_file = script_dir / "ForexAI-Connector.spec"
    if spec_file.exists():
        spec_file.unlink()
        print(f"Removed: {spec_file}")

    print("Clean complete!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        clean()
    else:
        build()
