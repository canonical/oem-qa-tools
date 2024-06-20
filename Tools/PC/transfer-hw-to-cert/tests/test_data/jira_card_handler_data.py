# The full content of Jira Card retrieved via API
# It's a completed golden sample of valid response.
VALID_RESULT_FROM_API = {
    "expand": "names,schema",
    "startAt": 0,
    "maxResults": 50,
    "total": 1,
    "issues": [
        {
            "expand": "operations,versionedRepresentations,editmeta,changelog,renderedFields",  # noqa: E501
            "id": "183261",
            "self": "https://warthogs.atlassian.net/rest/api/3/issue/183261",
            "key": "VS-2623",
            "fields": {
                "description": {
                    "version": 1,
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Summary: ",
                                    "marks": [
                                        {
                                            "type": "strong"
                                        }
                                    ]
                                },
                                {
                                    "type": "text",
                                    "text": "The units are certified, note the details and transfer to cert team."  # noqa: E501
                                },
                                {
                                    "type": "hardBreak"
                                },
                                {
                                    "type": "text",
                                    "text": "QA Certified Process Guide: ",
                                    "marks": [
                                        {
                                            "type": "strong"
                                        }
                                    ]
                                },
                                {
                                    "type": "text",
                                    "text": "QA Certified Process Guide",
                                    "marks": [
                                        {
                                            "type": "link",
                                            "attrs": {
                                                "href": "https://docs.google.com/document/d/19idgrgpSOCXQ2qP6onv5mS9H_lAZ8O_bKQOrge-Rjl0/edit#heading=h.d0h70u7v3a14"   # noqa: E501
                                            }
                                        }
                                    ]
                                },
                                {
                                    "type": "hardBreak"
                                },
                                {
                                    "type": "text",
                                    "text": "Certify Planning: ",
                                    "marks": [
                                        {
                                            "type": "strong"
                                        }
                                    ]
                                },
                                {
                                    "type": "hardBreak"
                                },
                                {
                                    "type": "text",
                                    "text": "GM Image Path: ",
                                    "marks": [
                                        {
                                            "type": "strong"
                                        }
                                    ]
                                },
                                {
                                    "type": "text",
                                    "text": "https://oem-share.canonical.com/partners/sutton/share/bachman/sutton-workstation-2022-10-07/pc-sutton-bachman-focal-amd64-X00-20221004-139.iso",   # noqa: E501
                                    "marks": [
                                        {
                                            "type": "link",
                                            "attrs": {
                                                "href": "https://oem-share.canonical.com/partners/sutton/share/bachman/sutton-workstation-2022-10-07/pc-sutton-bachman-focal-amd64-X00-20221004-139.iso"    # noqa: E501
                                            }
                                        }
                                    ]
                                },
                                {
                                    "type": "hardBreak"
                                },
                                {
                                    "type": "text",
                                    "text": "SKU details : ",
                                    "marks": [
                                        {
                                            "type": "strong"
                                        }
                                    ]
                                },
                                {
                                    "type": "hardBreak"
                                }
                            ]
                        }
                    ]
                },
                "customfield_10186": {
                    "version": 1,
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "QA: "
                                },
                                {
                                    "type": "text",
                                    "text": "fake-valid-launchpad_id",
                                    "marks": [
                                        {
                                            "type": "textColor",
                                            "attrs": {
                                                "color": "#ff5630"
                                            }
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            "type": "table",
                            "attrs": {
                                "isNumberColumnEnabled": False,
                                "layout": "default",
                                "localId": "9ab65442-6e7b-42ba-9332-46fe6c947aeb"   # noqa: E501
                            },
                            "content": [
                                {
                                    "type": "tableRow",
                                    "content": [
                                        {
                                            "type": "tableHeader",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": [
                                                        {
                                                            "type": "text",
                                                            "text": "CID",
                                                            "marks": [
                                                                {
                                                                    "type": "strong"    # noqa: E501
                                                                }
                                                            ]
                                                        }
                                                    ]
                                                }
                                            ]
                                        },
                                        {
                                            "type": "tableHeader",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": [
                                                        {
                                                            "type": "text",
                                                            "text": "SKU Name",
                                                            "marks": [
                                                                {
                                                                    "type": "strong"    # noqa: E501
                                                                }
                                                            ]
                                                        }
                                                    ]
                                                }
                                            ]
                                        },
                                        {
                                            "type": "tableHeader",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": [
                                                        {
                                                            "type": "text",
                                                            "text": "Location",
                                                            "marks": [
                                                                {
                                                                    "type": "strong"    # noqa: E501
                                                                }
                                                            ]
                                                        }
                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "type": "tableRow",
                                    "content": [
                                        {
                                            "type": "tableCell",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "panel",
                                                    "attrs": {
                                                        "panelType": "info"
                                                    },
                                                    "content": [
                                                        {
                                                            "type": "paragraph",    # noqa: E501
                                                            "content": [
                                                                {
                                                                    "type": "text",     # noqa: E501
                                                                    "text": "Mandatory",    # noqa: E501
                                                                    "marks": [
                                                                        {
                                                                            "type": "textColor",    # noqa: E501
                                                                            "attrs": {  # noqa: E501
                                                                                "color": "#bf2600"  # noqa: E501
                                                                            }
                                                                        }
                                                                    ]
                                                                },
                                                                {
                                                                    "type": "hardBreak"     # noqa: E501
                                                                },
                                                                {
                                                                    "type": "text",     # noqa: E501
                                                                    "text": "Example: 202311-12345"     # noqa: E501
                                                                }
                                                            ]
                                                        }
                                                    ]
                                                }
                                            ]
                                        },
                                        {
                                            "type": "tableCell",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "panel",
                                                    "attrs": {
                                                        "panelType": "info"
                                                    },
                                                    "content": [
                                                        {
                                                            "type": "paragraph",    # noqa: E501
                                                            "content": [
                                                                {
                                                                    "type": "text",     # noqa: E501
                                                                    "text": "Optional"      # noqa: E501
                                                                },
                                                                {
                                                                    "type": "hardBreak"     # noqa: E501
                                                                },
                                                                {
                                                                    "type": "text",     # noqa: E501
                                                                    "text": "Example: Canonical-Like-DVT2"      # noqa: E501
                                                                }
                                                            ]
                                                        }
                                                    ]
                                                }
                                            ]
                                        },
                                        {
                                            "type": "tableCell",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "panel",
                                                    "attrs": {
                                                        "panelType": "info"
                                                    },
                                                    "content": [
                                                        {
                                                            "type": "paragraph",    # noqa: E501
                                                            "content": [
                                                                {
                                                                    "type": "text",     # noqa: E501
                                                                    "text": "Mandatory",    # noqa: E501
                                                                    "marks": [
                                                                        {
                                                                            "type": "textColor",    # noqa: E501
                                                                            "attrs": {      # noqa: E501
                                                                                "color": "#bf2600"      # noqa: E501
                                                                            }
                                                                        }
                                                                    ]
                                                                }
                                                            ]
                                                        },
                                                        {
                                                            "type": "paragraph",    # noqa: E501
                                                            "content": [
                                                                {
                                                                    "type": "text",     # noqa: E501
                                                                    "text": "Example: TEL-L3-F23-S5-P1"     # noqa: E501
                                                                }
                                                            ]
                                                        }
                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "type": "tableRow",
                                    "content": [
                                        {
                                            "type": "tableCell",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": [
                                                        {
                                                            "type": "text",
                                                            "text": "202305-24689             "     # noqa: E501
                                                        }
                                                    ]
                                                }
                                            ]
                                        },
                                        {
                                            "type": "tableCell",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": []
                                                }
                                            ]
                                        },
                                        {
                                            "type": "tableCell",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": [
                                                        {
                                                            "type": "text",
                                                            "text": "Adc-L3-@34-S2-p0"      # noqa: E501
                                                        }
                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "type": "tableRow",
                                    "content": [
                                        {
                                            "type": "tableCell",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": []
                                                }
                                            ]
                                        },
                                        {
                                            "type": "tableCell",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": []
                                                }
                                            ]
                                        },
                                        {
                                            "type": "tableCell",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": []
                                                }
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "type": "tableRow",
                                    "content": [
                                        {
                                            "type": "tableCell",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": [
                                                        {
                                                            "type": "text",
                                                            "text": "ABCmar-98765"      # noqa: E501
                                                        }
                                                    ]
                                                }
                                            ]
                                        },
                                        {
                                            "type": "tableCell",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": []
                                                }
                                            ]
                                        },
                                        {
                                            "type": "tableCell",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": [
                                                        {
                                                            "type": "text",
                                                            "text": "TEL-L3-F24-S5-P2"      # noqa: E501
                                                        }
                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "type": "tableRow",
                                    "content": [
                                        {
                                            "type": "tableCell",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": [
                                                        {
                                                            "type": "text",
                                                            "text": "309041-3345534"    # noqa: E501
                                                        }
                                                    ]
                                                }
                                            ]
                                        },
                                        {
                                            "type": "tableCell",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": []
                                                }
                                            ]
                                        },
                                        {
                                            "type": "tableCell",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": [
                                                        {
                                                            "type": "text",
                                                            "text": "TEL-L3-F24-S5-P99"     # noqa: E501
                                                        }
                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "type": "tableRow",
                                    "content": [
                                        {
                                            "type": "tableCell",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": [
                                                        {
                                                            "type": "text",
                                                            "text": "202303-23456",     # noqa: E501
                                                            "marks": [
                                                                {
                                                                    "type": "strong"    # noqa: E501
                                                                },
                                                                {
                                                                    "type": "textColor",    # noqa: E501
                                                                    "attrs": {
                                                                        "color": "#36b37e"  # noqa: E501
                                                                    }
                                                                }
                                                            ]
                                                        }
                                                    ]
                                                },
                                                {
                                                    "type": "paragraph",
                                                    "content": []
                                                }
                                            ]
                                        },
                                        {
                                            "type": "tableCell",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": []
                                                }
                                            ]
                                        },
                                        {
                                            "type": "tableCell",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": [
                                                        {
                                                            "type": "text",
                                                            "text": "TEL-L3-F24-S5-P1"  # noqa: E501
                                                        }
                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "type": "tableRow",
                                    "content": [
                                        {
                                            "type": "tableCell",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": [
                                                        {
                                                            "type": "text",
                                                            "text": "202303-28754"  # noqa: E501
                                                        }
                                                    ]
                                                }
                                            ]
                                        },
                                        {
                                            "type": "tableCell",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": []
                                                }
                                            ]
                                        },
                                        {
                                            "type": "tableCell",
                                            "attrs": {},
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "content": []
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }
        }
    ]
}

# VALID_CONTENT_FROM_API is the valid output from get_content_from_a_jira_card function # noqa: E501
VALID_CONTENT_FROM_API = {
  "gm_image_link": "https://oem-share.canonical.com/partners/sutton/share/bachman/sutton-workstation-2022-10-07/pc-sutton-bachman-focal-amd64-X00-20221004-139.iso",    # noqa: E501
  "assignee_original_id": "accountID",
  "description_original_data": {
                "content": [
                    {
                        "content": [
                             {
                                 "marks": [{"type": "strong"}],
                                 "text": "Summary: ",
                                 "type": "text"
                             },
                             {
                                 "text": "The units are certified, note the \
                                  details and transfer to cert team.",
                                 "type": "text"
                             },
                             {
                                 "type": "hardBreak"
                             },
                             {
                                 "marks": [{"type": "strong"}],
                                 "text": "QA Certified Process Guide: ",
                                 "type": "text"
                             },
                             {
                                 "marks": [
                                     {
                                         "attrs": {"href": "docuemnt"},
                                         "type": "link"
                                     }
                                 ],
                                 "text": "QA Certified Process Guide",
                                 "type": "text"
                             },
                             {
                                 "type": "hardBreak"
                             },
                             {
                                 "marks": [{"type": "strong"}],
                                 "text": "Certify Planning: ",
                                 "type": "text"
                             },
                             {
                                 "marks": [
                                     {
                                         "attrs": {"href": "https://123.com"},
                                         "type": "link"
                                     },
                                     {
                                         "type": "strong"
                                     }
                                 ],
                                 "text": "123abc",
                                 "type": "text"
                             },
                             {
                                 "type": "hardBreak"
                             },
                             {
                                 "marks": [{"type": "strong"}],
                                 "text": "GM Image Path: ",
                                 "type": "text"
                             },
                             {
                                 "marks": [
                                     {
                                         "attrs": {"href": "https://oem-share.\
                                                   canonical.com/partners/sutton/share/bachman\
                                                   /sutton-workstation-2022-10-07\
                                                   /pc-sutton-bachman-focal-amd64-\
                                                   X00-20221004-139.iso"},
                                         "type": "link"
                                     }
                                 ],
                                 "text": "https://oem-share.canonical.com\
                                    /partners/sutton/share/bachman/sutton-workstation-2022-10-07\
                                    /pc-sutton-bachman-focal-amd64-\
                                    X00-20221004-139.iso",
                                 "type": "text"
                             },
                             {
                                 "type": "hardBreak"
                             },
                             {
                                 "marks": [{"type": "strong"}],
                                 "text": "SKU details : ",
                                 "type": "text"
                             },
                             {
                                 "type": "hardBreak"
                             }
                             ],
                        "type": 'doc',
                        "version": 1
                    }
                ]
   }
}
# VALID_TABLE_FROM_API is the valid output from get_result_table_from_a_jira_card function # noqa: E501
VALID_TABLE_FROM_API = {
  "table": [
    {
      "type": "tableRow",
      "content": [
        {
          "type": "tableHeader",
          "attrs": {},
          "content": [
            {
              "type": "paragraph",
              "content": [
                {
                  "type": "text",
                  "text": "CID",
                  "marks": [
                    {
                      "type": "strong"
                    }
                  ]
                }
              ]
            }
          ]
        },
        {
          "type": "tableHeader",
          "attrs": {},
          "content": [
            {
              "type": "paragraph",
              "content": [
                {
                  "type": "text",
                  "text": "Location",
                  "marks": [
                    {
                      "type": "strong"
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    },
    {
      "type": "tableRow",
      "content": [
        {
          "type": "tableCell",
          "attrs": {},
          "content": [
            {
              "type": "panel",
              "attrs": {
                "panelType": "info"
              },
              "content": [
                {
                  "type": "paragraph",
                  "content": [
                    {
                      "type": "text",
                      "text": "Mandatory",
                      "marks": [
                        {
                          "type": "textColor",
                          "attrs": {
                            "color": "#bf2600"
                          }
                        }
                      ]
                    },
                    {
                      "type": "hardBreak"
                    },
                    {
                      "type": "text",
                      "text": "Example: 202311-12345"
                    }
                  ]
                }
              ]
            }
          ]
        },
        {
          "type": "tableCell",
          "attrs": {},
          "content": [
            {
              "type": "panel",
              "attrs": {
                "panelType": "info"
              },
              "content": [
                {
                  "type": "paragraph",
                  "content": [
                    {
                      "type": "text",
                      "text": "Mandatory",
                      "marks": [
                        {
                          "type": "textColor",
                          "attrs": {
                            "color": "#bf2600"
                          }
                        }
                      ]
                    }
                  ]
                },
                {
                  "type": "paragraph",
                  "content": [
                    {
                      "type": "text",
                      "text": "Example: TEL-L3-F23-S5-P1"
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    },
    {
      "type": "tableRow",
      "content": [
        {
          "type": "tableCell",
          "attrs": {},
          "content": [
            {
              "type": "paragraph",
              "content": [
                {
                  "type": "text",
                  "text": "202305-24689             "
                }
              ]
            }
          ]
        },
        {
          "type": "tableCell",
          "attrs": {},
          "content": [
            {
              "type": "paragraph",
              "content": [
                {
                  "type": "text",
                  "text": "Adc-L3-@34-S2-p0"
                }
              ]
            }
          ]
        }
      ]
    },
    {
      "type": "tableRow",
      "content": [
        {
          "type": "tableCell",
          "attrs": {},
          "content": [
            {
              "type": "paragraph",
              "content": []
            }
          ]
        },
        {
          "type": "tableCell",
          "attrs": {},
          "content": [
            {
              "type": "paragraph",
              "content": []
            }
          ]
        }
      ]
    },
    {
      "type": "tableRow",
      "content": [
        {
          "type": "tableCell",
          "attrs": {},
          "content": [
            {
              "type": "paragraph",
              "content": [
                {
                  "type": "text",
                  "text": "ABCmar-98765"
                }
              ]
            }
          ]
        },
        {
          "type": "tableCell",
          "attrs": {},
          "content": [
            {
              "type": "paragraph",
              "content": [
                {
                  "type": "text",
                  "text": "TEL-L3-F24-S5-P2"
                }
              ]
            }
          ]
        }
      ]
    },
    {
      "type": "tableRow",
      "content": [
        {
          "type": "tableCell",
          "attrs": {},
          "content": [
            {
              "type": "paragraph",
              "content": [
                {
                  "type": "text",
                  "text": "309041-3345534"
                }
              ]
            }
          ]
        },
        {
          "type": "tableCell",
          "attrs": {},
          "content": [
            {
              "type": "paragraph",
              "content": [
                {
                  "type": "text",
                  "text": "TEL-L3-F24-S5-P99"
                }
              ]
            }
          ]
        }
      ]
    },
    {
      "type": "tableRow",
      "content": [
        {
          "type": "tableCell",
          "attrs": {},
          "content": [
            {
              "type": "paragraph",
              "content": [
                {
                  "type": "text",
                  "text": "202303-23456",
                  "marks": [
                    {
                      "type": "strong"
                    },
                    {
                      "type": "textColor",
                      "attrs": {
                        "color": "#36b37e"
                      }
                    }
                  ]
                }
              ]
            },
            {
              "type": "paragraph",
              "content": []
            }
          ]
        },
        {
          "type": "tableCell",
          "attrs": {},
          "content": [
            {
              "type": "paragraph",
              "content": [
                {
                  "type": "text",
                  "text": "TEL-L3-F24-S5-P2"
                }
              ]
            }
          ]
        }
      ]
    },
    {
      "type": "tableRow",
      "content": [
        {
          "type": "tableCell",
          "attrs": {},
          "content": [
            {
              "type": "paragraph",
              "content": [
                {
                  "type": "text",
                  "text": "202303-28754"
                }
              ]
            }
          ]
        },
        {
          "type": "tableCell",
          "attrs": {},
          "content": [
            {
              "type": "paragraph",
              "content": []
            }
          ]
        }
      ]
    }
  ]
}

# A single row data whose CID and Location are valid
VALID_ROW_DATA = {
    'type':
    'tableRow',
    'content': [{
        'type':
        'tableCell',
        'attrs': {},
        'content': [{
            'type':
            'paragraph',
            'content': [{
                'type':
                'text',
                'text':
                '202303-23456',
                'marks': [{
                    'type': 'strong'
                }, {
                    'type': 'textColor',
                    'attrs': {
                        'color': '#36b37e'
                    }
                }]
            }]
        }, {
            'type': 'paragraph',
            'content': []
        }]
    }, {
        'type':
        'tableCell',
        'attrs': {},
        'content': [{
            'type': 'paragraph',
            'content': [{
                'type': 'text',
                'text': 'TEL-L3-F24-S5-P1'
            }]
        }]
    }]
}
