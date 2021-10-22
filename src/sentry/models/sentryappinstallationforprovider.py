from django.db import models

from sentry.db.models import BaseManager, FlexibleForeignKey
from sentry.models import DefaultFieldsModel
from sentry.models.sentryappinstallationtoken import SentryAppInstallationToken


class SentryAppInstallationForProviderManager(BaseManager):
    def get_token(self, organization_id: int, provider: str) -> str:
        installation_for_provider = self.select_related(
            "sentry_app_installation"
        ).get(organization_id=organization_id, provider=provider)
        sentry_app_installation = installation_for_provider.sentry_app_installation

        # find a token associated with the installation so we can use it for authentication
        sentry_app_installation_token = (
            SentryAppInstallationToken.objects.select_related("api_token")
                .filter(sentry_app_installation=sentry_app_installation)
                .first()
        )
        return sentry_app_installation_token.api_token.token


class SentryAppInstallationForProvider(DefaultFieldsModel):
    """Connects a sentry app installation to an organization and a provider."""
    __include_in_export__ = False

    sentry_app_installation = FlexibleForeignKey("sentry.SentryAppInstallation")
    organization = FlexibleForeignKey("sentry.Organization")
    provider = models.CharField(max_length=64)

    objects = SentryAppInstallationForProviderManager()

    class Meta:
        app_label = "sentry"
        db_table = "sentry_sentryappinstallationforprovider"
        unique_together = (("provider", "organization"),)
