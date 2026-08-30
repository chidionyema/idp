# Idempotent: one founder user, one project named "estate", its ping key = the vault entry.
# Rendered by the configMapGenerator in kustomization.yaml (crew#684 CP6, 2026-08-30): a plain
# ConfigMap changed in place and the init container never re-ran, so a key the script now sets
# (api_key_readonly) stayed unset and the portal's tile read 401. The generated name carries a
# content hash, so a change here rolls the pod and re-runs this on start.
import os
from django.contrib.auth.models import User
from hc.accounts.models import Profile, Project

email = os.environ["FOUNDER_EMAIL"]
user = User.objects.filter(email=email).first()
if user is None:
    user = User.objects.create(username=email[:150], email=email)
    Profile.objects.get_or_create(user=user)
project = Project.objects.filter(owner=user).order_by("id").first()
if project is None:
    project = Project(owner=user)
project.name = "estate"
project.ping_key = os.environ["PING_KEY"]
# crew#684 CP5: the portal's read-only door
project.api_key_readonly = os.environ["RO_KEY"]
project.save()
print("enrolled", project.name, "for", email)
