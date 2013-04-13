from django.contrib.auth.models import Permission
from django.core.files.images import ImageFile
from django.db.models.query import QuerySet
from django.test import TestCase

import factory

from guardian.shortcuts import assign_perm
from taggit.models import Tag

from ..models import Board, Pin, Image
from ...users.models import User


TEST_IMAGE_PATH = 'logo.png'


class BoardFactory(factory.Factory):
    FACTORY_FOR = Board

    name = factory.Sequence(lambda n: 'Test board #{}'.format(n))


class UserFactory(factory.Factory):
    username = factory.Sequence(lambda n: 'user_{}'.format(n))
    email = factory.Sequence(lambda n: 'user_{}@example.com'.format(n))

    @factory.post_generation(extract_prefix='password')
    def set_password(self, create, extracted, **kwargs):
        self.set_password(extracted)
        self.save()

    @factory.post_generation(extract_prefix='user_permissions')
    def set_user_permissions(self, create, extracted, **kwargs):
        self.user_permissions = Permission.objects.filter(codename__in=['add_pin', 'add_image'])


class TagFactory(factory.Factory):
    name = factory.Sequence(lambda n: 'tag_{}'.format(n))


class ImageFactory(factory.Factory):
    image = factory.LazyAttribute(lambda a: ImageFile(open(TEST_IMAGE_PATH, 'rb')))


class PinFactory(factory.Factory):
    FACTORY_FOR = Pin

    submitter = factory.SubFactory(UserFactory)
    image = factory.SubFactory(ImageFactory)
    url = factory.Sequence(lambda n: 'http://testserver/mocked/{}.jpg'.format(n))
    board = factory.SubFactory(BoardFactory)

    @factory.post_generation
    def set_permissions(self, create, extracted, **kwargs):
        for perm in ['change_pin', 'delete_pin']:
            assign_perm(perm, self.submitter, self)

    @factory.post_generation(extract_prefix='tags')
    def add_tags(self, create, extracted, **kwargs):
        if isinstance(extracted, Tag):
            self.tags.add(extracted)
        elif isinstance(extracted, list):
            self.tags.add(*extracted)
        elif isinstance(extracted, QuerySet):
            self.tags = extracted
        else:
            self.tags.add(TagFactory())


class PinFactoryTest(TestCase):
    def test_default_tags(self):
        self.assertTrue(PinFactory().tags.get(pk=1).name.startswith('tag_'))

    def test_custom_tag(self):
        custom = 'custom_tag'
        self.assertEqual(PinFactory(tags=Tag.objects.create(name=custom)).tags.get(pk=1).name, custom)

    def test_custom_tags_list(self):
        tags = TagFactory.create_batch(2)
        PinFactory(tags=tags)
        self.assertEqual(Tag.objects.count(), 2)

    def test_custom_tags_queryset(self):
        TagFactory.create_batch(2)
        tags = Tag.objects.all()
        PinFactory(tags=tags)
        self.assertEqual(Tag.objects.count(), 2)

    def test_empty_tags(self):
        PinFactory(tags=[])
        self.assertEqual(Tag.objects.count(), 0)
