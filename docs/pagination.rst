.. _pagination:
.. currentmodule:: flask_smorest

Pagination
==========

When returning a list of objects, it is generally good practice to paginate the
resource. This is where :meth:`Blueprint.paginate <Blueprint.paginate>` steps
in.

Pagination is more or less transparent to view function depending on the source
of the data that is returned. Two modes are supported: pagination in view
function and post-pagination.


Pagination in View Function
---------------------------

In this mode, :meth:`Blueprint.paginate <Blueprint.paginate>` injects the
pagination parameters into the view function as a
:class:`PaginationParameters <pagination.PaginationParameters>` object passed
as ``pagination_parameters`` keyword argument.

It is the responsability of the view function to return only selected elements.

The view function must also specify the total number of elements by setting it
as ``item_count`` attribute of the `PaginationParameters` object.

.. code-block:: python
    :emphasize-lines: 5,6,7,9,10

    @blp.route('/')
    class Pets(MethodView):

        @blp.response(PetSchema(many=True))
        @blp.paginate()
        def get(self, pagination_parameters):
            pagination_parameters.item_count = Pet.size
            return Pet.get_elements(
                first_item=pagination_parameters.first_item,
                last_item=pagination_parameters.last_item)


Post-Pagination
---------------

This is the mode to use when the data is returned as a lazy database cursor.
The view function does not need to know the pagination parameters. It just
returns the cursor.

This mode is also used if the view function returns the complete list at no
extra cost and there is no interest in specifying the pagination parameters to
avoid fetching unneeded data. For instance, if the whole list is already in
memory.

This mode makes the view look nicer because everything happens in the decorator
and the lazy cursor.

Cursor Pager
^^^^^^^^^^^^

In this case, :meth:`Blueprint.paginate <Blueprint.paginate>` must be passed a
pager class to take care of the pagination. `flask-smorest` provides a pager
for `list`-like objects: :class:`Page <Page>`. For other types, a custom pager
may have to be defined.

For instance, the following custom pager works with cursor classes that support
slicing and provide a ``count`` method returning the total number of element.
This include SQLAlchemy's :class:`Query <sqlalchemy.orm.query.Query>`,
Mongoengine's :class:`QuerySet <mongoengine.queryset.QuerySet>`,...


.. code-block:: python

    from flask_smorest import Page

    class CursorPage(Page):
        @property
        def item_count(self):
            return self.collection.count()

    @blp.route('/')
    class Pets(MethodView):

        @blp.response(PetSchema(many=True))
        @blp.paginate(CursorPage)
        def get(self):
            return Pet.get()

Pagination Parameters
---------------------

Once a view function is decorated with
:meth:`Blueprint.paginate <Blueprint.paginate>`, the client can request a
specific range of data by passing query arguments:


``GET /pets/?page=2&page_size=10``


The view function gets default values for the pagination parameters, as well as
a maximum value for ``page_size``.

Those default values are defined as

.. code-block:: python

    DEFAULT_PAGINATION_PARAMETERS = {
        'page': 1, 'page_size': 10, 'max_page_size': 100}

They can be modified globally by overriding ``DEFAULT_PAGINATION_PARAMETERS``
class attribute of the :class:`Blueprint <Blueprint>` class or overridden in
a specific view function by passing them as keyword arguments to
:meth:`Blueprint.paginate <Blueprint.paginate>`.


Pagination Header
-----------------

When pagination is used, a ``'X-Pagination'`` header is added to the response.
It contains the pagination information.

.. code-block:: python

    print(headers['X-Pagination'])
    # {
    #     'total': 1000, 'total_pages': 200,
    #     'page': 2, 'first_page': 1, 'last_page': 200,
    #     'previous_page': 1, 'next_page': 3,
    # }

The name of the header can be changed by overriding
``PAGINATION_HEADER_FIELD_NAME`` class attribute of the
:class:`Blueprint <Blueprint>` class. When setting this attribute to ``None``,
no pagination header is added to the response.
