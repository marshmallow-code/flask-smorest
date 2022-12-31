import abc


class Plugin(abc.ABC):
    """Abstract base class to structure smore plugins"""

    @abc.abstractmethod
    def register_method_docs(self, doc, doc_info, *, api, spec, **kwargs):
        """
        Call when the views are registered in doc

        :param  dict doc: The current operation doc
        :param dict doc_info: Doc info stored by decorators
        :param Api api: The Api() instance
        :param APISpec spec: The APISpec() instance
        """

    @abc.abstractmethod
    def visit_api(self, api, **kwargs):
        """
        Visit the api

        This should be used to register toplevel objects on the spec

        :param api: The APISpec() instance
        """
        pass
