import os
import sys

from external import Storage
from transfer import get_drive_credentials, run


def main():
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
    credentials = get_drive_credentials()
    q = Storage.instance().queue
    q.enqueue(run, args=(credentials, minimum_prefix_split, new_owner, show_already_owned))


if __name__ == '__main__':
    main()
