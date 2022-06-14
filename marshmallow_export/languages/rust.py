from enum import Enum, EnumMeta

from marshmallow import Schema, fields
from marshmallow_enum import EnumField

from .abstract import AbstractLanguage
from marshmallow_export.types import Mapping, EnumInfo, SchemaInfo

from typing import Tuple, Dict, Any, List


DEFAULT_ENUM_DERIVES = [
    Mapping(mapping='Debug'),
    Mapping(mapping='Clone'),
    Mapping(mapping='Copy'),
    Mapping(mapping='Serialize', imports={'serde': ['Serialize']}),
    Mapping(mapping='Deserialize', imports={'serde': ['Deserialize']}),
    Mapping(mapping='EnumString', imports={'strum_macros': ['EnumString']}),
]


DEFAULT_SCHEMA_DERIVES = [
    Mapping(mapping='Debug'),
    Mapping(mapping='Clone'),
    Mapping(mapping='Copy'),
    Mapping(mapping='Serialize', imports={'serde': ['Serialize']}),
    Mapping(mapping='Deserialize', imports={'serde': ['Deserialize']}),
]


class Types(Enum):
    BOOL = Mapping(mapping='bool')
    INTEGER = Mapping(mapping='i64')
    FLOAT = Mapping(mapping='f64')
    DECIMAL = Mapping(mapping='Decimal', imports={'rust_decimal': ['Decimal']})
    STRING = Mapping(mapping='String')
    DATE_TIME_AWARE = Mapping(mapping='DateTime<Utc>', imports={'chrono': ['DateTime', 'Utc']})
    UUID = Mapping(mapping='Uuid', imports={'uuid': ['Uuid']})


type_mappings = {
    fields.Bool: Types.BOOL.value,
    fields.Boolean: Types.BOOL.value,
    fields.Constant: Types.STRING.value,
    fields.DateTime: Types.DATE_TIME_AWARE.value,
    fields.Decimal: Types.DECIMAL.value,
    fields.Dict: None,
    fields.Email: Types.STRING.value,
    fields.Field: None,
    fields.Float: Types.FLOAT.value,
    fields.Function: None,
    fields.Int: Types.INTEGER.value,
    fields.Integer: Types.INTEGER.value,
    fields.Mapping: None,
    fields.Method: None,
    fields.Number: Types.FLOAT.value,
    fields.Raw: None,
    fields.Str: Types.STRING.value,
    fields.String: Types.STRING.value,
    fields.TimeDelta: None,
    fields.Url: Types.STRING.value,
    fields.UUID: Types.UUID.value,
}


class Rust(AbstractLanguage):

    @property
    def type_mappings(self) -> Dict[fields.Field, Mapping]:
        return type_mappings

    @staticmethod
    def get_default_kwargs() -> Dict[str, Any]:
        return {
            'rust_enum_derives': DEFAULT_ENUM_DERIVES,
            'rust_schema_derives': DEFAULT_SCHEMA_DERIVES,
        }

    @staticmethod
    def _format_enum_field(field_name: str, value: Enum) -> str:
        return f'    {field_name},'

    @staticmethod
    def _format_enum(e: EnumMeta, enum_fields: List[str], enum_info: EnumInfo) -> str:
        enum_fields = '\n'.join(enum_fields)
        derives = ''
        if 'rust_enum_derives' in enum_info.kwargs and len(enum_info.kwargs['rust_enum_derives']) > 0:
            derives = f'#[derive({", ".join([m.mapping for m in enum_info.kwargs["rust_enum_derives"]])})]\n'

        return f'{derives}pub enum {e.__name__} {{\n{enum_fields}\n}}\n'

    def format_header(
            self,
            namespace: str,
            include_dump_only: bool,
            include_load_only: bool
    ) -> str:
        imports = dict()
        for schema, schema_info in self.schemas[namespace].items():
            if 'rust_schema_derives' in schema_info.kwargs:
                for rust_derive in schema_info.kwargs['rust_schema_derives']:
                    if isinstance(rust_derive.imports, dict):
                        for lib, imp in rust_derive.imports.items():
                            if not lib in imports:
                                imports[lib] = set()
                            
                            imports[lib].update(imp)

            for ma_field in schema._declared_fields.values():
                if not include_dump_only and ma_field.dump_only:
                    continue

                if not include_load_only and ma_field.load_only:
                    continue

                if isinstance(ma_field, fields.List):
                    ma_field = ma_field.inner
                
                if ma_field.__class__ not in self.type_mappings:
                    continue

                export_type = self.type_mappings[ma_field.__class__]
                if not isinstance(export_type.imports, dict):
                    continue

                for lib, imp in export_type.imports.items():
                    if not lib in imports:
                        imports[lib] = set()
                    
                    imports[lib].update(imp)
        
        imports = sorted(list(imports.items()), key=lambda e: e[0].lower())
        return '\n'.join([
            f'use {lib}::{"{" if len(imp) > 1 else ""}{", ".join(imp)}{"}" if len(imp) > 1 else ""};'
            for lib, imp in imports 
        ]) + '\n'

    def _format_schema_field(
            self,
            field_name: str,
            ma_field: fields.Field
    ) -> str:
        export_type, many = self.map_schema_field(ma_field)

        if many:
            export_type = f'Vec<{export_type}>'
        
        if ma_field.allow_none or not ma_field.required:
            export_type = f'Option<{export_type}>'
        
        return f'    pub {field_name}: {export_type},'

    def _format_schema(
            self,
            schema: Schema,
            schema_info: SchemaInfo,
            schema_fields: List[str]
    ) -> str:
        schema_name = self.get_schema_export_name(schema)
        schema_fields = '\n'.join(schema_fields)
        derives = ''

        if 'rust_schema_derives' in schema_info.kwargs and len(schema_info.kwargs['rust_schema_derives']) > 0:
            derives = f'#[derive({", ".join([m.mapping for m in schema_info.kwargs["rust_schema_derives"]])})]\n'

        return f'{derives}pub struct {schema_name} {{\n{schema_fields}\n}}\n'

