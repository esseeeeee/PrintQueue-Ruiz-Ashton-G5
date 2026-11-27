from django.test.runner import DiscoverRunner


class NoPromptTestRunner(DiscoverRunner):
    """Reuse the test database so lingering PostgreSQL sessions cannot block teardown."""

    def __init__(self, *args, **kwargs):
        kwargs["interactive"] = False
        kwargs["keepdb"] = True
        super().__init__(*args, **kwargs)
