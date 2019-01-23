import googleapiclient.errors
import os


def grant_ownership(service, drive_item, prefix, permission_id, show_already_owned):
    full_path = os.path.join(os.path.sep.join(prefix), drive_item['title']).encode('utf-8', 'replace')

    # pprint.pprint(drive_item)

    current_user_owns = False
    for owner in drive_item['owners']:
        if owner['permissionId'] == permission_id:
            if show_already_owned:
                print('Item {} already has the right owner.'.format(full_path))
            return
        elif owner['isAuthenticatedUser']:
            current_user_owns = True

    print('Item {} needs ownership granted.'.format(full_path))

    if not current_user_owns:
        print('    But, current user does not own the item.'.format(full_path))
        return

    try:
        permission = service.permissions().get(fileId=drive_item['id'], permissionId=permission_id).execute()
        permission['role'] = 'owner'
        print('    Upgrading existing permissions to ownership.')
        return service.permissions().update(fileId=drive_item['id'], permissionId=permission_id, body=permission,
                                            transferOwnership=True).execute()
    except googleapiclient.errors.HttpError as e:
        if e.resp.status != 404:
            raise googleapiclient.errors.HttpError('An error occurred updating ownership permissions: {}'.format(e))

    print('    Creating new ownership permissions.')
    permission = {'role': 'owner',
                  'type': 'user',
                  'id': permission_id}
    try:
        service.permissions().insert(fileId=drive_item['id'], body=permission,
                                     emailMessage='Automated recursive transfer of ownership.').execute()
    except googleapiclient.errors.HttpError as e:
        raise googleapiclient.errors.HttpError('An error occurred inserting ownership permissions: {}'.format(e))
