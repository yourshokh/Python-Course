"""
Module for preparing inverted indexes based on uploaded documents
"""

import sys
import json
import re
from argparse import ArgumentParser, ArgumentTypeError, FileType
from io import TextIOWrapper
from typing import Dict, List, Set
from collections import defaultdict

DEFAULT_PATH_TO_STORE_INVERTED_INDEX = "inverted.index"

STOP_WORDS = {
    'a', 'and', 'around', 'every', 'for', 'from', 'in', 'is', 'it', 
    'not', 'on', 'one', 'the', 'to', 'under'
}

class EncodedFileType(FileType):
    """File encoder"""

    def __call__(self, string):
        if string == "-":
            if "r" in self._mode:
                stdin = TextIOWrapper(sys.stdin.buffer, encoding=self._encoding)
                return stdin
            if "w" in self._mode:
                stdout = TextIOWrapper(sys.stdout.buffer, encoding=self._encoding)
                return stdout
            msg = 'argument "-" with mode %r' % self._mode
            raise ValueError(msg)

        try:
            return open(string, self._mode, self._bufsize, self._encoding, self._errors)
        except OSError as exception:
            args = {"filename": string, "error": exception}
            message = "can't open '%(filename)s': %(error)s"
            raise ArgumentTypeError(message % args)

    def print_encoder(self):
        """printer of encoder"""
        print(self._encoding)


class InvertedIndex:
    """
    This module is necessary to extract inverted indexes from documents.
    """

    def __init__(self, words_ids: Dict[str, List[int]]):
        self.index = words_ids

    def query(self, words: List[str]) -> List[int]:
        """Return the list of relevant documents for the given query"""
        if not words:
            return []
        

        first_word = words[0]
        if first_word not in self.index:
            return []
            
        result_docs = set(self.index[first_word])
        
        for word in words[1:]:
            if word in self.index:
                result_docs.intersection_update(self.index[word])
            else:
                return []
                
        return list(result_docs)

    def dump(self, filepath: str) -> None:
        """
        Allow us to write inverted indexes documents to temporary directory or local storage
        :param filepath: path to file with documents
        :return: None
        """
        with open(filepath, 'w', encoding='utf-8') as file:
            json.dump(self.index, file)

    @classmethod
    def load(cls, filepath: str):
        """
        Allow us to upload inverted indexes from either temporary directory or local storage
        :param filepath: path to file with documents
        :return: InvertedIndex
        """
        with open(filepath, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return cls(data)


def load_documents(filepath: str) -> Dict[int, str]:
    """
    Allow us to upload documents from either tempopary directory or local storage
    :param filepath: path to file with documents
    :return: Dict[int, str]
    """
    docs = {}
    with open(filepath, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            
            try:
                doc_id_str, content = line.lower().split("\t", 1)
                docs[int(doc_id_str)] = content
            except ValueError:
                continue 
    return docs


def build_inverted_index(documents: Dict[int, str]) -> InvertedIndex:
    """
    Builder of inverted indexes based on documents
    :param documents: dict with documents
    :return: InvertedIndex class
    """
    temp_index: Dict[str, Set[int]] = defaultdict(set)
    
    for doc_id, content in documents.items():
        words = re.split(r"\W+", content)
        
        for word in words:
            word = word.strip()
            if word and word not in STOP_WORDS:
                temp_index[word].add(doc_id)
    
    final_index = {word: list(doc_ids) for word, doc_ids in temp_index.items()}
    return InvertedIndex(final_index)


def callback_build(arguments) -> None:
    """process build runner"""
    return process_build(arguments.dataset, arguments.output)


def process_build(dataset, output) -> None:
    """
    Function is responsible for running of a pipeline to load documents,
    build and save inverted index.
    :param arguments: key/value pairs of arguments from 'build' subparser
    :return: None
    """
    documents: Dict[int, str] = load_documents(dataset)
    inverted_index = build_inverted_index(documents)
    inverted_index.dump(output)


def callback_query(arguments) -> None:
    """ "callback query runner"""
    process_query(arguments.query, arguments.index)


def process_query(queries, index) -> None:
    """
    Function is responsible for loading inverted indexes
    and printing document indexes for key words from arguments.query
    :param arguments: key/value pairs of arguments from 'query' subparser
    :return: None
    """
    inverted_index = InvertedIndex.load(index)
    
    for query in queries:
        if isinstance(query, str):
            query = query.strip().lower().split()
        
        if not query:
            continue
            
        doc_indexes = inverted_index.query(query)
        print(",".join(str(value) for value in doc_indexes))


def setup_subparsers(parser) -> None:
    """
    Initial subparsers with arguments.
    :param parser: Instance of ArgumentParser
    """
    subparser = parser.add_subparsers(dest="command")
    build_parser = subparser.add_parser(
        "build",
        help="this parser is need to load, build"
        " and save inverted index bases on documents",
    )
    build_parser.add_argument(
        "-d",
        "--dataset",
        required=True,
        help="You should specify path to file with documents. ",
    )
    build_parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_PATH_TO_STORE_INVERTED_INDEX,
        help="You should specify path to save inverted index. "
        "The default: %(default)s",
    )
    build_parser.set_defaults(callback=callback_build)

    query_parser = subparser.add_parser(
        "query", help="This parser is need to load and apply inverted index"
    )
    query_parser.add_argument(
        "--index",
        default=DEFAULT_PATH_TO_STORE_INVERTED_INDEX,
        help="specify the path where inverted indexes are. " "The default: %(default)s",
    )
    query_file_group = query_parser.add_mutually_exclusive_group(required=True)
    query_file_group.add_argument(
        "-q",
        "--query",
        dest="query",
        action="append",
        nargs="+",
        help="you can specify a sequence of queries to process them overall",
    )
    query_file_group.add_argument(
        "--query_from_file",
        dest="query",
        type=EncodedFileType("r", encoding="utf-8"),
        help="query file to get queries for inverted index",
    )
    query_parser.set_defaults(callback=callback_query)


def main():
    """
    Starter of the pipeline
    """
    parser = ArgumentParser(
        description="Inverted Index CLI is need to load, build,"
        "process query inverted index"
    )
    setup_subparsers(parser)
    arguments = parser.parse_args()
    arguments.callback(arguments)


if __name__ == "__main__":
    main()
