"""Packaging checks. Pure Python, so they run without the claude CLI."""
import re

from helpers import REPO, SKILL


def frontmatter(path):
    text = path.read_text(encoding='utf-8')
    m = re.match(r'---\n(.*?)\n---\n', text, re.S)
    assert m, '%s has no YAML frontmatter' % path
    fields = {}
    for line in m.group(1).splitlines():
        km = re.match(r'([A-Za-z][\w-]*):\s*(.*)$', line)
        if km:
            value = km.group(2).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
                value = value[1:-1]
            fields[km.group(1)] = value
    return fields


def skill_dirs():
    return sorted(p.parent for p in (REPO / 'skills').glob('*/SKILL.md'))


def test_every_skill_has_name_and_description_matching_its_folder():
    dirs = skill_dirs()
    assert SKILL in dirs
    for skill in dirs:
        fields = frontmatter(skill / 'SKILL.md')
        assert fields.get('name'), '%s: frontmatter needs a name' % skill
        assert fields.get('description'), '%s: frontmatter needs a description' % skill
        assert fields['name'] == skill.name


def test_paths_named_in_skill_md_exist():
    for skill in skill_dirs():
        text = (skill / 'SKILL.md').read_text(encoding='utf-8')
        named = set(re.findall(
            r'(?<![\w/.-])((?:references|scripts)/[\w./-]*?\.(?:md|py))\b', text))
        assert named, '%s names no references or scripts' % skill
        missing = sorted(p for p in named if not (skill / p).is_file())
        assert not missing, '%s names missing files: %s' % (skill, missing)
