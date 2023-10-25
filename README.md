# zypper_lock
zypper_lock.py: An Ansible module for managing zypper locklists.

The zypper package manager used by SUSE Linux includes package locking functionality. It maintains a list of package specifications and will not install or update packages which match those specifications. See the "Package Locks Management" of the manual page for zypper for more information.

This module allows Ansible to control the zypper lock list. At this time it supports adding ("present") and removing ("absent") specifications from the list. It can also be used to return a list of package specifications which are currently locked ("list") or to remove all specifications from the locklist ("purge"). The module does not currently support the "-t" (type) or "-r" (repository) arguments though that support will likely be added in the future.

The zypper_lock.py module is based on dnf_versionlock.py by Roberto Moreda and like that module is released under the GNU General Public License v3.0+ (see https://spdx.org/licenses/GPL-3.0-or-later.html or https://www.gnu.org/licenses/gpl-3.0.txt).
