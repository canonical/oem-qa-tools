import json
import re
import os
import traceback

from Jira.apis.base import JiraAPI, get_jira_members, JIRA_DIR_PATH
from Jira.utils.logging_utils import get_logger
logger = get_logger(__name__)


class Error(Exception):
    """Base class for other exceptions"""
    pass


class NoRequestDate(Error):
    """ Raised when no request date data
        Only for somerville
    """
    pass


class QaPcJira():

    BUG_LIST_LINK = 'https://bugs.launchpad.net/{}/+bugs?' \
        'field.searchtext&orderby=-importance&search=Search' \
        '&field.status:list=NEW&field.status:list=OPINION' \
        '&field.status:list=INVALID&field.status:list=WONTFIX' \
        '&field.status:list=EXPIRED&field.status:list=CONFIRMED' \
        '&field.status:list=TRIAGED&field.status:list=INPROGRESS' \
        '&field.status:list=FIXCOMMITTED&field.status:list=FIXRELEASED' \
        '&field.status:list=INCOMPLETE_WITH_RESPONSE' \
        '&field.status:list=INCOMPLETE_WITHOUT_RESPONSE' \
        '&assignee_option=any&field.assignee&field.bug_reporter' \
        '&field.bug_commenter&field.subscriber&field.structural_subscriber' \
        '&field.tag={}+&field.tags_combinator=ANY&field.has_cve.used' \
        '&field.omit_dupes.used&field.omit_dupes=on&field.affects_me.used' \
        '&field.has_patch.used&field.has_branches.used' \
        '&field.has_branches=on' \
        '&field.has_no_branches.used&field.has_no_branches=on' \
        '&field.has_blueprints.used&field.has_blueprints=on' \
        '&field.has_no_blueprints.used&field.has_no_blueprints=on'

    def __init__(self, payload={}, project=''):
        self.jira_api = JiraAPI()
        self.members = get_jira_members()
        if not project:
            raise ValueError('Value of "project" cannot be empty')
        if not payload:
            raise ValueError('Value of "payload" cannot be empty')
        self.project = project
        self.payload = payload
        self.project_profile = self._load_project_profile()
        self.current_stage = ''
        self.current_platform = {}
        self.epic = self.project_profile['epic']

        self.task_reporter = self.members[
            self.project_profile['reporter']]['jira_uid'] \
            if 'reporter' in self.project_profile and \
            self.project_profile['reporter'] in self.members \
            else None

        if not self.task_reporter:
            raise ValueError(
                'Reporter cannot be None. Please check the project config'
            )

        self.task_assignee = self.members[
            self.project_profile['assignee']]['jira_uid'] \
            if 'assignee' in self.project_profile and \
            self.project_profile['assignee'] in self.members \
            else None

        self.fixed_labels = self.project_profile['labels']['fixed']

    def _load_project_profile(self):
        """ Load the project profile from JSON
        """
        logger.info('Loading "{}" profile...'.format(self.project))
        with open(os.path.join(
            JIRA_DIR_PATH,
            'scenarios',
            'pc',
            'configs'
            f'{self.project}.json')
        ) as f:
            pf = json.load(f)
            return pf['jira_content']

    # FIXME: Should integrate with _api_get_task_by_tag method
    def _api_get_story_task_by_tag(self, tag=''):
        """ Get the story task by tag

            Parameters:
                tag {str}: Needed information
                    tag is lp_tag if project is stella,
                    otherwise it should be platform_tag
            Return {dist}
                e.g.
                    {
                        "id": "74064",
                        "self":
                        "https://warthogs.atlassian.net/rest/api/3/issue/74064",
                        "key": "VS-746",
                        "fields": { "summary": "['Cres'] (fossa-corsola-abc)" }
                    }
        """
        if tag:
            payload = {
                'jql': 'project = {} AND summary ~ "{}" AND '
                'issuetype = Story order by created DESC'.format(
                    self.jira_api.jira_project['key'], tag
                ),
                'fields': ['summary'],
            }
            response = self.jira_api.get_issues(payload=payload)
            candidates = json.loads(response.text)
            for c in candidates['issues']:
                if '({})'.format(tag) in c['fields']['summary']:
                    try:
                        del c['expand']
                    except Exception:
                        pass
                    return c
        return {}

    def _api_get_task_by_tag(self, tag=''):
        """ Get the general task by tag

            Parameters:
                tag {str}: Needed information

            Return {dist}
                e.g.
                    {
                        "id": "74064",
                        "self":
                        "https://warthogs.atlassian.net/rest/api/3/issue/74064",
                        "key": "VS-746",
                        "fields": { "summary": "['Cres'] (fossa-corsola-abc)" }
                    }
        """
        if tag:
            payload = {
                'jql': 'project = {} AND summary ~ "{}" AND '
                'type in standardIssueTypes() order by created DESC'.format(
                    self.jira_api.jira_project['key'], tag
                ),
                'fields': ['summary'],
            }
            response = self.jira_api.get_issues(payload=payload)
            candidates = json.loads(response.text)
            for c in candidates['issues']:
                if '({})'.format(tag) in c['fields']['summary']:
                    try:
                        del c['expand']
                    except Exception:
                        pass
                    return c
        return {}

    def _generate_story_card_title(self):
        """ Return {string}: return the title name
        """
        return '{} ({})'.format(
            self.current_platform['product_name'][0],
            self.current_platform['platform_tag']
        )

    def _generate_rts_card_title(self, milestone=''):
        """ Return {string}: return the title name
        """
        return '{} ({}) {}'.format(
            self.current_platform['product_name'][0],
            self.current_platform['platform_tag'],
            milestone
        )

    def _generate_prts_card_title(self):
        """ Generate the PRTS card title
        """
        raise NotImplementedError(
            'not implement the _generate_prts_card_title yet'
        )

    def _generate_transfer_cert_card_title(self):
        """ Generate the transfer to cert card title
        """
        raise NotImplementedError(
            'not implement the _generate_transfer_cert_card_title yet'
        )

    def _generate_online_update_card_title(self):
        """ Generate the Online Update card title
        """
        raise NotImplementedError(
            'not implement the _generate_online_update_card_title yet'
        )

    def _generate_show_product_name(self, product_name=[]):
        """ Generate the show product_name

            Parameters:
                product_name {list}: A bounch of product_name

            Return {string}: Show product_name
                e.g. Vostro 3520/Vostro 3420/Inspiron 15 3520
        """
        return '' if not product_name else '/'.join(set(product_name))

    def _generate_rts_description(self):
        """"""
        platform_tag = self.current_platform['platform_tag']
        product_name = self.current_platform['product_name']
        pm = self.current_platform['pm']
        fe = self.current_platform['fe']
        swe = self.current_platform['swe']
        lp_tag = self.current_platform['lp_tag'] if 'lp_tag' \
            in self.current_platform else None

        bug_list_link = self.BUG_LIST_LINK.format(self.project, platform_tag)

        # Generate the description content
        desired_content = [
            ('Model Name',
                self._generate_show_product_name(product_name)),
            ('Engineer Plan', ''),
            ('Test Matrix', ''),
            ('Manifest', ''),
            ('BIOS', ''),
            ('Platform Tag', platform_tag),
            ('Launchpad Bug List', bug_list_link, 'link', 'Bug List'),
            ('PM', pm),
            ('FE', fe),
            ('SWE', swe)
        ]

        if lp_tag:
            desired_content.append(('Launchpad Tag', lp_tag))

        description_content = self.jira_api.create_paragraph_content(
            desired_content=desired_content)
        return description_content

    def _generate_prts_description(self):
        """"""
        platform_tag = self.current_platform['platform_tag']
        pm = self.current_platform['pm']
        fe = self.current_platform['fe']
        swe = self.current_platform['swe']
        request = self.current_platform['request'] if 'request' \
            in self.current_platform else None
        lp_tag = self.current_platform['lp_tag'] if 'lp_tag' \
            in self.current_platform else None

        bug_list_link = self.BUG_LIST_LINK.format(self.project, platform_tag)

        # Generate the description content
        desired_content = [
            ('Engineer Plan', ''),
            ('Test Matrix', ''),
            ('Manifest', ''),
            ('BIOS', ''),
            ('Platform Tag', platform_tag),
            ('Launchpad Bug List', bug_list_link, 'link', 'Bug List'),
            ('PM', pm),
            ('FE', fe),
            ('SWE', swe)
        ]

        if lp_tag:
            desired_content.append(('Launchpad Tag', lp_tag))

        if request:
            desired_content.append(('Request', request))

        description_content = self.jira_api.create_paragraph_content(
            desired_content=desired_content)
        return description_content

    def _generate_online_update_description(self):
        """"""
        platform_tag = self.current_platform['platform_tag']
        pm = self.current_platform['pm']
        fe = self.current_platform['fe']
        swe = self.current_platform['swe']
        request = self.current_platform['request'] if 'request' \
            in self.current_platform else None
        lp_tag = self.current_platform['lp_tag'] if 'lp_tag' \
            in self.current_platform else None

        bug_list_link = self.BUG_LIST_LINK.format(self.project, platform_tag)

        # Generate the description content
        desired_content = [
            ('Engineer Plan', ''),
            ('Test Matrix', ''),
            ('Manifest', ''),
            ('BIOS', ''),
            ('Platform Tag', platform_tag),
            ('Launchpad Bug List', bug_list_link, 'link', 'Bug List'),
            ('PM', pm),
            ('FE', fe),
            ('SWE', swe)
        ]

        if lp_tag:
            desired_content.append(('Launchpad Tag', lp_tag))

        if request:
            desired_content.append(('Request', request))

        description_content = self.jira_api.create_paragraph_content(
            desired_content=desired_content)
        return description_content

    def _generate_story_description(self):
        """"""
        platform_tag = self.current_platform['platform_tag']
        product_name = self.current_platform['product_name']
        pm = self.current_platform['pm']
        fe = self.current_platform['fe']
        swe = self.current_platform['swe']
        lp_tag = self.current_platform['lp_tag'] if 'lp_tag' \
            in self.current_platform else None

        bug_list_link = self.BUG_LIST_LINK.format(self.project, platform_tag)

        # Generate the description content
        desired_content = [
            ('Model Name', self._generate_show_product_name(product_name)),
            ('Platform Tag', platform_tag),
            ('Launchpad Bug List', bug_list_link, 'link', 'Bug List'),
            ('PM', pm),
            ('FE', fe),
            ('SWE', swe)
        ]

        if lp_tag:
            desired_content.append(('Launchpad Tag', lp_tag))

        description_content = self.jira_api.create_paragraph_content(
            desired_content=desired_content)
        return description_content

    def _generate_transfer_cert_description(self):
        """ The content of transfer to cert card
        """
        # Generate the description content
        desired_content = [
            (
                'Summary',
                'The units are certified, note the details and transfer to '
                'cert team.'
            ),
            (
                'QA Certified Process Guide',
                'https://docs.google.com/document/d/19idgrgpSOCXQ2qP6onv5m'
                'S9H_lAZ8O_bKQOrge-Rjl0/edit#heading=h.d0h70u7v3a14',
                'link',
                'QA Certified Process Guide'
            ),
            ('Certify Planning', ''),
            ('GM Image Path', ''),
            ('SKU details ', ''),
        ]
        description_content = self.jira_api.create_paragraph_content(
            desired_content=desired_content)
        return description_content

    def _generate_transfer_cert_table_description(self):
        """ The table content of transfer to cert card
        """
        desired_table = {
            'attrs': {
                'isNumberColumnEnabled': False,
                'layout': 'default'
            },
            'headers': ['CID', 'SKU Name', 'Location'],
            'row_contents': [
                ('', '', ''),
            ]
        }
        table_content = self.jira_api.create_table_content(
            desired_table=desired_table)
        return table_content

    def _create_story_task(self):
        """ Create story task for a specific platform

            Return {dict}: Return the story info of specific platform
        """
        # Template of "fields" payload in Jira's request
        fields = self.jira_api.create_jira_fields_template(task_type='Story')

        # Assign Summary
        fields['summary'] = self._generate_story_card_title()

        # Assign the description content
        fields['description']['content'].append(
                self._generate_story_description())

        # Assign Reporter
        if self.task_reporter:
            fields['reporter']['id'] = self.task_reporter

        # Assign task to assignee
        if self.task_assignee:
            fields['assignee'] = {
                'id': self.task_assignee
            }

        # Assign lable to story task
        fields['labels'] = self.fixed_labels

        # Create issue
        response = self.jira_api.create_an_issue(
            payload={'fields': fields, 'updates': {}})
        if not response.ok:
            logger.warn('  - Story task ... Fail')
            return {}
        story_task = json.loads(response.text)

        # Update Epic
        self.jira_api.update_epic(
            epic=self.epic, issues_id=[int(story_task['id'])])

        return story_task

    def _create_rts_task(self, story_task={}):
        """ Create rts tasks for a specific platform

            return {list}: a list includes the info of platform's
                milestone tasks
        """
        rts_milestone = self.project_profile['milestones']['rts']
        issueUpdates = []  # Put tasks in this list

        for idx in range(len(rts_milestone)):
            # Template of "fields" payload in Jira's request
            fields = self.jira_api.create_jira_fields_template(
                task_type='Task')

            # Assign Summary
            fields['summary'] = self._generate_rts_card_title(
                milestone=rts_milestone[idx]
            )

            # Assign Reporter
            if self.task_reporter:
                fields['reporter']['id'] = self.task_reporter

            # Assign task to assignee
            if self.task_assignee:
                fields['assignee'] = {
                    'id': self.task_assignee
                }

            # Assign the description content
            fields['description']['content'].append(
                self._generate_rts_description())

            # Assign lable to rts task
            fields['labels'] = self.fixed_labels.copy()
            if 'rts_labels' in self.project_profile['labels']:
                fields['labels'].append(
                    self.project_profile['labels']['rts_labels'][idx]
                )

            # FIXME: Use regex to verify the valid time format
            # date_regex = datetime.datetime.strptime
            if 'start_date' in self.current_platform and \
                    self.current_platform['start_date'][idx]:
                fields['customfield_10015'] = \
                    self.current_platform['start_date'][idx]

            if 'end_date' in self.current_platform and \
                    self.current_platform['end_date'][idx]:
                fields['duedate'] = self.current_platform['end_date'][idx]

            # link task to story task
            update_link = self.jira_api.create_link_issue_content(
                target_issues=[{'key': story_task['key']}]) \
                if story_task['key'] else {}

            issueUpdates.append({'fields': fields, 'update': update_link})

        response = self.jira_api.create_issues(
            payload={'issueUpdates': issueUpdates})
        if not response.ok:
            logger.warn('  Milestone tasks ... Fail')
            return {}

        milestone_tasks = json.loads(response.text)['issues']
        ids = [int(task['id']) for task in milestone_tasks]
        # Update Epic
        self.jira_api.update_epic(epic=self.epic, issues_id=ids)

        return milestone_tasks

    def _create_prts_task(self, story_task={}):
        """ Create prts task for a specific platform
        """
        # Template of "fields" payload in Jira's request
        fields = self.jira_api.create_jira_fields_template(task_type='Task')

        # Assign Summary
        fields['summary'] = self._generate_prts_card_title()

        # Assign Reporter
        if self.task_reporter:
            fields['reporter']['id'] = self.task_reporter

        # Assign task to assignee
        if self.task_assignee:
            fields['assignee'] = {
                'id': self.task_assignee
            }

        # Assign the description content
        fields['description']['content'].append(
            self._generate_prts_description())

        # Assign lable to prts task
        fields['labels'] = self.fixed_labels.copy()
        if 'prts_labels' in self.project_profile['labels']:
            fields['labels'].extend(
                self.project_profile['labels']['prts_labels']
            )

        # link task to story task
        update_link = {}
        if story_task:
            update_link = self.jira_api.create_link_issue_content(
                target_issues=[{'key': story_task['key']}]) \
                if story_task['key'] else {}

        response = self.jira_api.create_an_issue(
            payload={'fields': fields, 'update': update_link})

        if not response.ok:
            logger.warn('Failed to create task...')
            return

        id = json.loads(response.text)['id']

        # Update Epic
        self.jira_api.update_epic(epic=self.epic, issues_id=[id])
        return json.loads(response.text)

    def _create_online_update_task(self, story_task={}):
        """ Create Online Update task for a specific platform
        """
        # Template of "fields" payload in Jira's request
        fields = self.jira_api.create_jira_fields_template(task_type='Task')

        # Assign Summary
        fields['summary'] = self._generate_online_update_card_title()

        # Assign Reporter
        if self.task_reporter:
            fields['reporter']['id'] = self.task_reporter

        # Assign task to assignee
        if self.task_assignee:
            fields['assignee'] = {
                'id': self.task_assignee
            }

        # Assign the description content
        fields['description']['content'].append(
            self._generate_online_update_description())

        # Assign lable to online_update task
        fields['labels'] = self.fixed_labels.copy()
        if 'online_update_labels' in self.project_profile['labels']:
            fields['labels'].extend(
                self.project_profile['labels']['online_update_labels']
            )

        # link task to story task
        update_link = {}
        if story_task:
            update_link = self.jira_api.create_link_issue_content(
                target_issues=[{'key': story_task['key']}]) \
                if story_task['key'] else {}

        response = self.jira_api.create_an_issue(
            payload={'fields': fields, 'update': update_link})

        if not response.ok:
            logger.warn('Failed to create task...')
            return

        id = json.loads(response.text)['id']

        # Update Epic
        self.jira_api.update_epic(epic=self.epic, issues_id=[id])
        return json.loads(response.text)

    def _create_transfer_to_cert_task(self, story_task={}):
        """ Create transfer to cert task for a specific platform
        """
        # Template of "fields" payload in Jira's request
        fields = self.jira_api.create_jira_fields_template(task_type='Task')

        # Assign Summary
        fields['summary'] = self._generate_transfer_cert_card_title()

        # Assign Reporter
        if self.task_reporter:
            fields['reporter']['id'] = self.task_reporter

        # Assign task to assignee
        if self.task_assignee:
            fields['assignee'] = {
                'id': self.task_assignee
            }

        # Assign the description content
        fields['description']['content'].append(
            self._generate_transfer_cert_description())

        # Add the table into the description content
        fields['description']['content'].append(
            self._generate_transfer_cert_table_description())

        # link task to story task
        update_link = {}
        if story_task:
            update_link = self.jira_api.create_link_issue_content(
                target_issues=[{'key': story_task['key']}]) \
                if story_task['key'] else {}

        response = self.jira_api.create_an_issue(
            payload={'fields': fields, 'update': update_link})

        if not response.ok:
            logger.warn('Failed to create task...')
            return

        id = json.loads(response.text)['id']

        # Update Epic
        self.jira_api.update_epic(epic=self.epic, issues_id=[id])
        return json.loads(response.text)

    def _get_story_task_by_tag(self):
        return self._api_get_story_task_by_tag(
            self.current_platform['platform_tag']
        )

    def _get_general_task_by_tag(self, tag=''):
        raise NotImplementedError(
            'not implement the _get_general_task_by_tag yet'
        )

    def _online_update_handler(self):
        """ Handle the procedure of creating Online Update Jira task
            Step:
                1. Check Online Update task doesn't exist
                    Won't create task if the Online Update task exists already
                2. Find a story task by Platfrom Tag (jellyfish-xxx)
                3. Create Online Update task
                    Link Online Update task to story task
        """
        self.current_stage = 'online_update'
        platforms = self.payload['online_update']
        for platform in platforms:
            self.current_platform = platform
            logger.info('Creating the Online Update task of "{}"'.format(
                platform['platform_tag']))

            try:
                # Step 1
                if self._get_general_task_by_tag():
                    logger.info('Skip because task has been created')
                    continue

                # Step 2
                story_task = self._get_story_task_by_tag()

                # Step 3
                prts_task = self._create_online_update_task(story_task)

                task = {
                    'platform_tag': platform['platform_tag'],
                    'prts_task_url': '{}/browse/{}'.format(
                        self.jira_api._base_url, prts_task['key']
                    )
                }
                logger.info(task)
            except NoRequestDate:
                logger.warn('Skip because no request_date data')
            except Exception as e:
                logger.error('Failed to create task since {}'.format(str(e)))
                logger.error(
                    traceback.print_exception(type(e), e, e.__traceback__))

    def _prts_handler(self):
        """ Handle the procedure of creating PRTS Jira task
            Step:
                1. Check PRTS task doesn't exist
                    Won't create task if the PRTS task exists already
                2. Find a story task by Platfrom Tag (jellyfish-xxx)
                3. Create PRTS task
                    Link PRTS task to story task if we have story task
        """
        self.current_stage = 'prts'
        platforms = self.payload['prts']
        for platform in platforms:
            self.current_platform = platform
            logger.info('Creating the PRTS task of "{}"'.format(
                platform['platform_tag']))

            try:
                # Step 1
                if self._get_general_task_by_tag():
                    logger.info('Skip because task has been created')
                    continue

                # Step 2
                story_task = self._get_story_task_by_tag()

                # Step 3
                prts_task = self._create_prts_task(story_task)

                task = {
                    'platform_tag': platform['platform_tag'],
                    'prts_task_url': '{}/browse/{}'.format(
                        self.jira_api._base_url, prts_task['key']
                    )
                }
                logger.info(task)
            except NoRequestDate:
                logger.warn('Skip because no request_date data')
            except Exception as e:
                logger.error('Failed to create task since {}'.format(str(e)))
                logger.error(
                    traceback.print_exception(type(e), e, e.__traceback__))

    def _rts_handler(self):
        """ Handle the procedure of creating RTS Jira task for each platform
            Step:
                1. Check story task doesn't exist
                    Won't create task if the story task exists already
                2. Create a story task for each platform
                3. Create different milestone task for each platform
                4. Create the transfer to cert task
        """

        self.current_stage = 'rts'
        platforms = self.payload['rts']

        for platform in platforms:
            self.current_platform = platform
            logger.info('Creating the task of "{}"'.format(
                platform['platform_tag']))
            try:
                # Step 1
                if self._get_story_task_by_tag():
                    logger.info('Skip because task has been created')
                    continue

                # Step 2
                story = self._create_story_task()

                # Step 3
                self._create_rts_task(story_task=story)

                # Step 4
                self._create_transfer_to_cert_task(story_task=story)

                task = {
                    'platform_tag': platform['platform_tag'],
                    'story_task_url': '{}/browse/{}'.format(
                        self.jira_api._base_url, story['key']
                    )
                }
                logger.info(task)
            except Exception as e:
                logger.error('Failed to create task')
                logger.error(
                    traceback.print_exception(type(e), e, e.__traceback__))

    def create_card(self):
        fn = {
            'rts': self._rts_handler,
            'prts': self._prts_handler,
            'online_update': self._online_update_handler
        }
        for stage in self.payload:
            if stage not in fn:
                logger.warn(
                    'Not implement the handler of \'{}\' yet'.format(stage))
                continue
            logger.info('-'*20 + stage + '-'*20)
            fn[stage]()


class SomervilleJira(QaPcJira):

    def __init__(self, payload, project='somerville'):
        super().__init__(payload, project)

    def _generate_general_card_prefix(self):
        """ Generate the more human readable platform_name in summary

            Parameters:
                platform_name {list}: A bounch of platform_name grouped
                                      by platform_tag

            Return {string}: Readable platform name
        """
        platform_name = self.current_platform['platform_name']

        if not platform_name:
            return ''
        if len(platform_name) == 1:
            return platform_name[0]

        title = ''
        # Keep the string till numeric
        platform = re.findall(r'(\D*)\d*.*', platform_name[0])[0].strip()
        # Keep the [] brackets
        platform = re.sub(r'\[', '\\[', platform)
        platform = re.sub(r'\]', '\\]', platform)
        for i in platform_name:
            # Remove the platform and (...)
            i = re.sub(rf'{platform}|\(+.*\)+', '', i).strip()
            title += i.strip() + ' /'
        platform = platform.replace('\\', '')
        title = '%s ' % (platform) + title[0:-1]
        return title

    def _generate_story_card_title(self):
        """ Return {string}: return the title name
        """
        return '{} ({})'.format(
            self._generate_general_card_prefix(),
            self.current_platform['platform_tag']
        )

    def _generate_rts_card_title(self, milestone=''):
        """ Return {string}: return the title name
        """
        return '{} ({}) {}'.format(
            self._generate_general_card_prefix(),
            self.current_platform['platform_tag'],
            milestone
        )

    def _generate_prts_card_title(self):
        """ Generate the PRTS card title
        """
        return '[PRTS] {} ({}) test'.format(
            self._generate_general_card_prefix(),
            self._generate_prts_or_online_update_tag()
        )

    def _generate_online_update_card_title(self):
        """ Generate the Online Update card title
        """
        return '[Online update] {} ({}) test'.format(
            self._generate_general_card_prefix(),
            self._generate_prts_or_online_update_tag()
        )

    def _generate_transfer_cert_card_title(self):
        """ Generate the transfer to cert card title
        """
        return '{} ({}) HW transfer to cert lab'.format(
            self._generate_general_card_prefix(),
            self.current_platform['platform_tag'],
        )

    def _generate_prts_or_online_update_tag(self):
        """ Generate the tag for PRTS or Online Update task
        """
        tag = '{}_{}_{}'.format(
            self.current_stage,
            self.current_platform['platform_tag'],
            self.current_platform['request_date']
        )
        return tag

    def _get_general_task_by_tag(self, tag=''):
        """ Get the task if it exists
        """
        current_stage = self.current_stage

        # We won't create the task if its request_date is empty
        # PRTS and Online Update have request_date data
        if current_stage != 'rts' and \
                not self.current_platform['request_date']:
            raise NoRequestDate()
        if not tag and current_stage != 'rts':
            tag = self._generate_prts_or_online_update_tag()
        return self._api_get_task_by_tag(tag)


class StellaJira(QaPcJira):

    def __init__(self, payload, project='stella'):
        super().__init__(payload, project)

    def _generate_story_card_title(self):
        """ Return {string}: return the title name
        """
        return '{} ({})'.format(
            self.current_platform['product_name'][0],
            self.current_platform['lp_tag']
        )

    def _generate_rts_card_title(self, milestone=''):
        """ Return {string}: return the title name
        """
        return '{} ({}) {} image test'.format(
            self.current_platform['product_name'][0],
            self.current_platform['lp_tag'],
            milestone
        )

    def _get_story_task_by_tag(self):
        return self._api_get_story_task_by_tag(
            self.current_platform['lp_tag'].replace('-prts', '')
        )

    def _generate_prts_card_title(self):
        """ Generate the PRTS card title
        """
        return '{} ({}) image test'.format(
            self.current_platform['product_name'][0],
            self.current_platform['lp_tag']
        )

    def _generate_transfer_cert_card_title(self):
        """ Generate the transfer to cert card title
        """
        return '{} ({}) HW transfer to cert lab'.format(
            self.current_platform['product_name'][0],
            self.current_platform['lp_tag'],
        )

    def _get_general_task_by_tag(self, tag=''):
        """ Get the task if it exists
        """
        return self._api_get_task_by_tag(self.current_platform['lp_tag'])

    def _online_update_handler(self):
        """ Won't accept the Online Update request since the online Update
            task won't be recorded on Stella's projectbook.
        """
        logger.info(
            'Won\'t accept the Online Update request since the '
            'online Update task won\'t be recorded on the projectbook.'
        )


class SuttonJira(QaPcJira):

    def __init__(self, payload, project='sutton'):
        super().__init__(payload, project)

    def _generate_story_card_title(self):
        """ Return {string}: return the title name
        """
        return '{} ({} {})'.format(
            self.current_platform['platform_name'][0],
            self.current_platform['product_name'][0],
            self.current_platform['platform_tag']
        )

    def _generate_rts_card_title(self, milestone=''):
        """ Return {string}: return the title name
        """
        return '{} ({} {}) {}'.format(
            self.current_platform['platform_name'][0],
            self.current_platform['product_name'][0],
            self.current_platform['platform_tag'],
            milestone
        )

    def _get_story_task_by_tag(self):
        tag = '{} {}'.format(
            self.current_platform['product_name'][0],
            self.current_platform['platform_tag']
        )
        return self._api_get_story_task_by_tag(tag)

    def _generate_prts_card_title(self):
        """ Generate the PRTS card title
        """
        return '[Sutton] {} ({}) test'.format(
            self.current_platform['product_name'][0],
            self._generate_prts_tag()
        )

    def _generate_prts_tag(self):
        """ Generate the tag for Refresh task
        """
        platform = self.current_platform['platform_name'][0].replace(' ', '-')
        product = self.current_platform['product_name'].replace(' ', '-')
        tag = '{}_{}'.format(platform, product)
        return tag

    def _generate_transfer_cert_card_title(self):
        """ Generate the transfer to cert card title
        """
        return '{} ({} {}) HW transfer to cert lab'.format(
            self.current_platform['platform_name'][0],
            self.current_platform['product_name'][0],
            self.current_platform['platform_tag']
        )

    def _get_general_task_by_tag(self, tag=''):
        """ Get the task if it exists
        """
        # No need to distinguish the prts and online update stage
        # because the stage string won't appear at the tag on title
        tag = tag if tag else self._generate_prts_tag()
        return self._api_get_task_by_tag(tag)

    def _online_update_handler(self):
        """ Won't accept the Online Update request since the online Update
            task won't be recorded on Sutton's projectbook.
        """
        logger.info(
            'Won\'t accept the Online Update request since the '
            'online Update task won\'t be recorded on the projectbook.'
        )


def create_task_card(payload):
    """ Create tasks for each platform on different project

        Parameters:
            payload {dist}: Must needed information of each project

        Return {dist}
            e.g.
                {
                    'somerville': {
                        'rts': [
                            {
                                'platform_tag': 'fossa-marill',
                                'story_task_link':
                                'https://warthogs.atlassian.net/browse/VS-718',
                            }
                        ].
                        'prts': [],
                        'online_update': []
                    }
                    'stella': {}
                    'sutton': {}
                }
    """
    import sys
    import inspect

    fn = {}
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj):
            fn[name] = obj

    for project in payload:
        p = project.capitalize()
        logger.info('='*20 + ' Project: {} '.format(p) + '='*20)
        project_class = '{}Jira'.format(p)
        target_class = project_class if project_class in fn else 'QaPcJira'
        try:
            # ex: SomervilleJira(payload['somerville']).create_card()
            fn[target_class](payload[project]).create_card()
        except Exception as e:
            logger.error(e)
