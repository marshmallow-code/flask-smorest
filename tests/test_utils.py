from flask_rest_api.utils import deepupdate


class TestUtils():

    def test_deepupdate(self):
        """Test deepupdate function

        Taken from http://stackoverflow.com/questions/38987#8310229
        """
        pluto_original = {
            'name': 'Pluto',
            'details': {
                'tail': True,
                'color': 'orange'
            }
        }

        pluto_update = {
            'name': 'Pluutoo',
            'details': {
                'color': 'blue'
            }
        }

        assert deepupdate(pluto_original, pluto_update) == {
            'name': 'Pluutoo',
            'details': {
                'color': 'blue',
                'tail': True
            }
        }
