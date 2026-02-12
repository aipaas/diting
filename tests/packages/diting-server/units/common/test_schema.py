#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pytest
from pydantic import ValidationError

from diting_server.common.schema import (
    BaseSchema,
    SchemaBase,
    StatusEnum,
)


class TestBaseSchema:
    """Test cases for BaseSchema class."""

    def test_base_schema_creation(self):
        """Test BaseSchema can be created with valid data."""

        class TestSchema(BaseSchema):
            user_name: str
            api_key: str

        schema = TestSchema(userName="test_user", apiKey="test_key")
        assert schema.user_name == "test_user"
        assert schema.api_key == "test_key"

    def test_camel_case_alias(self):
        """Test that camelCase aliases work correctly."""

        class TestSchema(BaseSchema):
            user_name: str
            api_key: str

        # Should accept both snake_case and camelCase
        schema1 = TestSchema(user_name="test_user", api_key="test_key")
        schema2 = TestSchema(userName="test_user", apiKey="test_key")

        assert schema1.user_name == schema2.user_name
        assert schema1.api_key == schema2.api_key

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden by default."""

        class TestSchema(BaseSchema):
            user_name: str

        with pytest.raises(ValidationError):
            TestSchema(user_name="test", extra_field="not_allowed")

    def test_from_attributes_enabled(self):
        """Test that from_attributes is enabled."""

        class TestSchema(BaseSchema):
            user_name: str

        # This should work with from_attributes=True
        class TestObject:
            def __init__(self):
                self.user_name = "test_user"

        obj = TestObject()
        schema = TestSchema.model_validate(obj)
        assert schema.user_name == "test_user"


class TestSchemaBase:
    """Test cases for SchemaBase class."""

    def test_schema_base_creation(self):
        """Test SchemaBase can be created."""

        class TestSchema(SchemaBase):
            status: str

        schema = TestSchema(status="active")
        assert schema.status == "active"

    def test_use_enum_values(self):
        """Test that use_enum_values is enabled."""

        class TestSchema(SchemaBase):
            status: StatusEnum

        schema = TestSchema(status=StatusEnum.SUCCESS)
        # Should use enum value, not enum object
        assert schema.status == "success"


class TestStatusEnum:
    """Test cases for StatusEnum enum."""

    def test_status_enum_values(self):
        """Test StatusEnum values."""
        assert StatusEnum.SUCCESS == "success"
        assert StatusEnum.FAILED == "failed"

    def test_status_enum_string_enum(self):
        """Test that StatusEnum is a string enum."""
        assert isinstance(StatusEnum.SUCCESS, str)
        assert isinstance(StatusEnum.FAILED, str)

    def test_status_enum_comparison(self):
        """Test StatusEnum comparison."""
        assert StatusEnum.SUCCESS == "success"
        assert StatusEnum.FAILED == "failed"
        assert StatusEnum.SUCCESS != StatusEnum.FAILED
