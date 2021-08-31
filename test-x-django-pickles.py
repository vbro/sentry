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

    def test_22_unpickles_21(self):
        assert django_version == "2.2"
        with open("project-2.1.pickle", "rb") as f:
            project_21 = pickle.loads(f.read())

        assert project_21 == self.project
        assert project_21.name == self.project.name
        assert project_21.slug == self.project.slug
        assert project_21.organization == self.project.organization
        assert project_21.status == self.project.status
        assert project_21.flags == self.project.flags
        assert project_21.platform == self.project.platform

    def test_21_unpickles_22(self):
        assert django_version == "2.1"
        with open("project-2.2.pickle", "rb") as f:
            project_22 = pickle.loads(f.read())

        assert project_22 == self.project
        assert project_22.name == self.project.name
        assert project_22.slug == self.project.slug
        assert project_22.organization == self.project.organization
        assert project_22.status == self.project.status
        assert project_22.flags == self.project.flags
        assert project_22.platform == self.project.platform
