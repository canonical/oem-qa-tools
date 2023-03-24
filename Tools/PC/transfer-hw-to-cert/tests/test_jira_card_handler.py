import unittest

from jira_card_handler import get_table_content_from_a_jira_card


class GetCandidateDutFromJiraCardTest(unittest.TestCase):
    def test_paramtere_key_is_wrong_type(self):
        """ Check the parameter type must need to be string
        """
        for t in [123, ('c', 'd'), {'hola': 'canonical'}]:
            self.assertRaises(TypeError, get_table_content_from_a_jira_card, t)


if __name__ == '__main__':
    unittest.main()
