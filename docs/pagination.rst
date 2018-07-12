.. _pagination:
.. module:: flask_rest_api

Pagination
==========

When returning a list of objects, it is generally good practice to paginate the
resource. This is when :meth:`Blueprint.paginate <Blueprint.paginate>` steps in.

Pagination is more or less transparent to view function depending on the source
of the data that is returned.


Pagination in the View Function
-------------------------------

In this mode, :meth:`Blueprint.paginate <Blueprint.paginate>` injects the
pagination parameters ``first_item`` and ``last_item`` as kwargs into the view
function.

It is the responsability of the view function to return only selected elements.

The view function must also specify the total number of elements using
:meth:`set_item_count <pagination.set_item_count>`.

.. code-block:: python
    :emphasize-lines: 7,8,9,10

    from flask_rest_api import set_item_count

    @blp.route('/')
    class Pets(MethodView):

        @blp.response(PetSchema(many=True))
        @blp.paginate()
        def get(self, first_item, last_item):
            set_item_count(Pet.size)
            return Pet.get_elements(first_item=first_item, last_item=last_item)


Post-Pagination
---------------

This is the mode to use when the data is returned as a lazy database cursor.
The view function does not need to know the pagination parameters. It just
returns the cursor.

This mode is also used if the view function returns the complete ``list`` at no
extra cost and there is no interest in specifying the pagination parameters to
avoid fetching unneeded data. For instance, if the whole list is already in
memory.

This mode makes the view look nicer because everything happens in the decorator
and the lazy cursor.

In this case, :meth:`Blueprint.paginate <Blueprint.paginate>` must be passed a
cursor pager to take care of the pagination. `flask-rest-api` provides a pager
for `list`-like objects: :class:`Page <pagination.Page>`. When dealing with a
lazy database cursor, a custom cursor pager can be defined using a cursor
wrapper.


.. code-block:: python
    :emphasize-lines: 18

    from flask_rest_api import Page

    class CursorWrapper():
        def __init__(self, obj):
            self.obj = obj
        def __getitem__(self, key):
            return self.obj[key]
        def __len__(self):
            return self.obj.count()

    class CursorPage(Page):
        _wrapper_class = CursorWrapper

    @blp.route('/')
    class Pets(MethodView):

        @blp.response(PetSchema(many=True))
        @blp.paginate(CursorPage)
        def get(self):
            return Pet.get()

The custom wrapper defined in the example above works for SQLAlchemy or PyMongo
cursors.


Pagination Parameters
---------------------

Once a view function is decorated with
:meth:`Blueprint.paginate <Blueprint.paginate>`, the client can request a
specific range of data by passing query arguments:


``GET /pets/?page=2&page_size=10``


The view function gets default values for the pagination parameters, as well as
a maximum value for ``page_size``.

Those default values are defined globally as

.. code-block:: python

    DEFAULT_PAGINATION_PARAMETERS = {
        'page': 1, 'page_size': 10, 'max_page_size': 100}

They can be modified globally by mutating
``flask_rest_api.pagination.DEFAULT_PAGINATION_PARAMETERS``, or overwritten in
a specific view function by passing them as keyword arguments to
:meth:`Blueprint.paginate <Blueprint.paginate>`.


Pagination Header
-----------------

When pagination is used, a ``'X-Pagination'`` header is added to the response.
It contains the pagination information.

.. code-block:: python

    print(headers['X-Pagination'])
    # {
    #     'total': 1000, 'total_pages': 200,
    #     'first_page': 1, 'last_page': 200,
    #     'previous_page': 1, 'next_page': 3,
    # }
