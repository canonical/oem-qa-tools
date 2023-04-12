import sys

from unittest.mock import MagicMock

sys.modules['Jira.scenarios.pc.pc'] = MagicMock()
sys.modules['GoogleSheet.google_sheet_api'] = MagicMock()
