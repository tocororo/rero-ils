#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2019 RERO
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

# COLORS for messages
NC='\033[0m'                    # Default color
INFO_COLOR='\033[1;97;44m'      # Bold + white + blue background
SUCCESS_COLOR='\033[1;97;42m'   # Bold + white + green background
ERROR_COLOR='\033[1;97;41m'     # Bold + white + red background

PROGRAM=`basename $0`
SCRIPT_PATH=$(dirname "$0")

# MESSAGES
msg() {
  echo -e "${1}" 1>&2
}
# Display a colored message
# More info: https://misc.flogisoft.com/bash/tip_colors_and_formatting
# $1: choosen color
# $2: title
# $3: the message
colored_msg() {
  msg "${1}[${2}]: ${3}${NC}"
}

info_msg() {
  colored_msg "${INFO_COLOR}" "INFO" "${1}"
}

error_msg() {
  colored_msg "${ERROR_COLOR}" "ERROR" "${1}"
}

error_msg+exit() {
    error_msg "${1}" && exit 1
}

success_msg() {
  colored_msg "${SUCCESS_COLOR}" "SUCCESS" "${1}"
}

success_msg+exit() {
  colored_msg "${SUCCESS_COLOR}" "SUCCESS" "${1}" && exit 0
}

# Displays program name
msg "PROGRAM: ${PROGRAM}"

# Poetry is a mandatory condition to launch this program!
if [[ -z "${VIRTUAL_ENV}" ]]; then
  error_msg+exit "Error - Launch this script via poetry command:\n\tpoetry run ${PROGRAM}"
fi

function pretests () {
  info_msg "Check vulnerabilities:"
  # +============================+===========+==========================+==========+
  # | package                    | installed | affected                 | ID       |
  # +============================+===========+==========================+==========+
  # | click                      | 7.1.2     | <8.0.0                   | 47833    |
  # | celery                     | 5.1.2     | <5.2.0                   | 42498    |
  # | celery                     | 5.1.2     | <5.2.2                   | 43738    |
  # | flask-security             | 3.0.0     | <3.1.0                   | 45183    |
  # | flask-security             | 3.0.0     | >0                       | 44501    |
  # | wtforms                    | 2.3.3     | <3.0.0a1                 | 42852    |
  # | py                         | 1.11.0    | <=1.11.0                 | 51457    |
  # | safety                     | 1.10.3    | <2.2.0                   | 51358    |
  # | sqlalchemy                 | 1.3.24    | <2.0.0b1                 | 51668    |
  # | wheel                      | 0.37.1    | <0.38.0                  | 51499    |
  # | sqlalchemy-utils           | 0.35.0    | >=0.27.0                 | 42194    |
  # | certifi                    | 2022.9.24 | <2022.12.07              | 52365    |
  # | setuptools                 | 65.4.1    | <65.5.1                  | 52495    |
  # | future                     | 0.18.2    | <=0.18.2                 | 52510    |
  # +==============================================================================+
  safety check -i 47833 -i 42498 -i 43738 -i 45183 -i 44501 -i 42852 -i 51457 -i 51358 -i 51499 -i 42194 -i 51668 -i 52365 -i 52495 -i 52510
  info_msg "Check json:"
  invenio reroils utils check_json tests/data rero_ils/modules data
  info_msg "Check license:"
  invenio reroils utils check_license check_license_config.yml
  info_msg "Test pydocstyle:"
  pydocstyle rero_ils tests docs
  info_msg "Test isort:"
  isort --check-only --diff "${SCRIPT_PATH}"
  info_msg "Test useless imports:"
  autoflake -c -r --remove-all-unused-imports --ignore-init-module-imports . &> /dev/null || {
    autoflake --remove-all-unused-imports -r --ignore-init-module-imports .
    exit 1
  }
  # info_msg "Check-manifest:"
  # TODO: check if this is required when rero-ils will be published
  # check-manifest --ignore ".travis-*,docs/_build*"
  info_msg "Sphinx-build:"
  sphinx-build -qnNW docs docs/_build/html
}

function tests () {
  info_msg "Tests All:"
  poetry run pytest
}

function tests_api () {
  info_msg "Tests API:"
  poetry run pytest ./tests/api
}
function tests_e2e () {
  info_msg "Tests E2E:"
  poetry run pytest ./tests/e2e
}
function tests_scheduler () {
  info_msg "Tests Scheduler:"
  poetry run pytest ./tests/scheduler
}
function tests_ui () {
  info_msg "Tests UI:"
  poetry run pytest ./tests/ui
}
function tests_unit () {
  info_msg "Tests Unit:"
  poetry run pytest ./tests/unit
}
function tests_external () {
  info_msg "Tests External:"
  poetry run pytest tests/api/test_external_services.py
}
function tests_other () {
  info_msg "Tests Other:"
  poetry run pytest ./tests/conftest.py ./tests/test_version.py ./tests/utils.py
}

if [ $# -eq 0 ]
  then
    set -e
    pretests
    tests
fi

if [ "$1" = "other" ]
  then
    set -e
    pretests
    tests_other
fi
if [ "$1" = "api" ]
  then
    set -e
    tests_api
fi
if [ "$1" = "e2e" ]
  then
    set -e
    tests_e2e
fi
if [ "$1" = "scheduler" ]
  then
    set -e
    tests_scheduler
fi
if [ "$1" = "ui" ]
  then
    set -e
    tests_ui
fi
if [ "$1" = "unit" ]
  then
    set -e
    tests_unit
fi
if [ "$1" = "external" ]
  then
    set -e
    tests_external
fi

success_msg+exit "Perfect ${PROGRAM} external! See you soon…"
