#!/usr/bin/python3.7
import os
import requests
from urllib.parse import quote
from shutil import copyfile, rmtree
import re

NEW_SLOT_DIR = './new_slots'
AMULET_DIR = NEW_SLOT_DIR + '/a'
DRAGON_DIR = NEW_SLOT_DIR + '/d'
WEAPON_DIR = NEW_SLOT_DIR + '/w'

ELEMENT_TYPE = ['Flame', 'Water', 'Wind', 'Light', 'Shadow']
WEAPON_TYPE = ['Sword', 'Blade', 'Dagger', 'Axe', 'Lance', 'Bow', 'Wand', 'Staff']

# Queries
MAX = 500
BASE_URL = 'https://dragalialost.gamepedia.com/api.php?action=cargoquery&format=json&limit={}'.format(MAX)

def get_api_request(offset, **kwargs):
    q = '{}&offset={}'.format(BASE_URL, offset)
    for key, value in kwargs.items():
        q += '&{}={}'.format(key, quote(value))
    return q

def get_data(**kwargs):
    offset = 0
    data = []
    while offset % MAX == 0:
        url = get_api_request(offset, **kwargs)
        r = requests.get(url).json()
        try:
            data += r['cargoquery']
            offset += len(data)
        except:
            raise Exception(url)
    return data

def parse_abilities(ability_data):
    ABILITIES_NO_COND = {
        'Skill Damage': 's',
        'Critical Rate': 'cc',
        'Critical Damage': 'cd',
        'Strength': 'a',
        'Force Strike': 'fs',
        'Skill Haste': 'sp',
        'Skill Prep': 'prep',
        'Broken Punisher': 'bk',
        'Overdrive Punisher': 'od',
        'Buff Time': 'bt',
        'Burning Punisher': 'k_burn',
        'Strength Doublebuff': 'bc',
        'Last Offense': 'lo',
    }
    ABILITIES_COND = {
        'Striking Haste': ('sp', 'fs'),
        'Flurry Devastation': ('cc', 'hit15'),
        'Flurry Strength': ('a', 'hit15'),
    }
    ABILITY_PATTERN = re.compile(r'(\(([A-Za-z]*)\))?((Full) HP = |HP (\d+)\% = )?\s*(' + '|'.join(ABILITIES_NO_COND.keys())+ r')?(' + '|'.join(ABILITIES_COND.keys())+ r')?\s*\+(\d+)\%')
    parsed = {}
    for k, v in ability_data.items():
        ability_tuple = None
        condition = None
        res = ABILITY_PATTERN.match(v['Name'])
        if res:
            _, condition, _, cond_full, cond_val, no_cond, cond, value = res.groups()
            ab_cond = None
            if no_cond is not None:
                ab_type = ABILITIES_NO_COND[no_cond]
            elif cond is not None:
                ab_type, ab_cond = ABILITIES_COND[cond]
            else:
                continue
            if ab_type == 'prep':
                ab_val = int(value)
            else:
                ab_val = int(value) / 100
            if cond_full is not None:
                ability_tuple = (ab_type, ab_val, 'hp100')
            elif cond_val is not None:
                ability_tuple = (ab_type, ab_val, 'hp' + cond_val)
            else:
                if ab_cond is not None:
                    ability_tuple = (ab_type, ab_val, ab_cond)
                else:
                    ability_tuple = (ab_type, ab_val)
            if condition in ELEMENT_TYPE:
                condition = 'c.ele == \'{}\''.format(condition.lower())
            if condition in WEAPON_TYPE:
                condition = 'c.wt == \'{}\''.format(condition.lower())
        parsed[k] = {
            'Name': v['Name'],
            'Details': v['Details'],
            'Params': ability_tuple,
            'Condition': condition
        }
    return parsed

def get_ability(thingy, abilities, mode='wp', i_range=3, j_range=3):
    ab_values = []
    cond_ab_values = []
    ability_comment = []
    for i in range(i_range, 0, -1):
        for j in range(j_range, 0, -1):
            key = 'Abilities{}{}'.format(i, j)
            if thingy[key] != '0':
                ab = abilities[thingy[key]]
                if 'Params' in ab and ab['Params'] is not None:
                    if ab['Condition'] is not None:
                        cond_ab_values.append(ab)
                    else:
                        ab_values.append(ab['Params'])
                ability_comment.append(ab['Name'])
                # ability_comment.append(ab['Details'])
                break
    ab_len = len(ab_values)
    if mode == 'wp':
        ability_arr_str = str(ab_values)
        ability_cond_str = ''
        if len(cond_ab_values) > 0:
            combined_ab = ab_values + [x['Params'] for x in cond_ab_values]
            conditions = ' and '.join([x['Condition'] for x in cond_ab_values])
            ability_cond_str = '\n' + ' '*4 + 'def on(self, c):\n'
            ability_cond_str += ' '*8 + 'if {}:\n'.format(conditions)
            ability_cond_str += ' '*12 + 'self.a = ' + str(combined_ab)
            ab_len = len(combined_ab)
    else:
        combined_ab = ab_values + [x['Params'] for x in cond_ab_values]
        ability_arr_str = str(combined_ab)
        ab_len = len(ab_values)
        ability_cond_str = ''

    ability_comment_str = '\n    # ' + '\n    # '.join(ability_comment)
    return ability_arr_str + ability_cond_str + ability_comment_str, ab_len

def abbreviateClassName(name):
    abbr = name[0]
    prev_char = ''
    for c in name:
        if prev_char == '_':
            abbr += c
        prev_char = c
    return abbr

if __name__ == '__main__':
    if os.path.exists(NEW_SLOT_DIR):
        try:
            rmtree(NEW_SLOT_DIR)
        except Exception:
            pass
    os.mkdir(NEW_SLOT_DIR)

    # Skills and abilities
    table = 'Abilities'
    fields = 'Id,GenericName,Name,Details,AbilityIconName,AbilityGroup,PartyPowerWeight,AbilityLimitedGroupId1,AbilityLimitedGroupId2,AbilityLimitedGroupId3'
    raw_ability_data = {x['title']['Id']:x['title'] for x in get_data(tables=table, fields=fields)}
    ability_data = parse_abilities(raw_ability_data)

    # Amulets/Wyrmprints
    tables = 'Wyrmprints'
    fields = 'Id,BaseId,Name,NameJP,Rarity,AmuletType,MinHp,MaxHp,MinAtk,MaxAtk,VariationId,Abilities11,Abilities12,Abilities13,Abilities21,Abilities22,Abilities23,Abilities31,Abilities32,Abilities33,ArtistCV,FlavorText1,FlavorText2,FlavorText3,FlavorText4,FlavorText5,IsPlayable,SellCoin,SellDewPoint,ReleaseDate,FeaturedCharacters,Obtain,Availability'
    where = 'Rarity >= 4'
    wp_data = get_data(tables=tables, fields=fields, where=where)
    os.mkdir(AMULET_DIR)
    with open(AMULET_DIR+'/all.py', 'w') as f:
        f.write('from slot.a import *\n\n')
        for item in wp_data:
            wp = item['title']
            ab, ab_len = get_ability(wp, ability_data, 'wp', 3, 3)
            if ab_len == 0:
                continue
            clean_name = re.sub(r'[^a-zA-Z0-9 ]', '', wp['Name']).replace(' ', '_')
            abbr_name = abbreviateClassName(clean_name)
            f.write('class {}(Amulet):\n'.format(clean_name))
            f.write('    att = {}\n'.format(wp['MaxAtk']))
            f.write('    a = ' + ab + '\n')
            f.write('{} = {}\n'.format(abbr_name, clean_name))
            f.write('\n')

    # Dragons
    os.mkdir(DRAGON_DIR)
    tables = 'Dragons'
    fields = 'BaseId,Id,Name,FullName,NameJP,Title,TitleJP,Obtain,Rarity,ElementalType,ElementalTypeId,VariationId,IsPlayable,MinHp,MaxHp,MinAtk,MaxAtk,Skill1,SkillName,SkillDescription,Abilities11,Abilities12,Abilities21,Abilities22,ProfileText,FavoriteType,JapaneseCV,EnglishCV,SellCoin,SellDewPoint,MoveSpeed,DashSpeedRatio,TurnSpeed,IsTurnToDamageDir,MoveType,IsLongRange,ReleaseDate,Availability'
    for ele in ELEMENT_TYPE:
        where = 'ElementalType = "{}"'.format(ele)
        dragon_data = get_data(tables=tables, fields=fields, where=where)
        with open(DRAGON_DIR + '/' + ele.lower() + '.py', 'w') as f:
            f.write('from slot import *\n\n')
            for item in dragon_data:
                dra = item['title']
                ab, ab_len = get_ability(dra, ability_data, 'dra', 2, 2)
                if ab_len == 0:
                    continue
                if dra['MaxAtk'] == '':
                    continue
                clean_name = re.sub(r'[^a-zA-Z0-9 ]', '', dra['FullName']).replace(' ', '_')
                f.write('class {}(DragonBase):\n'.format(clean_name))
                f.write('    ele = \'{}\'\n'.format(ele.lower()))
                f.write('    att = {}\n'.format(dra['MaxAtk']))
                f.write('    aura = ' + ab + '\n')
                f.write('\n')

    # Weapons
    os.mkdir(WEAPON_DIR)
    tables = 'Weapons'
    fields = 'Id,BaseId,FormId,WeaponName,WeaponNameJP,Type,TypeId,Rarity,ElementalType,ElementalTypeId,MinHp,MaxHp,MinAtk,MaxAtk,VariationId,Skill,SkillName,SkillDesc,Abilities11,Abilities21,IsPlayable,FlavorText,SellCoin,SellDewPoint,ReleaseDate,CraftNodeId,ParentCraftNodeId,CraftGroupId,FortCraftLevel,AssembleCoin,DisassembleCoin,DisassembleCost,MainWeaponId,MainWeaponQuantity,CraftMaterialType1,CraftMaterial1,CraftMaterialQuantity1,CraftMaterialType2,CraftMaterial2,CraftMaterialQuantity2,CraftMaterialType3,CraftMaterial3,CraftMaterialQuantity3,CraftMaterialType4,CraftMaterial4,CraftMaterialQuantity4,CraftMaterialType5,CraftMaterial5,CraftMaterialQuantity5,Obtain,Availability,AvailabilityId'
    for wt in WEAPON_TYPE:
        where = 'ElementalType IS NOT NULL AND Availability="High Dragon" AND Type = "{}"'.format(wt)
        weapon_data = get_data(tables=tables, fields=fields, where=where)
        with open(WEAPON_DIR + '/' + wt.lower() + '.py', 'w') as f:
            f.write('from slot import *\n\n')
            for item in weapon_data:
                wep = item['title']
                ab, ab_len = get_ability(wep, raw_ability_data, 'wep', 2, 1)
                # if ab_len == 0:
                #     continue
                clean_name = re.sub(r'[^a-zA-Z0-9 ]', '', wep['WeaponName']).replace(' ', '_')
                f.write('class {}(WeaponBase):\n'.format(clean_name))
                f.write('    ele = \'{}\'\n'.format(wep['ElementalType'].lower()))
                f.write('    wt = \'{}\'\n'.format(wt.lower()))
                f.write('    att = {}\n'.format(wep['MaxAtk']))
                f.write('    s3 = {} # ' + wep['SkillName'] + '\n')
                f.write('    a = ' + ab + '\n')
                f.write('\n')