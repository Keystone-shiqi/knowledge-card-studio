"""Resolve portable visual settings before any speech generation."""
import json
from pathlib import Path

STYLES = json.loads((Path(__file__).parent / 'styles.json').read_text(encoding='utf-8'))
DEFAULT_HEADER = dict(visible=True, section_visible=True, tagline='知识 · 表达',
                      section_prefix='', show_number=False, number_start=1, number_pad=2)

def validate_header(value, partial=False):
    if not isinstance(value, dict):
        raise ValueError('header 必须是对象')
    limits = dict(brand=24, tagline=24, section_prefix=12, section_label=24)
    allowed = set(DEFAULT_HEADER) | set(limits)
    for key, item in value.items():
        if key not in allowed:
            raise ValueError('未知 header 字段：' + key)
        if key in limits:
            if not isinstance(item, str) or len(item) > limits[key] or '\n' in item or '\r' in item:
                raise ValueError(f'header.{key} 必须为单行文字，最多{limits[key]}字')
        elif key in ('visible', 'section_visible', 'show_number'):
            if not isinstance(item, bool): raise ValueError('header.'+key+' 必须为布尔值')
        elif key == 'number_start':
            if type(item) is not int or not 0 <= item <= 9999: raise ValueError('number_start 需为0–9999整数')
        elif key == 'number_pad':
            if type(item) is not int or not 1 <= item <= 4: raise ValueError('number_pad 需为1–4整数')
    return value

def resolve_presentation(job, profile, style=None):
    theme = style or job.get('theme') or profile.get('theme') or 'studio-paper'
    if theme not in STYLES: raise ValueError('未知风格：'+str(theme)+'；可选 '+', '.join(STYLES))
    header = dict(DEFAULT_HEADER, brand=profile.get('brand', '教育观察'))
    for source in (profile, job):
        header.update(validate_header(source.get('header', {})))
    validate_header(header)
    for scene in job.get('scenes', []):
        override = validate_header(scene.get('header', {}), partial=True)
        if any(k not in ('section_visible', 'section_prefix', 'section_label', 'show_number') for k in override):
            raise ValueError('单幕 header 仅支持 section_visible/section_prefix/section_label/show_number')
    return theme, header
