from django.contrib import admin
from .models import RoleTemplate, AbilityTemplate, RoleAbility, GameTemplate, GameRoleSlot

admin.site.register(RoleTemplate)
admin.site.register(AbilityTemplate)
admin.site.register(RoleAbility)
admin.site.register(GameTemplate)
admin.site.register(GameRoleSlot)
