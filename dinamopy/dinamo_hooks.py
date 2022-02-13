class DinamoHooks:
    def __init__(self):
        pass

    def before_put(self, **kwargs):
        return kwargs

    def after_put(self, response):
        return response

    def before_overwrite(self, **kwargs):
        return kwargs

    def after_overwrite(self, response):
        return response

    def before_get(self, **kwargs):
        return kwargs

    def after_get(self, response):
        return response

    def before_update(self, **kwargs):
        return kwargs

    def after_update(self, response):
        return response

    def before_delete(self, **kwargs):
        return kwargs

    def after_delete(self, response):
        return response