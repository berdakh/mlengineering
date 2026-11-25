"""Allow ``python -m pumpwatch ...`` as an alternative to the console script."""
import sys

from pumpwatch.cli import main

sys.exit(main())
