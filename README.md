ED Dillinger Repository
Repository managed by build_repo.py
build_repo is a short python script for automating management of a small kodi repository hosted on a git server.
Usage: build_repo.py [options]

Options:
  -h, --help            show this help message and exit
  -a ADDONID, --addon=ADDONID
                        Specify a single Addon ID
  -b BUILDID, --build=BUILDID
                        Build a specific Addon ID
  -l, --list            List Addons
  -i                    Full Interative mode

Configuration is through ./config.txt
See ./config.txt for configuration details.

Interactive mode prompts for each configured ADDONID to compiled and the new version number.
Finally changes are commited and pushed.
