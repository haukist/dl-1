from core.advbase import *
from slot.a import *
from slot.d import *

def module():
    return Student_Maribelle

class Student_Maribelle(Adv):
    a1 = ('s', 0.4, 'hp100')
    a3 = ('bk',0.3)
    conf = {}
    conf['slots.d'] = Sakuya()
    conf['acl'] = """
        `dragon.act('c3 s end')
        `s3, not self.s3_buff
        `s1
        `s2
    """
    coab = ['Blade', 'Marth', 'Serena']

if __name__ == '__main__':
    from core.simulate import test_with_argv
    test_with_argv(None, *sys.argv)