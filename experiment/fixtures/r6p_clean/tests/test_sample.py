import unittest

import sample


class SampleTests(unittest.TestCase):
    def test_value_is_fixed(self):
        self.assertEqual(2, sample.VALUE)


if __name__ == "__main__":
    unittest.main()
