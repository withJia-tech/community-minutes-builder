"""Packaging checks. Pure Python, so they run without the claude CLI."""
import json
import os
import re
import shlex

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


GUIDE = REPO / 'docs' / 'volunteer-guide.md'


def test_paths_named_in_volunteer_guide_exist():
    text = GUIDE.read_text(encoding='utf-8')
    skill_paths = set(re.findall(
        r'(?<![\w/.-])((?:references|scripts)/[\w./-]*?\.(?:md|py))\b', text))
    repo_paths = set(re.findall(r'(?<![\w/.-])(skills/[\w./-]*[\w-])', text))
    assert skill_paths and repo_paths, 'the guide should name the files it tells people to use'
    missing = sorted(p for p in skill_paths if not (SKILL / p).is_file())
    missing += sorted(p for p in repo_paths if not (REPO / p).exists())
    assert not missing, 'docs/volunteer-guide.md names missing paths: %s' % missing


def test_volunteer_guide_install_command_matches_the_marketplace():
    market = json.loads((REPO / '.claude-plugin' / 'marketplace.json').read_text(encoding='utf-8'))
    plugin = market['plugins'][0]['name']
    text = GUIDE.read_text(encoding='utf-8')
    assert '/plugin install %s@%s' % (plugin, market['name']) in text


# --- plugin packaging ----------------------------------------------------------

MARKETPLACE = REPO / '.claude-plugin' / 'marketplace.json'
PLUGINS = REPO / 'plugins'
EMAIL = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def plugin_roots():
    roots = []
    for entry in load_json(MARKETPLACE)['plugins']:
        roots.append((entry, (REPO / entry['source']).resolve()))
    return roots


def test_marketplace_sources_hold_matching_plugin_manifests():
    market = load_json(MARKETPLACE)
    assert market.get('name') and market.get('owner', {}).get('name')
    assert market['plugins'], 'marketplace lists no plugins'
    for entry, root in plugin_roots():
        manifest = root / '.claude-plugin' / 'plugin.json'
        assert root.is_dir(), '%s: source %s missing' % (entry['name'], entry['source'])
        assert manifest.is_file(), '%s has no plugin.json' % root
        assert load_json(manifest)['name'] == entry['name']


def test_plugin_skill_paths_resolve_to_skill_folders():
    for entry, root in plugin_roots():
        skills = load_json(root / '.claude-plugin' / 'plugin.json').get('skills', [])
        skills = [skills] if isinstance(skills, str) else skills
        assert skills, '%s declares no skills' % entry['name']
        for rel in skills:
            folder = root / rel
            assert (folder / 'SKILL.md').is_file(), '%s: %s has no SKILL.md' % (
                entry['name'], rel)
            name = frontmatter(folder / 'SKILL.md')['name']
            assert name == os.path.basename(os.path.normpath(rel))


def test_hook_commands_point_at_existing_scripts():
    for entry, root in plugin_roots():
        hooks_file = root / 'hooks' / 'hooks.json'
        if not hooks_file.exists():
            continue
        commands = [h['command']
                    for groups in load_json(hooks_file)['hooks'].values()
                    for group in groups for h in group['hooks']
                    if h.get('type') == 'command']
        assert commands
        for command in commands:
            expanded = command.replace('${CLAUDE_PLUGIN_ROOT}', str(root))
            scripts = [t for t in shlex.split(expanded) if t.endswith('.py')]
            assert scripts, 'no script in hook command %r' % command
            for script in scripts:
                assert os.path.isfile(script), 'hook script missing: %s' % script


def test_no_symlink_under_plugins_loops_into_an_ancestor():
    links = []
    for dirpath, dirnames, filenames in os.walk(PLUGINS):
        for name in dirnames + filenames:
            path = os.path.join(dirpath, name)
            if os.path.islink(path):
                links.append(path)
    assert links, 'expected the skill symlink under plugins/'
    for link in links:
        target = os.path.realpath(link)
        assert os.path.exists(target), '%s is a dangling symlink' % link
        ancestor = os.path.realpath(os.path.dirname(link))
        while True:
            assert target != ancestor, '%s points back at its ancestor %s' % (
                link, ancestor)
            parent = os.path.dirname(ancestor)
            if parent == ancestor:
                break
            ancestor = parent


def test_manifests_carry_no_email_address():
    for path in [MARKETPLACE] + sorted(PLUGINS.glob('*/.claude-plugin/plugin.json')):
        assert not EMAIL.search(path.read_text(encoding='utf-8')), path


def test_example_profile_is_a_valid_profile():
    example = SKILL / 'examples' / 'committee-profile.example.json'
    profile = load_json(example)
    assert set(profile) <= {'term_replacements', 'people', 'action_tags'}
    assert isinstance(profile['term_replacements'], dict)
    assert all(p.get('name') for p in profile['people'])
    assert isinstance(profile['action_tags'], list)
    assert not EMAIL.search(example.read_text(encoding='utf-8'))


def test_version_is_set_in_plugin_json_only():
    # With a version in both places Claude Code silently uses plugin.json's.
    for entry, root in plugin_roots():
        assert 'version' not in entry, '%s: set version in plugin.json only' % entry['name']
        assert load_json(root / '.claude-plugin' / 'plugin.json').get('version')
