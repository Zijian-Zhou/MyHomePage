import os
import pwd
import sys


def _prepare_writable_tree(path, uid, gid):
    os.makedirs(path, exist_ok=True)
    targets = [path]
    for root, directories, files in os.walk(path, followlinks=False):
        targets.extend(os.path.join(root, name) for name in directories)
        targets.extend(os.path.join(root, name) for name in files)

    for target in targets:
        try:
            os.chown(target, uid, gid, follow_symlinks=False)
        except (NotImplementedError, OSError):
            # Docker Desktop bind mounts may not implement Unix ownership.
            pass


def _drop_privileges(username):
    account = pwd.getpwnam(username)
    if os.getenv('FIX_VOLUME_PERMISSIONS', '').lower() in {'1', 'true', 'yes', 'on'}:
        _prepare_writable_tree('/data', account.pw_uid, account.pw_gid)
        _prepare_writable_tree('/app/media', account.pw_uid, account.pw_gid)

    os.initgroups(account.pw_name, account.pw_gid)
    os.setgid(account.pw_gid)
    os.setuid(account.pw_uid)
    os.environ['HOME'] = account.pw_dir


def main():
    if len(sys.argv) < 2:
        raise SystemExit('No container command was provided.')
    if os.geteuid() == 0:
        _drop_privileges('django')
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == '__main__':
    main()
