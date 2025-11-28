"""
Root conftest.py to configure pytest for the entire project.

This file ensures that the src directory is in the Python path,
allowing tests to import modules without installation.
"""

import sys
from pathlib import Path

# Add the project root to Python path so 'src' imports work
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
