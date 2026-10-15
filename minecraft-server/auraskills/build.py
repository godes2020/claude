#!/usr/bin/env python3
"""Собирает AuraSkills + пак Animated Aurelium Skills под CraftEngine на русском.

Запуск:
  python3 build.py <animated_aurelium_skills.zip> <AuraSkills-2.4.0.jar>

Результат кладётся в ./upload/ (структура как у сервера: upload/plugins/...),
и рядом создаётся auraskills-upload.zip для заливки через панель.
"""
import io
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

from PIL import Image
from ruamel.yaml import YAML

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from translations import RU  # noqa: E402

NS = 'spectra_aurelium_skills'
OUT = HERE / 'upload'
PLUGINS = OUT / 'plugins'
CE_PACK = PLUGINS / 'CraftEngine' / 'resources' / 'auraskills'
ASSETS = CE_PACK / 'resourcepack' / 'assets' / NS
AURA = PLUGINS / 'AuraSkills'

IA_ROOT = 'choose your plugin/itemsadder drag and drop/auraskill v2/'
IA_CONTENT = IA_ROOT + 'itemsadder/contents/spectra_aurelium_skills/'

# ---------------------------------------------------------------- шрифт меню
# Фоны меню и полоска опыта рисуются символами шрифта spectra_aurelium_skills:gui.
GUI_FONT = f'{NS}:gui'
BACKGROUNDS = {  # имя картинки из пака -> символ
    'skills_menu_book': '',
    'abilities_menu': '',
    'progress_menu': '',
    'stats_menu': '',
    'leaderboard_menu': '',
    'book_all_squares': '',
}
XP_BAR = ''
SPACES = {-2: '', -12: '', -18: '', -20: ''}

# Русские надписи на деревянных плашках фонов.
TITLES = {
    'skills_menu_book': 'НАВЫКИ',
    'abilities_menu': 'СПОСОБНОСТИ',
    'progress_menu': 'УРОВНИ',
    'stats_menu': 'ХАРАКТЕРИСТИКИ',
    'leaderboard_menu': 'ТОП ИГРОКОВ',
    'book_all_squares': 'ИСТОЧНИКИ ОПЫТА',
}

# ------------------------------------------------------- модели предметов
# CustomModelData из меню пака -> имя предмета (и item_model).
CMD = {
    40047: 'skills_level_close', 40048: 'skill_farming', 40049: 'skill_foraging',
    40051: 'skill_empty_slot', 40052: 'skill_left_arrow', 40053: 'skill_right_arrow',
    40054: 'skills_level_next', 40055: 'skills_level_previous', 40056: 'skills_abilities_btn',
    40057: 'skills_xp_source_btn', 40058: 'skills_leaderboard_btn', 40059: 'skill_fishing',
    40060: 'skill_archery', 40061: 'skill_defence', 40062: 'skill_excavation',
    40063: 'skill_agility', 40064: 'skill_fighting', 40065: 'skill_enchanting',
    40066: 'skill_alchemy', 40067: 'skill_mining', 40068: 'skills_level_completed',
    40069: 'skills_level_locked', 40070: 'skills_level_progress', 40071: 'book_previous_nav',
    40072: 'book_next_nav', 40073: 'stats_animation', 40074: 'monster_head',
    40075: 'monster_body_right', 40076: 'monster_body_left', 40077: 'skill_ship',
    40078: 'skill_flag', 40079: 'icon_mana', 40080: 'icon_ability', 40081: 'icon_mana_locked',
    40082: 'icon_ability_locked', 40083: 'job_icon_enabled', 40084: 'job_icon_off',
    100: 'skills_head',
}
# Предметы с плоской текстурой: имя -> текстура.
GENERATED = {
    'skill_empty_slot': 'empty_slot', 'skill_left_arrow': 'left_arrow',
    'skill_right_arrow': 'right_arrow', 'skills_level_next': 'skills_level_next',
    'skills_level_previous': 'skills_level_previous', 'skills_abilities_btn': 'skills_abilities_btn',
    'skills_xp_source_btn': 'skills_xp_source_btn', 'skills_leaderboard_btn': 'skills_leaderboard_btn',
    'skills_level_close': 'skills_level_close', 'skills_level_completed': 'skills_level_completed',
    'skills_level_locked': 'skills_level_locked', 'skills_level_progress': 'skills_level_progress',
    'icon_mana': 'icon_mana', 'icon_ability': 'icon_ability', 'icon_mana_locked': 'icon_mana_locked',
    'icon_ability_locked': 'icon_ability_locked', 'job_icon_enabled': 'job_icon_enabled',
    'job_icon_off': 'job_icon_off',
}
for s in ['farming', 'foraging', 'mining', 'fishing', 'excavation', 'archery', 'defence',
          'fighting', 'endurance', 'agility', 'alchemy', 'enchanting', 'sorcery', 'healing', 'forging']:
    GENERATED[f'skill_{s}'] = f'skill_{s}'
# Предметы с моделью из Blockbench.
CUSTOM_MODELS = ['book_previous_nav', 'book_next_nav', 'stats_animation', 'monster_head',
                 'monster_body_right', 'monster_body_left', 'skill_ship', 'skill_flag']

# ------------------------------------------------- пиксельный шрифт 5px
GLYPHS = {
    'А': ['.XX.', 'X..X', 'XXXX', 'X..X', 'X..X'],
    'Б': ['XXXX', 'X...', 'XXX.', 'X..X', 'XXX.'],
    'В': ['XXX.', 'X..X', 'XXX.', 'X..X', 'XXX.'],
    'Г': ['XXXX', 'X...', 'X...', 'X...', 'X...'],
    'Е': ['XXXX', 'X...', 'XXX.', 'X...', 'XXXX'],
    'И': ['X..X', 'X..X', 'X.XX', 'XX.X', 'X..X'],
    'К': ['X..X', 'X.X.', 'XX..', 'X.X.', 'X..X'],
    'М': ['X...X', 'XX.XX', 'X.X.X', 'X...X', 'X...X'],
    'Н': ['X..X', 'X..X', 'XXXX', 'X..X', 'X..X'],
    'О': ['.XX.', 'X..X', 'X..X', 'X..X', '.XX.'],
    'П': ['XXXX', 'X..X', 'X..X', 'X..X', 'X..X'],
    'Р': ['XXX.', 'X..X', 'XXX.', 'X...', 'X...'],
    'С': ['.XXX', 'X...', 'X...', 'X...', '.XXX'],
    'Т': ['XXX', '.X.', '.X.', '.X.', '.X.'],
    'У': ['X..X', 'X..X', '.XXX', '...X', 'XXX.'],
    'Х': ['X..X', 'X..X', '.XX.', 'X..X', 'X..X'],
    'Ч': ['X..X', 'X..X', '.XXX', '...X', '...X'],
    'Ы': ['X...X', 'X...X', 'XXX.X', 'X.X.X', 'XXX.X'],
    ' ': ['..', '..', '..', '..', '..'],
}
TOP = (214, 128, 86, 255)     # светлая верхняя грань буквы
MID = (168, 84, 42, 255)      # тело буквы
BOT = (191, 96, 48, 255)      # нижняя строка буквы
SHADOW = (81, 43, 22, 255)    # тёмная обводка сверху-слева
LINE_DARK = (125, 61, 36, 255)
TEXT_COLORS = {TOP[:3], MID[:3], BOT[:3]}


def text_mask(text):
    cols = []
    for i, ch in enumerate(text):
        g = GLYPHS[ch]
        if i:
            cols.append([False] * 5)
        for x in range(len(g[0])):
            cols.append([g[y][x] == 'X' for y in range(5)])
    return cols  # список столбцов по 5 пикселей


def retitle(im, text):
    """Стирает английскую надпись на плашке и рисует русскую в том же стиле."""
    px = im.load()
    border = [x for x in range(im.width) if px[x, 44][:3] in TEXT_COLORS]
    left, right = min(border), max(border)
    pts = [x for y in range(45, 52) for x in range(left + 3, right - 2) if px[x, y][:3] in TEXT_COLORS]
    old0, old1 = min(pts) - 1, max(pts) + 1
    ref = left + 6
    for y in range(44, 53):
        for x in range(old0 - 1, old1 + 2):
            px[x, y] = px[ref, y]
    cols = text_mask(text)
    width = len(cols)
    x0 = round((left + right + 1) / 2 - width / 2)
    if x0 < left + 4 or x0 + width > right - 4:
        raise SystemExit(f'надпись «{text}» не помещается на плашку')
    # светлая полоса посередине прерывается под текстом, как в оригинале
    for x in range(x0 - 2, x0 + width + 2):
        px[x, 49] = LINE_DARK
    on = {(x0 + cx, 46 + cy) for cx, col in enumerate(cols) for cy, v in enumerate(col) if v}
    for (x, y) in on:
        if (x - 1, y - 1) not in on:
            px[x - 1, y - 1] = SHADOW
    for (x, y) in on:
        row = y - 46
        if row == 4:
            px[x, y] = BOT
        elif row == 0 or (row == 1 and (x, y - 1) not in on):
            px[x, y] = TOP
        else:
            px[x, y] = MID


# ------------------------------------------------------------- утилиты
def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def yaml_rt():
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=2, sequence=2, offset=0)
    return y


def build_resourcepack(z):
    tex_dir = ASSETS / 'textures'
    for name in z.namelist():
        if name.startswith(IA_CONTENT + 'textures/') and not name.endswith('/'):
            data = z.read(name)
            base = name.rsplit('/', 1)[1]
            stem = base.split('.')[0]
            if base.endswith('.png') and stem in TITLES:
                im = Image.open(io.BytesIO(data)).convert('RGBA')
                retitle(im, TITLES[stem])
                buf = io.BytesIO()
                im.save(buf, 'PNG')
                data = buf.getvalue()
            (tex_dir / base).parent.mkdir(parents=True, exist_ok=True)
            (tex_dir / base).write_bytes(data)
        elif name.startswith(IA_CONTENT + 'sounds/') and name.endswith('.ogg'):
            p = ASSETS / 'sounds' / name.rsplit('/', 1)[1]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(z.read(name))
    (ASSETS / 'sounds.json').write_bytes(z.read(IA_CONTENT + 'sounds.json'))

    # шрифт
    providers = [{'type': 'bitmap', 'file': f'{NS}:{n}.png', 'height': 256, 'ascent': 48, 'chars': [c]}
                 for n, c in BACKGROUNDS.items()]
    providers.append({'type': 'bitmap', 'file': f'{NS}:xp_bar_white.png', 'height': 7, 'ascent': 6, 'chars': [XP_BAR]})
    providers.append({'type': 'space', 'advances': {c: v for v, c in SPACES.items()}})
    write_json(ASSETS / 'font' / 'gui.json', {'providers': providers})

    # модели и определения предметов
    for item, tex in GENERATED.items():
        write_json(ASSETS / 'models' / 'item' / f'{item}.json',
                   {'parent': 'minecraft:item/generated', 'textures': {'layer0': f'{NS}:{tex}'}})
        write_json(ASSETS / 'items' / f'{item}.json',
                   {'model': {'type': 'minecraft:model', 'model': f'{NS}:item/{item}'}})
    for item in CUSTOM_MODELS:
        model = json.loads(z.read(IA_CONTENT + f'models/{item}.json'))
        model.pop('credit', None)
        for el in model.get('elements', []):
            el['faces'] = {k: f for k, f in el['faces'].items() if f.get('texture') != '#missing'}
        write_json(ASSETS / 'models' / 'item' / f'{item}.json', model)
        write_json(ASSETS / 'items' / f'{item}.json',
                   {'model': {'type': 'minecraft:model', 'model': f'{NS}:item/{item}'}})
    # голова игрока крупным планом: модель головы + скин из профиля предмета
    head = json.loads(z.read(IA_CONTENT + 'models/skills_head.json'))
    head.pop('credit', None)
    write_json(ASSETS / 'models' / 'item' / 'skills_head.json', head)
    write_json(ASSETS / 'items' / 'skills_head.json', {
        'model': {'type': 'minecraft:special', 'base': f'{NS}:item/skills_head',
                  'model': {'type': 'minecraft:player_head'}},
        'oversized_in_gui': True,
    })

    (CE_PACK / 'pack.yml').write_text(
        'author: Spectra (порт под CraftEngine)\n'
        'version: 0.1\n'
        'description: Анимированные меню AuraSkills\n'
        f'namespace: {NS}\n'
        'enable: true\n', encoding='utf-8')


# ---------------------------------------------------------------- меню
def gui(text):
    return f'<font:{GUI_FONT}>{text}</font>'


def convert_menu_text(s):
    alias = {'skill_book_sources': 'book_all_squares'}
    s = re.sub(r':offset_(-?\d+): *%img_([a-z_]+)%',
               lambda m: gui(SPACES[int(m.group(1))] + BACKGROUNDS[alias.get(m.group(2), m.group(2))]), s)
    s = s.replace('%img_offset_-2%%img_xp_bar_white_lore%', gui(SPACES[-2] + XP_BAR))
    s = re.sub(r'%tinify_([^%]+)%', r'\1', s)
    return s


# Английский текст, вписанный прямо в меню пака.
MENU_LITERALS = [
    ('<#82CD47>Lvl {level}', '<#82CD47>Ур. {level}'),
    ("<gray>▪ Job", "<gray>▪ Профессия"),
    ('<gold>(MAXED)', '<gold>(МАКС.)'),
    (' ▪ ᴍᴀɴᴀ ᴀʙɪʟɪᴛɪᴇѕ', ' ▪ Способность маны'),
    ('% / Mana ', '% / ед. маны '),
    ('{duration}s ', '{duration} сек. '),
    ('{cooldown}s ', '{cooldown} сек. '),
    ('<gray> ▪ {xp_unit}: {source_xp}', '<gray> ▪ Опыт: {source_xp}'),
]


def fix_item_models(node):
    """nbt: {CustomModelData: N} -> item_model: spectra_aurelium_skills:<имя>."""
    if isinstance(node, dict):
        if 'nbt' in node and isinstance(node['nbt'], dict) and 'CustomModelData' in node['nbt']:
            cmd = int(node['nbt']['CustomModelData'])
            keys = list(node.keys())
            pos = keys.index('nbt')
            del node['nbt']
            node.insert(pos, 'item_model', f'{NS}:{CMD[cmd]}')
        for v in node.values():
            fix_item_models(v)
    elif isinstance(node, list):
        for v in node:
            fix_item_models(v)


def convert_menus(z, jar):
    y = yaml_rt()
    menu_dir = AURA / 'menus'
    menu_dir.mkdir(parents=True, exist_ok=True)
    for name in ['abilities', 'leaderboard', 'level_progression', 'skills', 'sources', 'stats']:
        raw = z.read(IA_ROOT + f'AuraSkills/menus/{name}.yml').decode('utf-8')
        for a, b in MENU_LITERALS:
            raw = raw.replace(a, b)
        raw = convert_menu_text(raw)
        data = y.load(raw)
        fix_item_models(data)
        default = y.load(jar.read(f'menus/{name}.yml').decode('utf-8'))
        # ключи, появившиеся в AuraSkills 2.4.0 после выхода пака
        if name == 'level_progression':
            data['components']['job_cooldown'] = default['components']['job_cooldown']
            for item in ('job', 'job(1)'):
                data['items'][item]['lore'].append({'component': 'job_cooldown'})
        for k, v in default.get('options', {}).items():
            data.setdefault('options', {})
            if k not in data['options']:
                data['options'][k] = v
        if 'file_version' in default:
            data['file_version'] = default['file_version']
        with open(menu_dir / f'{name}.yml', 'w', encoding='utf-8') as f:
            y.dump(data, f)
    # меню подробностей характеристики в паке нет — берём стандартное
    (menu_dir / 'stat_info.yml').write_bytes(jar.read('menus/stat_info.yml'))


# ----------------------------------------------------------- сообщения
PLACEHOLDER = re.compile(r'\{[a-z_0-9]+\}|<[a-z_/#0-9]+>')


def build_messages(jar):
    y = yaml_rt()
    data = y.load(jar.read('messages/messages_en.yml').decode('utf-8'))
    seen = set()
    problems = []

    def fill(node, prefix=''):
        for k in list(node.keys()):
            key = f'{prefix}.{k}' if prefix else str(k)
            v = node[k]
            if isinstance(v, dict):
                fill(v, key)
            elif key == 'file_version':
                continue
            else:
                if key not in RU:
                    problems.append(f'нет перевода: {key}')
                    continue
                seen.add(key)
                lost = set(PLACEHOLDER.findall(str(v))) - set(PLACEHOLDER.findall(RU[key]))
                # единицы вписаны словом в нужном падеже, <page> в подсказке — не тег
                lost -= {'{xp_unit}', '{mana_unit}', '<page>'}
                if lost:
                    problems.append(f'потерян плейсхолдер в {key}: {v!r} -> {RU[key]!r}')
                node[k] = RU[key]
    fill(data)
    extra = set(RU) - seen
    if extra:
        problems += [f'лишний ключ: {k}' for k in sorted(extra)]
    if problems:
        raise SystemExit('\n'.join(problems))
    msg_dir = AURA / 'messages'
    msg_dir.mkdir(parents=True, exist_ok=True)
    with open(msg_dir / 'messages_ru.yml', 'w', encoding='utf-8') as f:
        y.dump(data, f)
    # Порядок слов в экшн-баре удобнее для русского: «+5 опыта · Фермерство».
    glob = jar.read('messages/global.yml').decode('utf-8')
    glob = glob.replace('{xp_gained} {skill} {{units.xp}}', '{xp_gained} {{units.xp}} <gray>· <gold>{skill}')
    (msg_dir / 'global.yml').write_text(glob, encoding='utf-8')


def build_config(jar):
    cfg = jar.read('config.yml').decode('utf-8')
    cfg = cfg.replace('default_language: en', 'default_language: ru', 1)
    (AURA / 'config.yml').write_text(cfg, encoding='utf-8')


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    pack_zip, jar_path = sys.argv[1], sys.argv[2]
    if OUT.exists():
        shutil.rmtree(OUT)
    with zipfile.ZipFile(pack_zip) as z, zipfile.ZipFile(jar_path) as jar:
        build_resourcepack(z)
        convert_menus(z, jar)
        build_messages(jar)
        build_config(jar)
    shutil.copy(jar_path, PLUGINS / 'AuraSkills-2.4.0.jar')
    archive = HERE / 'auraskills-upload.zip'
    if archive.exists():
        archive.unlink()
    shutil.make_archive(str(archive.with_suffix('')), 'zip', OUT)
    print('готово:', OUT, archive)


if __name__ == '__main__':
    main()
