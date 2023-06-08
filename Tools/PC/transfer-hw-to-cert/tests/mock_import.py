import sys

from unittest.mock import MagicMock

sys.modules['Jira.apis.base'] = MagicMock()
sys.modules['GoogleSheet.google_sheet_api'] = MagicMock()
