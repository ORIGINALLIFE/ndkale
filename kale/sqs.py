"""Base class for SQS utility classes."""
from __future__ import absolute_import

import logging

import boto3
import botocore
from kale import exceptions
from kale import settings

logger = logging.getLogger(__name__)


class SQSTalk(object):
    """Base class for SQS utility classes."""

    _client = None
    _session = None
    _sqs = None

    # queue name to SQS.Queue object mapping
    _queues = {}

    def __init__(self, *args, **kwargs):
        """Constructor.
        :raises: exceptions.ImproperlyConfiguredException: Raised if the
            settings are not adequately configured.
        """

        if not settings.PROPERLY_CONFIGURED:
            raise exceptions.ImproperlyConfiguredException(
                'Settings are not properly configured.')

        self.aws_region = settings.AWS_REGION if settings.AWS_REGION != '' else None
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID if settings.AWS_ACCESS_KEY_ID != '' else None
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY if settings.AWS_SECRET_ACCESS_KEY != '' else None

        self._session = boto3.Session(region_name=self.aws_region,
                                      aws_access_key_id=aws_access_key_id,
                                      aws_secret_access_key=aws_secret_access_key)
        self._client = self._session.client('sqs')
        self._sqs = self._session.resource('sqs')

    def _get_or_create_queue(self, queue_name):
        """Fetch or create a queue.

        :param str queue_name: string for queue name.
        :return: Queue
        :rtype: boto3.resources.factory.sqs.Queue
        """

        # Check local cache first.
        if queue_name in self._queues:
            return self._queues[queue_name]

        # get or create queue
        try:
            resp = self._client.get_queue_url(QueueName=queue_name)
            queue_url = resp.get('QueueUrl')
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] != 'AWS.SimpleQueueService.NonExistentQueue':
                raise e

            logger.info('Creating new SQS queue: %s' % queue_name)
            queue = self._client.create_queue(QueueName=queue_name)
            queue_url = queue.get('QueueUrl')

        # create queue object
        queue = self._sqs.Queue(queue_url)

        self._queues[queue_name] = queue
        return queue

    def get_all_queues(self, prefix=''):
        """Returns all queues, filtered by prefix.

        :param str prefix: string for queue prefix.
        :return: a list of queue objects.
        :rtype: list[boto3.resources.factory.sqs.Queue]
        """

        # QueueNamePrefix is optional and can not be None.
        resp = self._client.list_queues(QueueNamePrefix=prefix)

        queue_urls = resp.get('QueueUrls', [])

        queues = []
        for queue_url in queue_urls:
            queues.append(self._sqs.Queue(queue_url))

        return queues
