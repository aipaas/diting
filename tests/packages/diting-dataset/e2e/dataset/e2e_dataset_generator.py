#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from diting_core.models.embeddings.factory import embedding_factory
from diting_core.models.llms.factory import llm_factory
from diting_dataset.dataset.dataset_generator import DataSetGenerator


class TestDataSetGenerator(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        model = "gpt-4o-mini"
        api_key = "NTk5MjpxaWFubGl1YXBpa2V5OumZiOW/lzgyMDIwOjEyMjUz"
        base_url = "https://chatgpt.sangfor.com/api/proxy"

        llm = llm_factory(model, base_url, api_key)
        embedding_model = embedding_factory(
            **{
                "model": "bge-m3",
                "base_url": "http://10.57.1.182:30081/v1/",
                "api_key": "sk-jwaRNx5UJxB9WVZf7UgdRKuMOPPRkMn_w1YgUbhb20I",
            }
        )
        ds_generator = DataSetGenerator(llm=llm, embedding_model=embedding_model)

        cls.ds_generator = ds_generator

    async def test_generate_dataset_from_langchain_docs_success(self):
        from langchain_community.document_loaders import DirectoryLoader

        path = "markdown/"
        loader = DirectoryLoader(path, glob="**/*.md")
        docs = await loader.aload()
        ds = await self.ds_generator.generate_dataset_from_langchain_docs(
            docs, [], verbose=True
        )
        self.assertTrue(len(ds.to_list()) > 0)

    async def test_generate_dataset_from_docs_success(self):
        path = "markdown/"
        ds = await self.ds_generator.generate_dataset_from_docs(
            [path], [], verbose=True
        )
        for case in ds.to_list():
            print(case)
        self.assertTrue(len(ds.to_list()) > 0)
