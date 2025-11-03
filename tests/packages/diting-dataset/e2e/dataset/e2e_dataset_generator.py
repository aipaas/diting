#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from diting_core.models.embeddings.factory import embedding_factory
from diting_core.models.llms.factory import llm_factory
from diting_dataset.dataset.dataset_generator import DataSetGenerator


class TestDataSetGenerator(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        llm = llm_factory(
            model="gpt-4o-mini",
        )
        embedding_model = embedding_factory(
            model="bge-m3",
        )
        ds_generator = DataSetGenerator(llm=llm, embedding_model=embedding_model)

        cls.ds_generator = ds_generator

    async def test_generate_dataset_from_langchain_docs_success(self):
        from langchain_community.document_loaders import DirectoryLoader

        path = "markdown/智能评估模块概要设计.md"
        loader = DirectoryLoader(path, glob="**/*.md")
        docs = await loader.aload()
        ds = await self.ds_generator.generate_dataset_from_langchain_docs(
            docs, 20, [], verbose=True
        )
        self.assertTrue(len(ds.to_list()) > 0)

    async def test_generate_dataset_from_docs_success(self):
        path = "markdown/diting-dataset-README.md"
        ds = await self.ds_generator.generate_dataset_from_docs([path], 20, [])
        for case in ds.to_list():
            print(case)
        self.assertTrue(len(ds.to_list()) > 0)
