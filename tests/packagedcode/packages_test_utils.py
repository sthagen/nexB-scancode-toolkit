#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/scancode-toolkit for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import os

from commoncode import testcase
from commoncode import text


class PackageTester(testcase.FileBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'data')

    def check_package_parse(
        self,
        package_function,
        manifest_loc,
        expected_loc,
        regen=False,
    ):
        """
        Helper to test the creation of a package object with ``package_function``
        and test it against an expected JSON file.
        """
        manifest_loc = self.get_test_loc(manifest_loc, must_exist=True)
        package = package_function(manifest_loc)
        if not package:
            raise Exception(f'Failed to parse package: {manifest_loc}')
        return self.check_package(package, expected_loc, regen)

    def check_package(self, package, expected_loc, regen=False):
        """
        Helper to test a package object against an expected JSON file.
        """

        package.license_expression = package.compute_normalized_license()
        results = package.to_dict()

        expected_loc = self.get_test_loc(expected_loc, must_exist=False)
        check_result_equals_expected_json(
            result=results,
            expected_loc=expected_loc,
            regen=regen,
        )

    def check_packages(self, packages, expected_loc, regen=False):
        """
        Helper to test a list of package objects against an expected JSON file.
        """
        expected_loc = self.get_test_loc(expected_loc)

        results = []
        for package in packages:
            package.license_expression = package.compute_normalized_license()
            results.append(package.to_dict())

        check_result_equals_expected_json(
            result=results,
            expected_loc=expected_loc,
            regen=regen,
        )


def check_result_equals_expected_json(result, expected_loc, regen=False):
    """
    Check equality between a result collection and the data in an expected_loc
    JSON file. Regen the expected file if regen is True.
    """
    if regen:
        expected = result

        expected_dir = os.path.dirname(expected_loc)
        if not os.path.exists(expected_dir):
            os.makedirs(expected_dir)

        with open(expected_loc, 'w') as ex:
            json.dump(expected, ex, indent=2, separators=(',', ': '))
    else:
        with open(expected_loc) as ex:
            expected = json.load(ex)

    assert result == expected


def get_test_files(location, test_file_suffix):
    """
    Walk directory at ``location`` and yield location-relative paths to test
    files matching ``test_file_suffix``).
    """

    # NOTE we do not use commoncode here as we want NO files spkipped for testing
    for base_dir, _dirs, files in os.walk(location):
        for file_name in files:
            if not file_name.endswith(test_file_suffix):
                continue

            file_path = os.path.join(base_dir, file_name)
            file_path = file_path.replace(location, '', 1)
            file_path = file_path.strip(os.path.sep)
            yield file_path


def create_test_function(
    manifest_loc,
    package_function,
    test_name,
    expected_loc,
    regen=False,
):
    """
    Return a test function closed on test arguments to run
    `tested_function(manifest_loc)`.
    """

    def test_package(self):
        self.check_package_parse(
            package_function=package_function,
            manifest_loc=manifest_loc,
            expected_loc=expected_loc,
            regen=regen,
        )

    test_package.__name__ = test_name
    return test_package


def build_tests(
    test_dir,
    clazz,
    test_method_prefix,
    package_function,
    test_file_suffix,
    regen=False,
):
    """
    Dynamically build test methods from package manifest file in ``test_dir``
    and attach a test method to the ``clazz`` test subclass of PackageTester.

    For each method:
    - run ``package_function`` with a manifest test file with``test_file_suffix``
      ``package_function`` should return a Package object.
    - set the name prefixed with ``test_method_prefix``.
    - check that a test expected file named `test_file_name-expected.json`
      has content matching the results of the ``package_function`` run.
    """
    assert issubclass(clazz, PackageTester)

    print('test_dir', test_dir)
    # loop through all items and attach a test method to our test class
    for test_file_path in get_test_files(test_dir, test_file_suffix):
        test_name = test_method_prefix + text.python_safe_name(test_file_path)
        manifest_loc = os.path.join(test_dir, test_file_path)

        test_method = create_test_function(
            manifest_loc=manifest_loc,
            package_function=package_function,
            test_name=test_name,
            expected_loc=manifest_loc + '-expected.json',
            regen=regen,
        )
        setattr(clazz, test_name, test_method)
