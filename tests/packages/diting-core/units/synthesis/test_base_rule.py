#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch, AsyncMock
from diting_core.synthesis.rules.base_rule import BaseGenerateRule


class MockGenerateRule(BaseGenerateRule):
    async def _apply(self, rule_input, **kwargs):
        return {field: f"output_{field}" for field in self.required_output_fields}


class TestBaseGenerateRule(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.rule = MockGenerateRule()
        self.rule.required_input_fields = ["input_field"]
        self.rule.required_output_fields = ["output_field"]

    async def test_apply_success(self):
        """测试正常情况下的apply方法"""
        rule_input = {"input_field": "input_value"}
        result = await self.rule.apply(rule_input)
        self.assertEqual(result, {"output_field": "output_output_field"})

    async def test_apply_missing_input_field(self):
        """测试缺少输入字段时抛出断言错误"""
        rule_input = {}
        with self.assertRaises(Exception):
            await self.rule.apply(rule_input)

    async def test_apply_invalid_output(self):
        """测试输出字段不符合预期时抛出断言错误"""
        with patch(
            "diting_core.synthesis.rules.base_rule.assert_fields_validity",
            side_effect=Exception("Invalid output"),
        ):
            rule_input = {"input_field": "input_value"}
            with self.assertRaises(Exception):
                await self.rule.apply(rule_input)

    async def test_apply_with_callbacks(self):
        """测试带有回调的apply方法"""
        rule_input = {"input_field": "input_value"}
        callbacks = [AsyncMock()]
        result = await self.rule.apply(rule_input, callbacks=callbacks)
        self.assertEqual(result, {"output_field": "output_output_field"})

    async def test_apply_with_verbose(self):
        """测试带有verbose参数的apply方法"""
        rule_input = {"input_field": "input_value"}
        result = await self.rule.apply(rule_input, verbose=True)
        self.assertEqual(result, {"output_field": "output_output_field"})

    async def test_name_property(self):
        """测试name属性"""
        self.assertEqual(self.rule.name, "mock_generate_rule")


if __name__ == "__main__":
    unittest.main()
