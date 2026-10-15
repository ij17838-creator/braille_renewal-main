"""영어 9단원 「짧은 문장」.

근거: 「개정 한국 점자 규정」 제29항(규정집 20쪽), 제32항(21쪽), 제37항 [붙임](25쪽), 「통일영어점자 규정」 10절 보기.
게임은 앞 단원 점형으로 문장을 그때그때 만든다(카드 없음). 자료의 문장 점형은 저장소 영어 엔진(engine/en)으로 적고,
UEB 규정집 보기 문장과 규정집 제32항 보기(점자 ASCII)로 대조한다.
"""
from common import braille, dots_text, reg_cells, standard_doc, unit_data
from en_common import STANDING_ALONE, answers, check_ueb, en_braille, ko_rule, read_items, word_card, write_items

UNIT_ID = 'en-sentence'
# UEB 규정집 보기 문장 (10.1절 113쪽, 10.5절 123~125쪽, 10.9절 146쪽)
UEB_EXAMPLES = {
    'Be good.': '⠠⠆ ⠛⠙⠲',
    'In or out?': '⠠⠔ ⠕⠗ ⠳⠦',
    'When will Will meet us?': '⠠⠱⠢ ⠺ ⠠⠺ ⠍⠑⠑⠞ ⠥⠦',
    'That is quite fair and very just.': '⠠⠞ ⠊⠎ ⠟ ⠋⠁⠊⠗ ⠯ ⠧ ⠚⠲',
    'Every child from here knows Mr More.': '⠠⠑ ⠡ ⠋ ⠐⠓ ⠐⠅⠎ ⠠⠍⠗ ⠠⠍⠲',
    'You should receive your letter tomorrow afternoon.': '⠠⠽ ⠩⠙ ⠗⠉⠧ ⠽⠗ ⠇⠗ ⠞⠍ ⠁⠋⠝⠲',
}
# 제32항 보기 (규정집 21쪽): 두 줄을 이어 붙임
KO_SENTENCE = ('식탁 위에 apples, bananas, grapes 등이 있다.', '``,oaha`mrn`0apples1`bananas1`grapes4`i{7o`o/i4')
READ_ITEMS = ['I can go with you.', 'It was good.', 'We were out.', 'Do you like it?']
WRITE_ITEMS = ['This is for the child.', 'His name is Tom.', 'Thank you, my friend.', 'The children were in the room.']


def build():
    u = unit_data(UNIT_ID)
    check_ueb(UEB_EXAMPLES)
    ko_cells = reg_cells(KO_SENTENCE[1])
    assert '⠴' + en_braille('apples, bananas, grapes') + '⠲' in braille(ko_cells)  # 로마자표 사이는 UEB (쉼표 ⠂)
    learn = [
        {'title': '문장을 점자로 적는 순서', 'blocks': [
            {'t': 'bullets', 'items': [
                '문장 첫 글자 같은 대문자 앞에는 대문자 기호표 ⠠를 적습니다 (2단원).',
                '홀로 쓰인 낱말은 단어 약자나 축어로 줄입니다 (3·4·6·8단원). ' + STANDING_ALONE,
                '낱말 안의 철자는 묶음 약자로 줄입니다 (4~7단원).',
                '문장 끝 부호는 앞 낱말에 붙여 적습니다 (2단원).',
            ]},
        ]},
        {'title': '규정집 보기 문장', 'blocks': [
            {'t': 'p', 'text': '「통일영어점자 규정」 10절의 보기 문장입니다. 낱말마다 어떤 약자를 썼는지 찾아보세요.'},
            {'t': 'cards', 'items': [word_card(t) for t in UEB_EXAMPLES]},
        ]},
        {'title': '한글 문장 안의 영어', 'blocks': [
            {'t': 'p', 'text': '한글 문장 안의 영어는 로마자표(⠴)와 로마자 종료표(⠲) 사이에 적고, 그 사이는 「통일영어점자 규정」을 따릅니다 (제29항, 제32항). '
                               '그래서 아래 보기에서 영어 낱말 사이의 쉼표는 영어 점형(⠂, 2점)입니다. 아래는 규정집 제32항의 보기 문장입니다.'},
            {'t': 'cards', 'items': [{'name': KO_SENTENCE[0], 'cells': ko_cells, 'labels': None, 'line': dots_text(ko_cells)}]},
            {'t': 'p', 'text': '다만 한글 문장 안에서는 단어 약자를 쓰지 않고 풀어 적습니다. be, enough, his, in, was, were는 로마자 종료표 앞에서도 풀어 적습니다 (제37항, 제37항 [붙임]).'},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 문장일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 문장을 괄호에 쓰세요. 「빈칸」은 띄어쓰기입니다.', 'blank': '(                              )',
             'items': read_items(READ_ITEMS)}]},
        {'title': '쓰기 연습: 문장을 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '배운 약자를 모두 써서 적으세요. 띄어쓰기도 한 칸입니다.', 'items': write_items(WRITE_ITEMS)}]},
    ]
    return standard_doc(
        u, rules=ko_rule('제29항', '제32항', '제37항 [붙임]'),
        rule_src='「개정 한국 점자 규정」 제29항, 제32항, 제37항 [붙임] (규정집 20~25쪽), 「통일영어점자 규정」(UEB, 2024) 10절 보기',
        key=u['teach']['line'],
        intro_bullets=[
            '앞에서 배운 알파벳, 부호, 약자, 축어를 모두 써서 문장을 적습니다.',
            '영어 문장 안의 문장 부호는 영어 점형으로 적습니다.',
            '한글 문장 안의 영어는 로마자표 ⠴와 로마자 종료표 ⠲ 사이에 적고, 단어 약자는 풀어 적습니다.',
        ],
        learn=learn, practice=practice,
        checks=[
            '짧은 영어 문장의 점자를 읽을 수 있다.',
            '짧은 영어 문장을 약자를 써서 점자로 적을 수 있다.',
            '한글 문장 안의 영어를 로마자표와 로마자 종료표 사이에 적는다는 것을 안다.',
        ],
        answers=answers(READ_ITEMS, WRITE_ITEMS),
    )
