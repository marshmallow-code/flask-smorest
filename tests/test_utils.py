from flask_smorest.utils import deepupdate, load_info_from_docstring


class TestUtils:

    def test_deepupdate(self):
        """Test deepupdate function

        Taken from http://stackoverflow.com/questions/38987#8310229
        """
        pluto_original = {
            'name': 'Pluto',
            'details': {
                'tail': True,
                'color': 'orange'
            },
            'age': 1,
        }

        pluto_update = {
            'name': 'Pluutoo',
            'details': {
                'color': 'blue'
            },
            'age': {'category': 'puppy'},
        }

        assert deepupdate(pluto_original, pluto_update) == {
            'name': 'Pluutoo',
            'details': {
                'color': 'blue',
                'tail': True
            },
            'age': {'category': 'puppy'},
        }

    def test_load_info_from_docstring(self):
        assert (load_info_from_docstring(None)) == {}
        assert (load_info_from_docstring(None, delimiter="---")) == {}
        assert (load_info_from_docstring('')) == {}

        docstring = """
        """
        assert (load_info_from_docstring(docstring)) == {}

        docstring = """Summary"""
        assert (load_info_from_docstring(docstring)) == {
            'summary': 'Summary',
        }

        docstring = """Summary
        Two-line summary is possible.

        Long description
        Really long description
        ---
        Ignore this.
        """
        assert (
            load_info_from_docstring(docstring) ==
            load_info_from_docstring(docstring, delimiter="---") ==
            {
                'summary': 'Summary\nTwo-line summary is possible.',
                'description': 'Long description\nReally long description',
            }
        )
        assert (
            load_info_from_docstring(docstring, delimiter=None) ==
            load_info_from_docstring(docstring, delimiter="~~~") ==
            {
                'summary': 'Summary\nTwo-line summary is possible.',
                'description': (
                    'Long description\nReally long description\n---\n'
                    'Ignore this.'
                )
            }
        )
