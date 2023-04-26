def generate_bot_message(panel_type='info', title='', content=[]):
    """ Create the Jira content of Bot Message

        Parameters:
            panel_type {str}: The type of Jira panel
                e.g. info, note, success, warning, error
            title {str}: The string we want to display after Bot Message -
            content {list}: The list of Jira content
                e.g. [{
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": "Jenkins Job: "
                            },
                            {
                                "type": "text",
                                "text": "http://123",
                                "marks": [
                                    {
                                        "type": "link",
                                        "attrs": {
                                            "href": "http://13"
                                        }
                                    }
                                ]
                            }
                        ]
                    }]
    """
    body = {
        'version': 1,
        'type': 'doc',
        'content': [
            {
                'type': 'panel',
                'attrs': {
                    'panelType': panel_type
                },
                'content': [
                    {
                        'type': 'paragraph',
                        'content': [
                            {
                                'type': 'emoji',
                                'attrs': {
                                    'shortName': ':robot:',
                                    'id': '1f916',
                                    'text': '🤖'
                                }
                            },
                            {
                                'type': 'text',
                                'text': ' '
                            },
                            {
                                'type': 'text',
                                'text': f'Bot Message - {title}',
                                'marks': [
                                    {
                                        'type': 'strong'
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }

    for c in content:
        body['content'][0]['content'].append(c)

    return body
