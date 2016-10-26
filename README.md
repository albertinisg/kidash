# Kidash

Kidash handle dashboards, visualizations, searches and index-patterns from Kibana.
All the queries are launched against an ElasticSearch and the default index `.kibana`.

## Usage

```
usage: kidash [-g] <action> [<args>] | --help

Import, export and delete dashboards, visualizations, searches and index patterns
from Kibana.

Available actions:

    import           Import elements from a given JSON file (Kibana format)
    export           Export elements from Kibana
    delete           Delete elements based on queries and using Bulk actions

optional arguments:
  -h, --help            show this help message and exit
  -g, --debug           set debug mode on

Run 'kidash <action> --help' to get information about a specific action type.
```

## Requirements

* elasticsearch>=2.4.0

## Installation

Kidash installation is available from the source code.

To install it, you will need to clone the repository first:

```
$ git clone https://github.com/albertinisg/kidash.git
```

Then navigate into the repository and run the following commands:

```
$ pip3 install -r requirements.txt
$ python3 setup.py install
```

## Examples

### import

```
kidash import 'https://user:password@grimoire.biterg.io/data' git-organizations-projects.json
```

### export

```
kidash export 'https://user:password@grimoire.biterg.io/data' dashboards-kib/twitter.json -t dashboard -f all
```

### delete

```
kidash delete 'https://user:password@grimoire.biterg.io/data' -t index-pattern -f all
```

## License

Licensed under GNU General Public License (GPL), version 3 or later.
