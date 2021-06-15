import pickle

from django import VERSION

django_version = f"{VERSION[0]}.{VERSION[1]}"

from sentry.testutils import TestCase


class Lol(TestCase):
    def setUp(self):
        self.project = self.create_project(name="cool project")

    def test_generate_pickle(self):
        with open(f"project-{django_version}.pickle", "wb") as f:
            f.write(pickle.dumps(self.project))

    def test_20_unpickles_111(self):
        assert django_version == "2.0"
        with open("project-1.11.pickle", "rb") as f:
            project_11 = pickle.loads(f.read())

        assert project_11 == self.project
        assert project_11.name == self.project.name
        assert project_11.slug == self.project.slug
        assert project_11.organization == self.project.organization
        assert project_11.status == self.project.status
        assert project_11.flags == self.project.flags
        assert project_11.platform == self.project.platform

    def test_111_unpickles_20(self):
        assert django_version == "1.11"
        with open("project-2.0.pickle", "rb") as f:
            project_20 = pickle.loads(f.read())

        assert project_20 == self.project
        assert project_20.name == self.project.name
        assert project_20.slug == self.project.slug
        assert project_20.organization == self.project.organization
        assert project_20.status == self.project.status
        assert project_20.flags == self.project.flags
        assert project_20.platform == self.project.platform
