#!/usr/bin/python
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import pprint
import sys
import time
import webbrowser

import googleapiclient.discovery
import googleapiclient.errors
import googleapiclient.http
import httplib2
import oauth2client.client
from redis import Redis
from rq import Queue

from ownership import grant_ownership

async_results = {}
redis_conn = Redis()
q = Queue(connection=redis_conn)
r = Redis(host='localhost', port=6379, db=1)


def get_drive_service():
    OAUTH2_SCOPE = 'https://www.googleapis.com/auth/drive'
    CLIENT_SECRETS = 'client_secrets.json'
    flow = oauth2client.client.flow_from_clientsecrets(CLIENT_SECRETS, OAUTH2_SCOPE)
    flow.redirect_uri = oauth2client.client.OOB_CALLBACK_URN
    authorize_url = flow.step1_get_authorize_url()
    webbrowser.open(authorize_url)
    print('Link for authorization: {}'.format(authorize_url))
    if sys.version_info[0] > 2:
        code = input('Verification code: ').strip()
    else:
        code = raw_input('Verification code: ').strip()
    credentials = flow.step2_exchange(code)
    http = httplib2.Http()
    credentials.authorize(http)
    drive_service = googleapiclient.discovery.build('drive', 'v2', http=http)
    return drive_service


def get_permission_id_for_email(service, email):
    try:
        id_resp = service.permissions().getIdForEmail(email=email).execute()
        return id_resp['id']
    except googleapiclient.errors.HttpError as e:
        print('An error occured: {}'.format(e))


def show_info(service, drive_item, prefix, permission_id):
    try:
        print(os.path.join(prefix, drive_item['title']))
        print('Would set new owner to {}.'.format(permission_id))
    except KeyError:
        print('No title for this item:')
        pprint.pprint(drive_item)


def process_all_files(service, callback=None, callback_args=None, minimum_prefix=None, current_prefix=None,
                      folder_id='root'):
    if minimum_prefix is None:
        minimum_prefix = []
    if current_prefix is None:
        current_prefix = []
    if callback_args is None:
        callback_args = []

    print('Gathering file listings for prefix {}...'.format(current_prefix))

    page_token = None
    while True:
        try:
            param = {}
            if page_token:
                param['pageToken'] = page_token
            children = service.children().list(folderId=folder_id, **param).execute()
            for child in children.get('items', []):
                item = service.files().get(fileId=child['id']).execute()
                #pprint.pprint(item)
                if item['kind'] == 'drive#file':
                    if current_prefix[:len(minimum_prefix)] == minimum_prefix:
                        print(u'File: {} ({}, {})'.format(item['title'], current_prefix, item['id']))
                        # callback(service, item, current_prefix, **callback_args)
                        q.enqueue(callback, args=(service, item, current_prefix), kwargs=callback_args)
                    if item['mimeType'] == 'application/vnd.google-apps.folder':
                        if r.get(item['id']) is None:  # already finished
                            print(u'Folder: {} ({}, {})'.format(item['title'], current_prefix, item['id']))
                            next_prefix = current_prefix + [item['title']]
                            comparison_length = min(len(next_prefix), len(minimum_prefix))

                            if minimum_prefix[:comparison_length] == next_prefix[:comparison_length]:
                                process_all_files(service, callback, callback_args, minimum_prefix, next_prefix,
                                                  item['id'])
                                r.set(item['id'], 1)  # marked as finished
            page_token = children.get('nextPageToken')
            if not page_token:
                break
        except googleapiclient.errors.HttpError as e:
            print('An error occurred: {}'.format(e))
            break


def check_remaining():
    start_time = time.time()
    i = 0
    total = len(async_results)
    while i < total:
        os.system('clear')
        print('All jobs are enqueued.')
        print('Asynchronously: (now = %.2f)' % (time.time() - start_time,))
        for result in async_results:
            value = result.return_value
            if value is not None:
                i += 1
        print('{} of {} completed.'.format(i, total))
        time.sleep(0.2)

    print('Done')


if __name__ == '__main__':
    if sys.version_info[0] > 2:
        minimum_prefix = sys.argv[1]
        new_owner = sys.argv[2]
        show_already_owned = False if len(sys.argv) > 3 and sys.argv[3] == 'false' else True
    else:
        minimum_prefix = sys.argv[1].decode('utf-8')
        new_owner = sys.argv[2].decode('utf-8')
        show_already_owned = False if len(sys.argv) > 3 and sys.argv[3].decode('utf-8') == 'false' else True
    print('Changing all files at path "{}" to owner "{}"'.format(minimum_prefix, new_owner))
    minimum_prefix_split = minimum_prefix.split(os.path.sep)
    print('Prefix: {}'.format(minimum_prefix_split))
    service = get_drive_service()
    permission_id = get_permission_id_for_email(service, new_owner)
    print('User {} is permission ID {}.'.format(new_owner, permission_id))
    process_all_files(service, grant_ownership,
                      {'permission_id': permission_id, 'show_already_owned': show_already_owned},
                      minimum_prefix_split)
    check_remaining()
    # print(files)
