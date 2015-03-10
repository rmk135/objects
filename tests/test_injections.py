"""Objects injections unittests."""

import unittest2 as unittest
from objects.injections import Injection


class InjectionTest(unittest.TestCase):

    """Injection test cases."""

    def test_init(self):
        """Test Injection creation and initialization."""
        injection = Injection('some_arg_name', 'some_value')

        self.assertEqual(injection.name, 'some_arg_name')
        self.assertEqual(injection.injectable, 'some_value')
