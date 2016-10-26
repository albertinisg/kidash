#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 Bitergia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors:
#     Alberto Martín <alberto.martin@bitergia.com>
#

from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan, bulk
import json
import logging
import argparse

CHUNK_SIZE = 1000
FILTER = {"query": {"filtered": {"query": {"match_all": {}},"filter": {"not": {"prefix": {"_id": "_"}}}}}}
CLIENT_FILTER = {"query": {"filtered": {"query": {"prefix": {"_id": "_"}}}}}
ALL = {"query": {"match_all": {}}}

logger = logging.getLogger(__name__)


class Kidash:

    def __init__(self, url, index='.kibana', doc_type=None):
        self.es = Elasticsearch(url, verify_certs=True)
        self.index = index
        self.doc_type = doc_type

    def search_request(self, body, size, filter_path):
        """Make a search in ES based on the given parameters.

        :param body: Body of the query to send
        :param filter_path: Filter for the parameters to retrieve
        :param size: length of the elements to retrieve
        :returns: an Object with the elements retrieved
        """
        request = self.es.search(index=self.index,
                                 doc_type=self.doc_type,
                                 body=body,
                                 filter_path=filter_path,
                                 size=size)
        return request

    def get_number_of_items(self, body):
        """Retrieve the number of items for a given search.

        :param body: Body of the query to send
        :returns: A counter of the total number of ids
        """
        filter_path = ['hits.total']
        request = self.search_request(body, 1, filter_path)
        t_ids = request['hits']['total']
        return t_ids

    def list_item_ids(self, body):
        """Retrieve the list of items for a given search.

        :param body: Body of the query to send
        :returns: an id's list
        """
        filter_path = ['hits.hits._id']
        size = self.get_number_of_items(body)
        request = self.search_request(body, size, filter_path)
        ids_list = request['hits']['hits']
        return ids_list

    def retrieve_items_by_list(self, ids_list):
        """Retrieve items based in a given id's list.

        :param body: Body of the query to send
        :returns: The list of elements retrieved
        """
        body_docs = {'docs': ids_list}
        request = self.es.mget(index=self.index,
                               doc_type=self.doc_type,
                               body=json.dumps(body_docs))
        elements_list = request['docs']
        return elements_list

    def retrieve_items_by_query(self, body=ALL):
        """Retrieve items based in a given query.

        By default it launches the query 'match_all'

        :param body: Body of the query to send
        :returns: The list of elements retrieved
        """
        filter_path = ['hits.hits._*']
        size = self.get_number_of_items(body)
        request = self.search_request(body, size, filter_path)
        return request['hits']['hits']

    def stream_items(self, query):
        """Scan the items of a given query, retrieve it and adds the delete operation.

        :param doc_type: Type of document to search
        :param query: Body of the query to send
        :yields: The elements retrieved
        """
        for item in scan(self.es,
                         query=query,
                         index=self.index,
                         doc_type=self.doc_type,
                         scroll='1m',
                         _source=False):

            del item['_score']
            item['_op_type'] = 'delete'
            yield item

    def load_items(self, list_of_elements):
        """Load a list of given items into ElasticSearch.

        :param doc_type: Type of document to search
        :param list_of_elements: List of the elements to load
        """
        bulk_items = []
        for element in list_of_elements:
            item = {
                        "_index": self.index,
                        "_type": element['_type'],
                        "_id": element['_id'],
                        "_source": element['_source'],
                    }
            bulk_items.append(item)
        bulk(self.es, bulk_items)

    def delete_items(self, query):
        """Remove the elements of a given query by using Bulk operations.

        :param doc_type: Type of document to search
        :param query: Body of the query to send
        """
        bulk(self.es, self.stream_items(query), chunk_size=CHUNK_SIZE)

    def import_items(self, filepath):
        """Import a set of elements given a file.

        :param filepath: Path of the file to load
        """
        list_of_elements = json.loads(open(filepath).read())
        self.load_items(list_of_elements)

    def export_items(self, output_file, query):
        """Export a set of elements based on the parameters given.

        :param output_file: File where to export the items
        """
        items = self.retrieve_items_by_query(query)
        try:
            output_file.write(json.dumps(items, indent=2, sort_keys=True))
            output_file.write('\n')
        except IOError as e:
            raise RuntimeError(str(e))


class KidashCommand:
    """Abstract class to run actions from the command line.

    When the class is initialized, it parses the given arguments using
    the defined argument parser on the class method. Those arguments
    will be stored in the attribute 'parsed_args'.

    The method 'run' must be implemented to exectute the action.
    """
    def __init__(self, *args):
        parser = self.create_argument_parser()
        self.parsed_args = parser.parse_args(args)

    def run(self):
        raise NotImplementedError

    @classmethod
    def create_argument_parser(cls):
        """Returns a generic argument parser."""

        parser = argparse.ArgumentParser()

        # Required arguments

        parser.add_argument('url',
                            help="URL of the ES endpoint.")

        return parser


class ImportCommand(KidashCommand):
    """Class to run Import action from the command line."""

    def __init__(self, *args):
        super().__init__(*args)

        self.url = self.parsed_args.url
        self.filepath = self.parsed_args.filepath
        self.action = Kidash(self.url)

    def run(self):
        """Import JSON file into Kibana.

        This method runs the action to load the elements available in the JSON
        file into the Kibana dashboard.
        """
        self.action.import_items(self.filepath)

    @classmethod
    def create_argument_parser(cls):
        """Returns the Import argument parser."""

        parser = super().create_argument_parser()

        parser.add_argument('filepath',
                            help="JSON file in Kibana format to be loaded.")

        return parser


class ExportCommand(KidashCommand):
    """Class to run Export action from the command line."""

    def __init__(self, *args):
        super().__init__(*args)

        self.url = self.parsed_args.url
        self.outputfile = self.parsed_args.outputfile
        if self.parsed_args.doc_type:
            self.doc_type = self.parsed_args.doc_type
            self.action = Kidash(self.url, doc_type=self.doc_type)
        else:
            self.action = Kidash(self.url)

    def run(self):
        """Import JSON file into Kibana.

        This method runs the action to load the elements available in the JSON
        file into the Kibana dashboard.
        """
        if self.parsed_args.filter is 'filter':
            self.action.export_items(self.outputfile, FILTER)
        elif self.parsed_args.filter is 'client':
            self.action.export_items(self.outputfile, CLIENT_FILTER)
        else:
            self.action.export_items(self.outputfile, ALL)

    @classmethod
    def create_argument_parser(cls):
        """Returns the Import argument parser."""

        parser = super().create_argument_parser()

        parser.add_argument('outputfile', nargs='?', type=argparse.FileType('w'),
                            help="JSON file where to export Kibana elements.")

        group = parser.add_argument_group('general arguments')

        group.add_argument('-t', '--doc-type', dest='doc_type',
                           help="Document type. Available ones from Kibana are: "
                           "'dashboard', 'visualization', 'search' and 'index-pattern'")
        group.add_argument('-f', '--filter', dest='filter',
                           help="Select a filter to export. Available ones are: "
                           "'client', 'filtered' and 'all'")
        return parser
