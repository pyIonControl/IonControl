from pint.testsuite import QuantityTestCase

from modules.quantity import Q


class TestQuantity(QuantityTestCase):
    def test_hash(self):
        self.assertEqual(hash(Q(12, 'ms')), hash(Q(12, 'ms')))

    def test_times(self):
        q = Q(1, 'hr') / Q(30, 'min')
        self.assertEqual(q, Q(2))

    def test_infer_base_unit(self):
        from pint.util import infer_base_unit
        self.assertEqual(infer_base_unit(Q(1, 'millimeter / second')), Q(1, 'meter / second').units)
        self.assertEqual(infer_base_unit(Q(1, 'millimeter * nanometer')), Q(1, 'meter**2').units)

    def test_simplify(self):
        self.assertQuantityAlmostEqual((Q(10, 'kg') * Q(1, 'm') / Q(1000, 's**2')), Q(10, 'mN'))
        self.assertQuantityAlmostEqual(Q(10, 'kg') * Q(1, 'm**2') / Q(1, 's**2'), Q(10, 'J'))
        self.assertQuantityAlmostEqual(Q(1, "V*m*kg/s**2"), Q(1, 'N * V'))
        self.assertQuantityAlmostEqual(Q(1, 'nm * um * km / pm'), Q(1, 'm**2'))
        self.assertQuantityAlmostEqual(Q(10, 'kg') * Q(1, 'm') / Q(1000, 's**2') / Q(10, 'meter**2'), Q(1, 'mPa'))
        self.assertQuantityAlmostEqual(Q(10, 'kg') * Q(1, 'm**2') / Q(1000, 's'), Q(10, 'mJ * s'))

    def test_to_compact(self):
        print(Q(-3300, 'Hz').to_compact())

