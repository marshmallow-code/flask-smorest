"""Database and Application mocks"""


class ItemNotFound(Exception):
    """Item not found"""


class DatabaseMock:
    """Database mock

    Stores data in a list and provides data management methods
    """

    def __init__(self):
        self.items = []
        self.max_id = 0

    def _get_next_id(self):
        self.max_id += 1
        return self.max_id

    def _get_item_index(self, item):
        try:
            return self.items.index(item)
        except ValueError as exc:
            raise ItemNotFound from exc

    def get_by_id(self, item_id):
        try:
            return next(
                i for i in self.items if i['item_id'] == item_id)
        except StopIteration as exc:
            raise ItemNotFound from exc

    def post(self, new_item):
        new_item['item_id'] = self._get_next_id()
        self.items.append(new_item)
        return new_item

    def put(self, item_id, new_item):
        item = self.get_by_id(item_id)
        new_item['item_id'] = item_id
        self.items[self.items.index(item)] = new_item
        return new_item

    def delete(self, item_id):
        item = self.get_by_id(item_id)
        index = self._get_item_index(item)
        del self.items[index]
