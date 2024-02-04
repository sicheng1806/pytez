'''
这个模块用于支持命名和锚点系统
'''
from .position import must_abspos

class Anchor():
    '''
    这个模块定义了Anchor类，用于支持Anchor的调用

    功能
    -------
    锚点储存位置信息，锚点类储存锚点,锚点可以使用字典储存

    用法
    -------
    初始化后使用锚点方法可以调用锚点

    属性
    ------
    1. ``_anchors`` 锚点字典，锚点命名中不能有 '.' 。
    2. ``anchors`` 锚点字典

    方法
    ------
    1. ``get_anchor(name)`` 通过锚点名字获取锚点
    2. ``set_anchor(name,abspos)`` 改变已有锚点的值
    3. ``new_anchor(name,abspos)`` 新建锚点
    4. ``exist_anchor(name)`` 锚点是否存在
    5. ``get_anchors()`` 返回锚点字典
    '''

    def __init__(self) -> None:
        self._anchors = {}

    @property
    def anchors(self):
        return self._anchors
    def get_anchors(self):
        return self.anchors
    def get_anchor(self,name):
        '''返回一个锚点坐标'''
        self._must_exist_anchor(name)
        return self._anchors[name]
    def set_anchor(self,name,abspos):
        '''改变已有锚点的值'''
        must_abspos(abspos)
        self._must_exist_anchor(name)
        self._anchors[name] = abspos
    def new_anchor(self,name,abspos):
        '''新建锚点'''
        must_abspos(abspos)
        self._must_name_valid(name)
        self._anchors[name] = abspos
    def exist_anchor(self,name):
        return name in self._anchors
    def _must_exist_anchor(self,name):
        if not self.exist_anchor(name):
            raise AttributeError(f"{self}中，锚点{name}，不存在")
        return True
    def _must_name_valid(self,name):
        if not  isinstance(name,str) or '.'  in name:
            raise AttributeError(f"{name}不是合法的锚点名称")


    