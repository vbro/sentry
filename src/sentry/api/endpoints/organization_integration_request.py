from django.utils.encoding import force_text
from rest_framework.response import Response

from sentry.api.bases.organization_request_change import OrganizationRequestChangeEndpoint
from sentry.notifications.notifications.organization_request.integration_request import (
    IntegrationRequestNotification,
)


class OrganizationIntegrationRequestEndpoint(OrganizationRequestChangeEndpoint):
    def post(self, request, organization):
        """
        Email the organization owners asking them to install an integration.
        ````````````````````````````````````````````````````````````````````
        When a non-owner user views integrations in the integrations directory,
        they lack the ability to install them themselves. POSTing to this API
        alerts users with permission that there is demand for this integration.

        :param string providerSlug: Unique string that identifies the integration.
        :param string providerType: One of: first_party, plugin, sentry_app.
        :param string message: Optional message from the requester to the owners.
        """

        provider_type = request.data.get("providerType")
        provider_slug = request.data.get("providerSlug")
        message_option = request.data.get("message", "").strip()

        requester = request.user
        if requester.id in [user.id for user in organization.get_owners()]:
            return Response({"detail": "User can install integration"}, status=200)

        try:
            IntegrationRequestNotification(
                organization, requester, provider_type, provider_slug, message_option
            ).send()
        except RuntimeError as error:
            return Response({"detail": force_text(error)}, status=400)

        return Response(status=201)
