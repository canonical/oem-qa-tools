VALID_TEST_RESULT_CONTENT = {
  "expand": "names,schema",
  "startAt": 0,
  "maxResults": 50,
  "total": 1,
  "issues": [
    {
      "expand": "operations,versionedRepresentations,editmeta,changelog",
      "id": "183261",
      "self": "https://warthogs.atlassian.net/rest/api/3/issue/183261",
      "key": "VS-2623",
      "fields": {
        "customfield_10186": {
          "version": 1,
          "type": "doc",
          "content": [
            {
              "type": "paragraph",
              "content": [
                {
                  "type": "text",
                  "text": "QA:"
                }
              ]
            },
            {
              "type": "table",
              "attrs": {
                "isNumberColumnEnabled": False,
                "layout": "default",
                "localId": "9ab65442-6e7b-42ba-9332-46fe6c947aeb"
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
                              "text": "SKU Name",
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
                                  "text": "Optional"
                                },
                                {
                                  "type": "hardBreak"
                                },
                                {
                                  "type": "text",
                                  "text": "Example: Canonical-Like-DVT2"
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
                              "text": "202303-23456"
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
                              "text": "TEL-L3-F24-S5-P1"
                            }
                          ]
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

INVALID_TEST_RESULT_CONTENT = {
  "expand": "names,schema",
  "startAt": 0,
  "maxResults": 50,
  "total": 1,
  "issues": [
    {
      "expand": "operations,versionedRepresentations,editmeta,changelog",
      "id": "183260",
      "self": "https://warthogs.atlassian.net/rest/api/3/issue/183260",
      "key": "VS-2622",
      "fields": {
        "customfield_10186": None
      }
    }
  ]
}
