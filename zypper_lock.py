#! /usr/bin/env python3

# Based on dnf_versionlock.py:
# Copyright (c) 2021, Roberto Moreda <moreda@allenta.com>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (c) 2023, Marcus Lauer <melauer@seas.upenn.edu> and the School of Engineering and Applied Science (SEAS)
# at the University of Pennsylvania.

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: zypper_lock

short_description: Lock and unlock packages in the C(zypper) package manager.

description: The C(zypper) package manager has support for Package Locks Management
which prevents packages from being updated by locking them. This module is a
simple interface to C(zypper) locks management. It takes a list of strings and passes
them to "C(zypper) addlock" or "C(zypper) removelock". Presumably the strings are package
names, but any string which can be understood by C(zypper) will work.

options:
  name:
    description: Names of packages to add or delete from the C(locklist).
    type: list
    required: false
    elements: str
    default: []
  state:
    description:
      - Whether to add (C(present)) to or remove (C(absent)) specified packages from the locklist.
      - C(present) will add a package name spec to the locklist.
      - C(absent) will remove a package name spec from the locklist.
      - C(list) will return the list of currently locked packages in 'initial_locklist'.
      - C(purge) will remove all packages from the locklist.
    choices: [ 'absent', 'present', 'list', 'purge' ]
    type: str
    default: present
  pkgtype:
    description:
      - Type of package to lock.
      - Types come from the Package Types section of the C(zypper) manual.
      - If not given, no -t argument will be passed to the C(zypper) command.
      - Currently C(zypper) defaults to 'package'.
    choices: ['package', 'patch', 'pattern', 'product', 'srcpackage']
    type: str
    default: None
  repo:
    description:
      - Restrict locks to given repository.
      - Argument can be an alias, name, number, or URI.
      - If not given, no -r argument will be passed to the C(zypper) command.
    type: str
    default: None
  message:
    description:
      - Add a message to a lock.
      - Argument should be a quoted string.
      - If not given, no -m argument will be passed to the C(zypper) command.
author:
    - Marcus Lauer <melauer@seas.upenn.edu>

'''

EXAMPLES = r'''
# Lock a package.
- name: Prevent tcsh from being updated.
  zypper_lock:
    name: 'tcsh'
    state: present

- name: Prevent the kernel source srcpackage from being updated.
  zypper_lock:
    name: 'kernel-source'
    pkgtype: srcpackage
    state: present

- name: Lock a package and specify the repo which the lock affects.
  zypper_lock:
    name: 'fuse3'
    repo: 'filesystems'
    state: present

- name: Lock a package a add a message to the lock.
  zypper_lock:
    name: 'zypper'
    message: "Do not upgrade zypper"

# Unlock several packages.
- name: Unlock all installed shells.
  zypper_lock:
    name: ['bash', 'ksh', 'tcsh', 'zsh']
    state: absent

# Remove all locked packages.
  zypper_lock:
    state: purge

# Get a list of all locked packages.
  zypper_lock:
    state: list
  register: list_of_locked_packages
'''

RETURN = r'''
initial_locklist:
    description: Locklist before module execution.
    returned: always
    type: list
    elements: str
    sample: [ 'bash', 'zsh' ]
final_locklist:
    description: Locklist after module execution.
    returned: success
    type: list
    elements: str
    sample: [ 'bash' ]
patterns_to_add:
    description: Package names to be locked.
    returned: success
    type: list
    elements: str
    sample: [ 'tcsh' ]
patterns_to_delete:
    description: Package names to be unlocked.
    returned: success
    type: list
    elements: str
    sample: [ 'zsh' ]
'''

from ansible.module_utils.basic import AnsibleModule
import os
import re

ZYPPER_CMD = "/usr/bin/zypper"
PACKAGE_RE = re.compile("^\d+\ +\| ([^\|\ ]*)")

def zypper_lock(module, command, patterns=None):
    output = []

    if patterns is not None:
        full_command_arr = [ZYPPER_CMD, "--quiet"] + command + patterns
        rc, out, err = module.run_command( full_command_arr, check_rc=True )
        output.append(out)
    else:
        full_command_arr = [ZYPPER_CMD] + command
        rc, out, err = module.run_command( full_command_arr, check_rc=True )
        for line in out.split("\n"):
            package = PACKAGE_RE.match(line)
            if package is not None:
                output.append(package[1])

    result = "\n".join(output)
    return result

def process_options(options, command):
    result = command

    if command[0] in ["addlock","removelock"]:
        if options["pkgtype"] in ["package","patch","pattern","product","srcpackage"]:
            result.append("-t")
            result.append(options['pkgtype'])
        if options["repo"] is not None:
            result.append("-r")
            result.append(options['repo'])
    if command[0] in ["addlock"]:
        if options["message"] is not None:
            result.append("-m")
            result.append(options['message'])

    return result

def main():
    # Check that the required files exist.
    if not os.path.isfile(ZYPPER_CMD) and os.access(ZYPPER_CMD, os.X_OK):
        module.fail_json(f"Cannot find {ZYPPER_CMD}")

    # Create the Ansible Module.
    module = AnsibleModule(
        argument_spec = dict(
            name = dict(type="list", elements="str", default=[]),
            state = dict(type="str", default="present", choices=["present", "absent", "list", "purge"]),
            pkgtype = dict(type="str", choices=["package", "patch", "pattern", "product", "srcpackage"]),
            repo = dict(type="str"),
            message = dict(type="str")
        ),
        supports_check_mode=True
    )

    # Set up some variables.
    patterns = module.params["name"]
    state = module.params["state"]
    options = dict(
        pkgtype=module.params["pkgtype"],
        repo=module.params["repo"],
        message=module.params["message"]
    )

    changed = False
    msg = ""

    # Get the list of packages which are currently locked.
    initial_locklist = zypper_lock(module, ["locks"]).split("\n")

    # Add or remove packages, but only if necessary.
    patterns_to_add = []
    patterns_to_delete = []

    if state in ["present"]:
        for p in patterns:
            if p not in initial_locklist:
                patterns_to_add.append(p)
                if module.check_mode:
                    changed = True

        if patterns_to_add and not module.check_mode:
            zypper_command = process_options(options, ["addlock"])
            msg = zypper_lock(module, zypper_command, patterns_to_add)
            changed = True

    elif state in ["absent"]:
        for p in patterns:
            if p in initial_locklist:
                patterns_to_delete.append(p)
                if module.check_mode:
                    changed = True

        if patterns_to_delete and not module.check_mode:
            zypper_command = process_options(options, ["removelock"])
            msg = zypper_lock(module, zypper_command, patterns_to_delete)
            changed = True

    elif state in ["purge"]:
        patterns_to_delete = initial_locklist
        if patterns_to_delete and not module.check_mode:
            zypper_command = process_options(options, ["removelock"])
            # Instead of having to keep track of which repo each pattern is in, just remove all indexes from last to first.
            indexes_to_delete = [f'{x}' for x in reversed(range(1, len(patterns_to_delete)+1))]
            msg = zypper_lock(module, zypper_command, indexes_to_delete)
            changed = True

    # Get a list of changes.
    if module.check_mode or state in ["list"]:
        final_locklist = initial_locklist
    else:
        final_locklist = zypper_lock(module, ["locks"]).split("\n")

    # Output a result.
    response = {
        "changed": changed,
        "msg": msg,
        "initial_locklist": initial_locklist,
        "final_locklist": final_locklist,
        "patterns_to_add": patterns_to_add,
        "patterns_to_delete": patterns_to_delete
    }

    module.exit_json(**response)

if __name__ == "__main__":
    main()
