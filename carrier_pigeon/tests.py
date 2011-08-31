from django.test import TestCase

from django.db import models
from django.db.models.signals import class_prepared
from django.db.models.signals import post_save

from carrier_pigeon import REGISTRY, add_instance, subscribe_to_post_save
from carrier_pigeon.configuration import DefaultConfiguration
from carrier_pigeon.models import BasicDirtyFieldsMixin, ItemToPush
from carrier_pigeon.select import select


class TestConfiguration(DefaultConfiguration):
    push_urls = ('ftp://foo.bar.baz',)

    def filter_by_instance_type(self, instance):
        return True

    def filter_by_updates(self, instance):
        return True

    def filter_by_state(self, instance):
        return True

    def get_directory(self, instance):
        return 'foo/bar/baz'
add_instance(TestConfiguration())


class TestFilterByInstanceTypeFalse(TestConfiguration):
    def filter_by_instance_type(self, instance):
        return False
add_instance(TestFilterByInstanceTypeFalse())


class TestFilterByUpdatesFalse(TestConfiguration):
    def filter_by_updates(self, instance):
        return False
add_instance(TestFilterByUpdatesFalse())


class TestFilterByStateFalse(TestConfiguration):
    def filter_by_state(self, instance):
        return False
add_instance(TestFilterByStateFalse())


class Dummy(models.Model, BasicDirtyFieldsMixin):
    foo = models.IntegerField()
post_save.connect(select, sender=Dummy)


class ManagerTest(TestCase):
    def test_new_filter(self):
        dummy = Dummy(foo=1)
        dummy.save()

        qs = ItemToPush.objects.new()
        count = qs.count()

        self.assertEqual(count, 2)

    def test_new_filter_chainable(self):
        dummy = Dummy(foo=1)
        dummy.save()

        qs = ItemToPush.objects.new().new()
        count = qs.count()

        self.assertEqual(count, 2)

    #FIXME: add tests for other choices


class AddToQueueTest(TestCase):
    def test_add_to_queue(self):
        """This actually also tests that the filtering is corretly done
        through the presence of enough carrier pigeon configuration classes
        in the registry. see :class:`TestConfiguration`, :class:`TestFilterByInstanceTypeFalse`,
        :class:`TestFilterByUpdatesFalse`, :class:`TestFilterByStateFalse`"""
        dummy = Dummy(foo=1)
        dummy.save()

        qs = ItemToPush.objects.filter(status=ItemToPush.STATUS.NEW)
        count = qs.count()

        self.assertEqual(count, 2)
        for item in qs:
            self.assertEqual(item.status, ItemToPush.STATUS.NEW)

    def test_add_to_queue_update(self):
        """Test whether filter by updates is correctly handled"""
        dummy = Dummy(foo=1)
        dummy.save()

        qs = ItemToPush.objects.filter(status=ItemToPush.STATUS.NEW)
        count = qs.count()

        self.assertEqual(count, 2)
        for item in qs:
            self.assertEqual(item.status, ItemToPush.STATUS.NEW)

        ItemToPush.objects.all().delete()

        dummy = Dummy.objects.get(pk=dummy.pk)
        dummy.foo = 2
        dummy.save()

        qs = ItemToPush.objects.new()
        count = qs.count()

        self.assertEqual(count, 1)
        for item in qs:
            self.assertEqual(item.status, ItemToPush.STATUS.NEW)

