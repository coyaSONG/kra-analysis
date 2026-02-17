#!/usr/bin/env python3
"""Legacy entrypoint for manual API smoke check.

Canonical script lives at `apps/api/tests/test_api.py`.
"""

import asyncio

from tests.test_api import main

if __name__ == "__main__":
    asyncio.run(main())
