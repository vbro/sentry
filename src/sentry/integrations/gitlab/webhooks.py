import logging

from dateutil.parser import parse as parse_date
from django.db import IntegrityError, transaction
from django.http import Http404, HttpResponse
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from rest_framework.request import Request
from rest_framework.response import Response

from sentry.models import Commit, CommitAuthor, Integration, PullRequest, Repository
from sentry.plugins.providers import IntegrationRepositoryProvider
from sentry.utils import json

logger = logging.getLogger("sentry.webhooks")

PROVIDER_NAME = "integrations:gitlab"


class Webhook:
    def __call__(self, integration, organization, event):
        raise NotImplementedError

    def get_repo(self, integration, organization, event):
        """
        Given a webhook payload, get the associated Repository record.

        Assumes a 'project' key in event payload.
        """
        try:
            project_id = event["project"]["id"]
        except KeyError:
            logger.info(
                "gitlab.webhook.missing-projectid", extra={"integration_id": integration.id}
            )
            raise Http404()

        external_id = "{}:{}".format(integration.metadata["instance"], project_id)
        try:
            repo = Repository.objects.get(
                organization_id=organization.id, provider=PROVIDER_NAME, external_id=external_id
            )
        except Repository.DoesNotExist:
            return None
        return repo

    def update_repo_data(self, repo, event):
        """
        Given a webhook payload, update stored repo data if needed.

        Assumes a 'project' key in event payload, with certain subkeys. Rework
        this if that stops being a safe assumption.
        """

        project = event["project"]

        url_from_event = project["web_url"]
        path_from_event = project["path_with_namespace"]

        if repo.url != url_from_event or repo.config.get("path") != path_from_event:
            repo.update(
                url=url_from_event,
                config=dict(repo.config, path=path_from_event),
            )


class MergeEventWebhook(Webhook):
    """
    Handle Merge Request Hook

    See https://docs.gitlab.com/ee/user/project/integrations/webhooks.html#merge-request-events
    """

    def __call__(self, integration, organization, event):
        repo = self.get_repo(integration, organization, event)
        if repo is None:
            return

        # while we're here, make sure repo data is up to date
        self.update_repo_data(repo, event)

        try:
            number = event["object_attributes"]["iid"]
            title = event["object_attributes"]["title"]
            body = event["object_attributes"]["description"]
            created_at = event["object_attributes"]["created_at"]
            merge_commit_sha = event["object_attributes"]["merge_commit_sha"]

            last_commit = event["object_attributes"]["last_commit"]
            author_email = None
            author_name = None
            if last_commit:
                author_email = last_commit["author"]["email"]
                author_name = last_commit["author"]["name"]
        except KeyError as e:
            logger.info(
                "gitlab.webhook.invalid-merge-data",
                extra={"integration_id": integration.id, "error": str(e)},
            )
            # TODO(mgaeta): This try/catch is full of reportUnboundVariable errors.
            return

        if not author_email:
            raise Http404()

        author = CommitAuthor.objects.get_or_create(
            organization_id=organization.id, email=author_email, defaults={"name": author_name}
        )[0]

        try:
            PullRequest.create_or_save(
                organization_id=organization.id,
                repository_id=repo.id,
                key=number,
                values={
                    "title": title,
                    "author": author,
                    "message": body,
                    "merge_commit_sha": merge_commit_sha,
                    "date_added": parse_date(created_at).astimezone(timezone.utc),
                },
            )
        except IntegrityError:
            pass


class PushEventWebhook(Webhook):
    """
    Handle push hook

    See https://docs.gitlab.com/ee/user/project/integrations/webhooks.html#push-events
    """

    def __call__(self, integration, organization, event):
        repo = self.get_repo(integration, organization, event)
        if repo is None:
            return

        # while we're here, make sure repo data is up to date
        self.update_repo_data(repo, event)

        authors = {}

        # TODO gitlab only sends a max of 20 commits. If a push contains
        # more commits they provide a total count and require additional API
        # requests to fetch the commit details
        for commit in event.get("commits", []):
            if IntegrationRepositoryProvider.should_ignore_commit(commit["message"]):
                continue

            author_email = commit["author"]["email"]

            # TODO(dcramer): we need to deal with bad values here, but since
            # its optional, lets just throw it out for now
            if author_email is None or len(author_email) > 75:
                author = None
            elif author_email not in authors:
                authors[author_email] = author = CommitAuthor.objects.get_or_create(
                    organization_id=organization.id,
                    email=author_email,
                    defaults={"name": commit["author"]["name"]},
                )[0]
            else:
                author = authors[author_email]
            try:
                with transaction.atomic():
                    Commit.objects.create(
                        repository_id=repo.id,
                        organization_id=organization.id,
                        key=commit["id"],
                        message=commit["message"],
                        author=author,
                        date_added=parse_date(commit["timestamp"]).astimezone(timezone.utc),
                    )
            except IntegrityError:
                pass


class GitlabWebhookEndpoint(View):
    provider = "gitlab"

    _handlers = {"Push Hook": PushEventWebhook, "Merge Request Hook": MergeEventWebhook}

    @method_decorator(csrf_exempt)
    def dispatch(self, request: Request, *args, **kwargs) -> Response:
        if request.method != "POST":
            return HttpResponse(status=405)

        return super().dispatch(request, *args, **kwargs)

    def post(self, request: Request) -> Response:
        token = "<unknown>"
        try:
            # Munge the token to extract the integration external_id.
            # gitlab hook payloads don't give us enough unique context
            # to find data on our side so we embed one in the token.
            token = request.META["HTTP_X_GITLAB_TOKEN"]
            instance, group_path, secret = token.split(":")
            external_id = f"{instance}:{group_path}"
        except Exception:
            logger.info("gitlab.webhook.invalid-token", extra={"token": token})
            return HttpResponse(status=400)

        try:
            integration = (
                Integration.objects.filter(provider=self.provider, external_id=external_id)
                .prefetch_related("organizations")
                .get()
            )
        except Integration.DoesNotExist:
            logger.info(
                "gitlab.webhook.invalid-organization",
                extra={"external_id": request.META["HTTP_X_GITLAB_TOKEN"]},
            )
            return HttpResponse(status=400)

        if not constant_time_compare(secret, integration.metadata["webhook_secret"]):
            logger.info(
                "gitlab.webhook.invalid-token-secret", extra={"integration_id": integration.id}
            )
            return HttpResponse(status=400)

        try:
            event = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            logger.info(
                "gitlab.webhook.invalid-json", extra={"external_id": integration.external_id}
            )
            return HttpResponse(status=400)

        try:
            handler = self._handlers[request.META["HTTP_X_GITLAB_EVENT"]]
        except KeyError:
            logger.info(
                "gitlab.webhook.missing-event", extra={"event": request.META["HTTP_X_GITLAB_EVENT"]}
            )
            return HttpResponse(status=400)

        for organization in integration.organizations.all():
            handler()(integration, organization, event)
        return HttpResponse(status=204)
