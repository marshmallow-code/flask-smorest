from collections import OrderedDict

from flask_rest_api.etag import generate_etag


class TestEtag():

    def test_etag_is_deterministic(self):
        """Check etag computation is deterministic

           generate_etag should return the same value everytime the same
           dictionary is passed. This is not obvious since dictionaries
           are unordered by design. We check this by feeding it different
           OrderedDict instances that are equivalent to the same dictionary.
        """

        data = OrderedDict([
            ('a', 1),
            ('b', 2),
            ('c', OrderedDict([('a', 1), ('b', 2)]))
        ])
        etag = generate_etag(data)

        data_copies = [
            OrderedDict([
                ('b', 2),
                ('a', 1),
                ('c', OrderedDict([('a', 1), ('b', 2)])),
            ]),
            OrderedDict([
                ('a', 1),
                ('b', 2),
                ('c', OrderedDict([('b', 2), ('a', 1)])),
            ]),
            OrderedDict([
                ('a', 1),
                ('c', OrderedDict([('a', 1), ('b', 2)])),
                ('b', 2),
            ]),
            OrderedDict([
                ('c', OrderedDict([('a', 1), ('b', 2)])),
                ('b', 2),
                ('a', 1),
            ]),
        ]

        data_copies_etag = [generate_etag(d) for d in data_copies]
        assert all(e == etag for e in data_copies_etag)
