from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Scout, ScoutProfile, LandManager

@receiver(post_save, sender=Scout)
def create_user_scout(sender, instance, created, **kwargs):
    if created:
        ScoutProfile.objects.create(user=instance)
    groups = ["Resource Editor", "Crowdsource Editor"]
    for gn in groups:
        g = Group.objects.get(name=gn)
        g.user_set.add(instance)

    instance.scoutprofile.save()

@receiver(post_save, sender=Scout)
def save_user_scout(sender, instance, **kwargs):
    instance.scoutprofile.save()

@receiver(post_save, sender=LandManager)
def create_user_land_manager(sender, instance, created, **kwargs):
    if created:
        groups = ["Resource Editor", "Crowdsource Editor"]
        for gn in groups:
            g = Group.objects.get(name=gn)
            g.user_set.add(instance.user)