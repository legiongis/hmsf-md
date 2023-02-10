from django.db import models
from tinymce.models import HTMLField

class ProfileLink(models.Model):

    name = models.CharField(max_length=100)
    desc = models.CharField(max_length=500, blank=True, null=True)
    url = models.CharField(max_length=500, blank=True, null=True)
    file = models.FileField(upload_to="uploadedfiles", blank=True, null=True)
    sortorder_scout = models.IntegerField(
        default=0,
        help_text="use 0 if you DO NOT want this link to appear on the Scout profile page"
    )
    sortorder_landmanager = models.IntegerField(
        default=0,
        help_text="use 0 if you DO NOT want this link to appear on the Land Manager profile page"
    )
    sortorder_admin = models.IntegerField(
        default=0,
        help_text="use 0 if you DO NOT want this link to appear on the Admin profile page"
    )

    def __str__(self):
        return self.name

    def serialize(self):

        target = self.url
        if not self.url and self.file:
            target = self.file.url
        return {
            "name": self.name,
            "desc": self.desc,
            "target": target,
        }


class ProfileContent(models.Model):

    name = models.CharField(max_length=100)
    content = HTMLField()
    sortorder_scout = models.IntegerField(
        default=0,
        help_text="use 1 for this content to appear on the Scout profile page"
    )
    sortorder_landmanager = models.IntegerField(
        default=0,
        help_text="use 1 for this content to appear on the Land Manager profile page"
    )
    sortorder_admin = models.IntegerField(
        default=0,
        help_text="use 1 for this content to appear on the Admin profile page"
    )

    def __str__(self):
        return self.name