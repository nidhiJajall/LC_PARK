import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
import pyclbr

class Command(BaseCommand):
    help = 'Create model, section, subsection, and view permissions'

    def handle(self, *args, **options):
        PROJECT_NAME = input("Please enter the project name: ")
        REQUEST_METHODS = ['get', 'post', 'put', 'delete', 'patch']
        DISPLAY_MODELS = settings.DISPLAY_MODELS
        PROJECT_APPS = settings.PROJECT_APPS
        EXTRA_USER_META = settings.EXTRA_USER_META

        self.stdout.write("DISPLAY_MODELS found: {}".format(len(DISPLAY_MODELS.keys())))
        self.stdout.write("EXTRA_USER_META found: {}".format(len(EXTRA_USER_META)))

        views = []
        for each in PROJECT_APPS:
            try:
                module = pyclbr.readmodule('{}.views'.format(each))
                for item in module.values():
                    views.append(item.name.lower())
            except Exception as e:
                self.stdout.write(str(e))

        self.stdout.write("TOTAL_VIEWS found: {}".format(len(views)))

        model_permissions_created_count = 0
        section_permissions_created_count = 0
        subsection_permissions_created_count = 0
        view_permissions_created_count = 0

        for model in DISPLAY_MODELS.keys():
            content_type = ContentType.objects.filter(model__iexact=model)
            if not content_type.exists():
                self.stdout.write("ContentType not found for: {}".format(model))
                continue
            else:
                content_type = content_type.first()
            if not Permission.objects.filter(content_type=content_type, codename='view_{}'.format(model)).exists():
                Permission.objects.create(name='Can View {}'.format(model),
                                          content_type=content_type,
                                          codename='view_{}'.format(model))
                model_permissions_created_count += 1
            if not Permission.objects.filter(content_type=content_type, codename='add_{}'.format(model)).exists():
                Permission.objects.create(name='Can Add {}'.format(model),
                                          content_type=content_type,
                                          codename='add_{}'.format(model))
                model_permissions_created_count += 1
            if not Permission.objects.filter(content_type=content_type, codename='change_{}'.format(model)).exists():
                Permission.objects.create(name='Can Change {}'.format(model),
                                          content_type=content_type,
                                          codename='change_{}'.format(model))
                model_permissions_created_count += 1
            if not Permission.objects.filter(content_type=content_type, codename='delete_{}'.format(model)).exists():
                Permission.objects.create(name='Can Delete {}'.format(model),
                                          content_type=content_type,
                                          codename='delete_{}'.format(model))
                model_permissions_created_count += 1

        content_type, created = ContentType.objects.get_or_create(app_label=PROJECT_NAME, model="none")

        for section in EXTRA_USER_META.keys():
            if not Permission.objects.filter(codename='view_{}'.format(section.lower())).exists():
                Permission.objects.create(name='Can View {} Section'.format(section),
                                          content_type=content_type,
                                          codename='view_{}'.format(section.lower()))
                section_permissions_created_count += 1

        for section, subsections in EXTRA_USER_META.items():
            for subsection in subsections:
                if 'screen' in subsection.keys():
                    if not Permission.objects.filter(codename='view_{}'.format(subsection['screen'].lower())).exists():
                        Permission.objects.create(name='Can View {} Subsection'.format(subsection['screen']),
                                                  content_type=content_type,
                                                  codename='view_{}'.format(subsection['screen'].lower()))
                        subsection_permissions_created_count += 1

        for view in views:
            for method in REQUEST_METHODS:
                if not Permission.objects.filter(codename='{}_{}_view'.format(method, view)).exists():
                    Permission.objects.create(name='Can {} {} View'.format(method, view),
                                              content_type=content_type,
                                              codename='{}_{}_view'.format(method, view))
                    view_permissions_created_count += 1

        print("--------------------------------------------------------------------")
        print("{} Model permissions created".format(model_permissions_created_count))
        print("{} Section permissions created".format(section_permissions_created_count))
        print("{} Subsection permissions created".format(subsection_permissions_created_count))
        print("{} View permissions created".format(view_permissions_created_count))