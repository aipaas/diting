#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import asyncio
import pandas as pd
from typing import List, Dict

from diting_core.cases.llm_case import LLMCase
from diting_core.metrics.context_precision.context_precision import ContextPrecision
from diting_core.metrics.context_recall.context_recall import ContextRecall
from diting_core.models.llms.factory import llm_factory


class DebugSemanticSearch:
    """
    A class to debug semantic search by evaluating context precision and recall metrics
    based on user-provided query ID, and data from qa_train.csv and corpus.csv files.
    """

    def __init__(self, corpus_file_path: str, qa_train_file_path: str):
        """
        Initialize the DebugSemanticSearch with paths to corpus and QA files.
        
        Args:
            corpus_file_path (str): Path to the corpus CSV file containing documents
            qa_train_file_path (str): Path to the QA train CSV file
        """
        self.corpus_file_path = corpus_file_path
        self.qa_train_file_path = qa_train_file_path
        self.corpus_data = self._load_corpus()
        self.qa_train_data = self._load_qa_train()

    def _load_corpus(self) -> pd.DataFrame:
        """
        Load corpus data from CSV file.
        
        Returns:
            pd.DataFrame: Loaded corpus data
        """
        return pd.read_csv(self.corpus_file_path)

    def _load_qa_train(self) -> pd.DataFrame:
        """
        Load QA train data from CSV file.
        
        Returns:
            pd.DataFrame: Loaded QA train data
        """
        return pd.read_csv(self.qa_train_file_path)

    def _get_qa_by_qid(self, qid: str) -> Dict[str, str]:
        """
        Retrieve query and generation ground truth from QA train data based on QID.
        
        Args:
            qid (str): Question ID
            
        Returns:
            Dict[str, str]: Dictionary with 'query' and 'generation_gt' keys
        """
        row = self.qa_train_data[self.qa_train_data['qid'] == qid]
        if row.empty:
            raise ValueError(f"No QA data found for qid: {qid}")
        
        query = row['query'].iloc[0]
        generation_gt = row['generation_gt'].iloc[0]
        return {
            'query': query,
            'generation_gt': generation_gt
        }

    def _get_content_by_doc_ids(self, doc_ids: List[str]) -> List[str]:
        """
        Retrieve content from corpus based on document IDs.
        
        Args:
            doc_ids (List[str]): List of document IDs
            
        Returns:
            List[str]: List of content strings corresponding to the document IDs
        """
        contents = []
        for doc_id in doc_ids:
            content = self.corpus_data[self.corpus_data['doc_id'] == doc_id]['contents'].iloc[0]
            contents.append(content)
        return contents

    async def evaluate(self, qid: str, doc_ids: List[str]):
        """
        Evaluate context precision and recall for given query ID and document IDs.
        
        Args:
            qid (str): Question ID to retrieve query and answer from QA train data
            doc_ids (List[str]): Document IDs to retrieve content for evaluation
            
        Returns:
            dict: Evaluation results including scores and reasons
        """
        # Get query and answer based on QID
        qa_data = self._get_qa_by_qid(qid)
        query = qa_data['query']
        answer = qa_data['generation_gt']
        
        # Get content based on document IDs
        retrieval_context = self._get_content_by_doc_ids(doc_ids)
        
        # Create test case
        test_case = LLMCase(
            user_input=query,
            expected_output=answer,
            retrieval_context=retrieval_context
        )
        
        # Initialize metrics with a model (using a mock for demonstration)
        model = llm_factory(
            model="qwen/qwen3-next-80b-a3b-instruct",
            base_url="https://integrate.api.nvidia.com/v1",
            api_key="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"  # 请替换为有效密钥
        )
        context_precision = ContextPrecision(model=model)
        context_recall = ContextRecall(model=model)
        
        # Evaluate metrics
        precision_result = await context_precision._compute(test_case=test_case)
        recall_result = await context_recall._compute(test_case=test_case)
        
        # Return results
        return {
            "qid": qid,
            "query": query,
            "answer": answer,
            "doc_ids": doc_ids,
            "retrieval_context": retrieval_context,
            "context_precision_score": precision_result.score,
            "context_precision_reason": precision_result.reason,
            "context_recall_score": recall_result.score,
            "context_recall_reason": recall_result.reason
        }


async def main():
    """
    Main function to demonstrate usage.
    """
    # Initialize debug tool
    debug_tool = DebugSemanticSearch(
        corpus_file_path="D:/diting/packages/diting-core/src/diting_core/optimization/datasets/retrieval_data/corpus.csv",
        qa_train_file_path="D:/diting/packages/diting-core/src/diting_core/optimization/datasets/retrieval_data/qa_train.csv"
    )
    
    # Example usage - replace with actual user inputs
    qid = "1oy5tc"  # Example qid from qa_train.csv
    doc_ids = ["5b957791-3c7b-4f29-a410-8d005a538855", "3feb6f59-63df-487f-af3f-489072fc11cb", "3dfb85e0-33a8-47c4-bd9c-a14c3f400dba", "248999d2-b6c2-4ad1-b86a-eedc772d0266", "21b30f0b-5097-47aa-8164-1167576f62f4", "4cab6831-bb9c-4246-b768-fbe9710cf2f0", "0c6974af-e284-4365-a8aa-456a583e820d"]  # Example doc_id from corpus
    
    # Evaluate
    results = await debug_tool.evaluate(qid, doc_ids)
    
    # Print results
    print("Evaluation Results:")
    print(f"QID: {results['qid']}")
    print(f"Query: {results['query']}")
    print(f"Answer: {results['answer']}")
    print(f"Document IDs: {results['doc_ids']}")
    print(f"Context Precision Score: {results['context_precision_score']}")
    print(f"Context Precision Reason: {results['context_precision_reason']}")
    print(f"Context Recall Score: {results['context_recall_score']}")
    print(f"Context Recall Reason: {results['context_recall_reason']}")


if __name__ == "__main__":
    asyncio.run(main())