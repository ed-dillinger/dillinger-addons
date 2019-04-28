#ED Dillinger Repository

Repository managed by build_repo.py
build_repo is a configurable python script for automating management of a kodi repository hosted on a git server.

See https://github.com/ed-dillinger/build_repo

Usage: build_repo.py [options]

Options:
  -h, --help            show this help message and exit
  -a ADDONID, --addon=ADDONID
                        Build a single specific Addon ID
  -b BUILDID, --build=BUILDID
                        Build a single specific Addon ID
  -l, --list            Print List Addons of addons and exit
  -i                    Full Interative mode, default mode
  -d, --dry-run         Dry Run, Do not write any files or make commits
  -v, --verbose         Verbose output


Configuration is through ./config/config.txt
See ./config/config.txt for configuration details.

Interactive mode prompts for each configured ADDONID to compiled and the new version number.
Addon versions are maintained through a versions file, ./config/versions.json.

Version prompts may be entered manually or incremented:
	x.x.x: specify a specific version number
	+: increment minor version x.x.(x+1)
	++: increment major version x.(x+1).0
	+++: increment build version (x+1).0.0

Finally changes are commited and pushed.
