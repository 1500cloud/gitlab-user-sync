# gitlab-user-sync: synchronises users between G Suite and a GitLab group
# Copyright (C) 2019 1500 Services Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging

from gitlab import Gitlab, DEVELOPER_ACCESS
from google.oauth2 import service_account
from googleapiclient.discovery import build

LOGGER = logging.getLogger(__name__)
DEFAULT_ACCESS_LEVEL = DEVELOPER_ACCESS
GITLAB_INSTANCE = 'https://gitlab.com/'


def build_directory_service(service_account_file_path, administrator_email):
    credentials = service_account.Credentials.from_service_account_file(
        service_account_file_path,
        scopes=['https://www.googleapis.com/auth/admin.directory.user.readonly']
    ).with_subject(administrator_email)

    return build('admin', 'directory_v1', credentials=credentials)


def fetch_expected_gitlab_users(directory_service, customer_id):
    expected_users = {}
    request = directory_service.users().list(
        customer=customer_id,
        projection='full',
        query='isSuspended=false',
    )
    while request is not None:
        response = request.execute()
        expected_users.update({
            user['customSchemas']['External_Services']['GitLab_username']: user['primaryEmail']
            for user in response.get('users', [])
            if user['customSchemas'].get('External_Services', {}).get('GitLab_username') is not None
        })
        request = directory_service.users().list_next(request, response)
    return expected_users


def build_gitlab_service(access_token):
    gitlab = Gitlab(GITLAB_INSTANCE, private_token=access_token)
    return gitlab


def fetch_actual_gitlab_users(group):
    members = group.members.all(all=True)
    return {member['username']: member['id'] for member in members}


def main(google_credentials_path, google_administrator_email, google_customer_id, gitlab_access_token, gitlab_group_id):
    directory_service = build_directory_service(google_credentials_path, google_administrator_email)
    gitlab_service = build_gitlab_service(gitlab_access_token)
    gitlab_group = gitlab_service.groups.get(gitlab_group_id)

    gsuite_users = fetch_expected_gitlab_users(directory_service, google_customer_id)
    gitlab_members = fetch_actual_gitlab_users(gitlab_group)

    if len(set(gsuite_users.keys()) & set(gitlab_members.keys())) == 0:
        raise RuntimeError(
            "There are no users in common between the G Suite Directory and GitLab. Refusing to do anything, "
            "as this is likely to lead to losing access to the GitLab account "
        )

    for user_to_remove in set(gitlab_members.keys()) - set(gsuite_users.keys()):
        LOGGER.info(
            "Removing user {} from GitLab group {} (no corresponding directory entry)".format(user_to_remove, gitlab_group.name)
        )
        gitlab_group.members.delete(gitlab_members[user_to_remove])

    for user_to_add in set(gsuite_users.keys()) - set(gitlab_members.keys()):
        gitlab_user = gitlab_service.users.list(username=user_to_add)
        if len(gitlab_user) == 0:
            LOGGER.warning(
                'GitLab user {} for {} was not found in GitLab'.format(user_to_add, gsuite_users[user_to_add])
            )
            continue

        LOGGER.info(
            "Adding user {} to GitLab group {} (belonging to {})".format(user_to_add, gitlab_group.name, gsuite_users[user_to_add])
        )
        gitlab_group.members.create({'user_id': gitlab_user[0].id, 'access_level': DEFAULT_ACCESS_LEVEL})

