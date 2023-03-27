import sys

from unittest.mock import MagicMock

sys.modules['Jira.apis.base'] = MagicMock()
