import abc
import logging
from typing import TYPE_CHECKING, Any, Iterable, Mapping, MutableMapping, Union

from django.urls import reverse

from sentry import features
from sentry.notifications.notifications.base import BaseNotification
from sentry.notifications.notify import notification_providers
from sentry.notifications.types import NotificationSettingTypes
from sentry.types.integrations import ExternalProviders
from sentry.utils.http import absolute_uri

if TYPE_CHECKING:
    from sentry.models import NotificationSetting, Organization, Team, User

logger = logging.getLogger(__name__)


class OrganizationRequestNotification(BaseNotification, abc.ABC):
    def __init__(self, organization: "Organization", requester: "User") -> None:
        super().__init__(organization)
        self.requester = requester

    def get_context(self) -> MutableMapping[str, Any]:
        raise NotImplementedError

    def get_base_context(self) -> MutableMapping[str, Any]:
        return {
            "organization_name": self.organization.name,
            "organization_slug": self.organization.slug,
            "requester_name": self.requester.get_display_name(),
            "requester_link": absolute_uri(
                f"/settings/{self.organization.slug}/members/{self.requester.id}/"
            ),
            "settings_link": absolute_uri(
                reverse("sentry-organization-settings", args=[self.organization.slug])
            ),
        }

    def get_reference(self) -> Any:
        raise self.organization

    def record_notification_sent(
        self, recipient: Union["Team", "User"], provider: ExternalProviders, **kwargs: Any
    ) -> None:
        super().record_notification_sent(recipient, provider, requester=self.requester.id, **kwargs)

    def determine_recipients(self) -> Iterable[Union["Team", "User"]]:
        """
        Depending on the type of request this might be all organization owners,
        a specific person, or something in between.
        """
        raise NotImplementedError

    def get_participants(self) -> Mapping[ExternalProviders, Iterable[Union["Team", "User"]]]:
        available_providers: Iterable[ExternalProviders] = {ExternalProviders.EMAIL}
        if not features.has("organizations:slack-requests", self.organization):
            available_providers = notification_providers()

        notification_settings_by_provider = NotificationSetting.objects.filter_to_accepting_recipients(
            NotificationSettingTypes.WORKFLOW,  # TODO(steve): Add a new NotificationSettingTypes.
            self.organization,
            self.determine_recipients(),
        )

        return {
            provider: _
            for provider, _ in notification_settings_by_provider
            if provider in available_providers
        }

    def send(self) -> None:
        from sentry.notifications.notify import notify

        participants_by_provider = self.get_participants()
        if not participants_by_provider:
            return

        for provider, recipients in participants_by_provider.items():
            notify(provider, self, recipients, self.get_context())
