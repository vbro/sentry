from collections import defaultdict

from django.db.models import prefetch_related_objects

from sentry.api.serializers import Serializer, register, serialize
from sentry.incidents.models import (
    AlertRuleTrigger,
    AlertRuleTriggerAction,
    AlertRuleTriggerExclusion,
)


@register(AlertRuleTrigger)
class AlertRuleTriggerSerializer(Serializer):
    def get_attrs(self, item_list, user, **kwargs):
        prefetch_related_objects(item_list, "alert_rule")

        triggers = {item.id: item for item in item_list}
        result = defaultdict(dict)

        actions = AlertRuleTriggerAction.objects.filter(alert_rule_trigger__in=item_list).order_by(
            "id"
        )
        serialized_actions = serialize(list(actions))
        for trigger, serialized in list(zip(actions, serialized_actions)):
            triggers_actions = result[triggers[trigger.alert_rule_trigger_id]].setdefault(
                "actions", []
            )
            triggers_actions.append(serialized)

        return result

    def serialize(self, obj, attrs, user):
        return {
            "id": str(obj.id),
            "alertRuleId": str(obj.alert_rule_id),
            "label": obj.label,
            "thresholdType": obj.alert_rule.threshold_type,
            "alertThreshold": obj.alert_threshold,
            "resolveThreshold": obj.alert_rule.resolve_threshold,
            "dateCreated": obj.date_added,
            "actions": attrs.get("actions", []),
        }


class DetailedAlertRuleTriggerSerializer(AlertRuleTriggerSerializer):
    def get_attrs(self, item_list, user, **kwargs):
        triggers = {item.id: item for item in item_list}
        result = defaultdict(dict)
        for trigger_id, project_slug in AlertRuleTriggerExclusion.objects.filter(
            alert_rule_trigger__in=item_list
        ).values_list("alert_rule_trigger_id", "query_subscription__project__slug"):
            exclusions = result[triggers[trigger_id]].setdefault("excludedProjects", [])
            exclusions.append(project_slug)
        return result

    def serialize(self, obj, attrs, user):
        data = super().serialize(obj, attrs, user)
        data["excludedProjects"] = sorted(attrs.get("excludedProjects", []))
        return data
