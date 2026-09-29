#!/usr/bin/env python
"""Quick test of data loading."""
import sys
print(f"Python: {sys.executable}")
print(f"Version: {sys.version}")
print(f"Path: {sys.path[:3]}")

try:
    import pandas as pd
    print(f"✅ pandas {pd.__version__}")
except ImportError as e:
    print(f"❌ pandas: {e}")

try:
    import numpy as np
    print(f"✅ numpy {np.__version__}")
except ImportError as e:
    print(f"❌ numpy: {e}")

try:
    from mplads.data_loader import load_combined_data
    df = load_combined_data()
    print(f"✅ Loaded {len(df)} projects")
    print(f"Columns: {df.shape[1]}")
except Exception as e:
    print(f"❌ Data loading: {e}")
    import traceback
    traceback.print_exc()
